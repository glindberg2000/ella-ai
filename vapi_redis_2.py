from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, Response
import uuid
import asyncio
import json
import time
import os
from redis.asyncio import Redis
from redis.exceptions import ResponseError
import logging
from typing import Optional
import httpx
from ella_memgpt.extendedRESTclient import ExtendedRESTClient
from memgpt.client.client import RESTClient as memgpt_client

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

debug = True  # Turn on debug mode to see detailed logs

app = FastAPI()

# Redis connection
redis_url = f"redis://:{os.getenv('REDIS_PASSWORD')}@localhost:6379"

# MemGPT connection
# Load environment variables from .env file
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")

@app.on_event("startup")
async def startup_event():
    """Initialize the Redis connection on application startup."""
    app.redis = Redis.from_url(redis_url, decode_responses=True, encoding='utf-8')
    logging.info("Starting background worker task...")
    asyncio.create_task(worker_process())  # Start the worker as a background task

@app.on_event("shutdown")
async def shutdown_event():
    """Close the Redis connection on application shutdown."""
    await app.redis.close()

async def queue_request(server_url_secret, user_api_key, agent_id, latest_message):
    """Queue a new request in Redis with a unique `request_id`."""
    request_id = str(uuid.uuid4()) #Poetentially extract from VAPI instead
    await app.redis.lpush("requests", json.dumps({
        "request_id": request_id,
        "incoming_message": latest_message,
        "timestamp_created": time.time(),
        "server_url_secret": server_url_secret,
        "user_api_key": user_api_key,
        "agent_id": agent_id,
        "raw_message_placeholder": None #Placeholder if you want to save the entire request
    }))
    return request_id


async def send_message_to_agent(agent_id, message, user_api_key):
    url = f"{base_url}/api/agents/{agent_id}/messages"
    payload = {"stream": False,
               "message": message,
                "role": "user"}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {user_api_key}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        return response
    

async def worker_process():
    """Background worker process to consume requests, process them, and store responses."""
    while True:
        logging.info("Checking for requests in Redis...")

        # Retrieve the latest request data from Redis
        raw_data = await app.redis.rpop("requests")

        if not raw_data:
            logging.info("No requests found. Sleeping for 1 second.")
            await asyncio.sleep(1)
            continue
        
        # Decode the raw data
        try:
            req_data = json.loads(raw_data)
        except json.JSONDecodeError:
            logging.error("Failed to decode request data.")
            logging.error(f"Request data: {raw_data}")
            continue
        
        request_id = req_data.get("request_id")
        if not request_id:
            logging.error("Request data missing 'request_id'.")
            continue
        
        logging.info(f"Processing request with ID: {request_id}")

        # Process the request data
        processed_response = await process_request(req_data)
        
        # Store the processed response with `request_id`
        await app.redis.rpush(f"responses:{request_id}", json.dumps(processed_response))
        logging.info(f"Stored processed response with request_id: {request_id}.")


# async def process_request_dummy(req_data):
#     """Simulate processing a request with backend logic."""

#     # Simulate processing time
#     time.sleep(2)
    
#     # Add a timestamp to indicate when the processing was completed
#     timestamp_processed = time.time()
    
#     # Create a copy of the original data and add the timestamp
#     response = req_data.copy()
#     response["timestamp_processed"] = timestamp_processed
#     response["response_message"] = f"Processed message with Request ID {req_data.get('request_id')}"
    
#     logging.info("Request processing completed.")

#     return response

def assistant_messages(json_data):
    # Extract all assistant messages
    messages = [item["assistant_message"] for item in json_data if "assistant_message" in item]
    
    # Join messages with proper punctuation
    assistant_messages = " ".join(message.rstrip(".,!") + "." for message in messages)
    
    return assistant_messages

async def process_request(req_data):
    # Extract and validate required data from req_data
    request_id = req_data.get("request_id", None)
    incoming_message = req_data.get("incoming_message", None)
    user_api_key = req_data.get("user_api_key", None)
    agent_id = req_data.get("agent_id", None)
    timestamp_created = req_data.get("timestamp_created", None)       
    raw_message_placeholder = req_data.get("raw_message_placeholder", None)
    server_url_secret = req_data.get("server_url_secret", None)

    # Ensure that the critical data is not missing
    if not request_id:
        raise ValueError("The 'request_id' is required but not found in the request data.")

    if not incoming_message:
        raise ValueError("The 'incoming_message' is required but not found in the request data.")

    if not user_api_key:
        raise ValueError("The 'user_api_key' is missing but is expected in the request data.")

    if not agent_id:
        raise ValueError("The 'agent_id' is missing but is expected in the request data.")

    #user_api = ExtendedRESTClient(base_url, user_api_key, debug)
    user_api = memgpt_client(base_url, user_api_key, debug)

 #Call the send_message function and unpack the result
    try:
        user_message_response = user_api.send_message(agent_id, incoming_message, "user", False)

        # Extract details from the UserMessageResponse
        message_details = user_message_response.messages  # Get the messages list
        logging.info(f"Message details from worker process: {message_details}")


        # Return a relevant HTTP response with the unpacked result
        # return {
        #     "status": "success",
        #     "message_details": message_details
        # }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

    #     def user_message(self, agent_id: str, message: str) -> Union[List[Dict], Tuple[List[Dict], int]]:
    #     return self.send_message(agent_id, message, role="user")
            # def send_message(self, agent_id: uuid.UUID, message: str, role: str, stream: Optional[bool] = False) -> UserMessageResponse:
            # data = {"message": message, "role": role, "stream": stream}
            # response = requests.post(f"{self.base_url}/api/agents/{agent_id}/messages", json=data, headers=self.headers)
            # return UserMessageResponse(**response.json())

    timestamp_processed = time.time()
    #response_message = f"Processing message with ID: {request_id}"
    response_message = assistant_messages(message_details)
    # # Example processing with all required data
    processed_result = {
        "request_id": request_id,
        "incoming_message": incoming_message,
        "response_message": response_message,
        "inner_monologue": None,
        "server_url_secret": server_url_secret,
        "user_api_key": user_api_key,
        "agent_id": agent_id,
        "timestamp_created": timestamp_created,
        "timestamp_processed" :timestamp_processed,
        "vapi_response": create_vapi_response(response_message,request_id=request_id, timestamp=timestamp_processed)
    }



    return processed_result


async def extract_request_data(request: Request):
    """Extracts necessary data from the incoming request.

    Args:
        request (Request): The incoming FastAPI request object.

    Returns:
        tuple: A tuple containing user_api_key, default_agent_id, and latest_message.

    Raises:
        HTTPException: If any required data is missing or in an invalid format.
    """
    # Extract the full incoming request data
    incoming_request_data = await request.json()
    logging.info(f'Full incoming request data: {incoming_request_data}')

    # Extract serverUrlSecret
    try:
        server_url_secret = incoming_request_data['call']['serverUrlSecret']
        logging.info(f'Extracted serverUrlSecret: {server_url_secret}')
    except KeyError as e:
        logging.error(f'serverUrlSecret not found in the expected call configuration: {str(e)}')
        raise HTTPException(status_code=400, detail="serverUrlSecret is missing from the call configuration")

    # Split serverUrlSecret into user API key and default agent ID
    try:
        user_api_key, default_agent_id = server_url_secret.split(':')
        logging.info(f'Extracted user API key: {user_api_key} and default agent ID: {default_agent_id}')
    except ValueError:
        logging.error("Invalid serverUrlSecret format. Expected format 'user_api_key:default_agent_id'")
        raise HTTPException(status_code=400, detail="Invalid serverUrlSecret format")

    # Extract the latest message
    try:
        latest_message = incoming_request_data['messages'][-1]['content']
        logging.info(f'Latest message from Vapi: {latest_message}')
    except (KeyError, IndexError, TypeError) as e:
        logging.error("Failed to extract the latest message due to improper data structure.")
        raise HTTPException(status_code=400, detail=f"Error in message data: {str(e)}")

    return server_url_secret, user_api_key, default_agent_id, latest_message


async def stream_all_responses_chunked(request_id: str, server_url_secret: Optional[str] = None):

    """Stream all processed responses from Redis until the specific `request_id` is found.
    optional filter by server_url_secret"""

    max_retries = 30  # Maximum retries before exiting the loop
    retries = 0  # Track the number of retries

    while retries < max_retries:
        response_ids = await app.redis.keys("responses:*")  # Get all response keys
        
        found_request_id = False  # Flag to determine if request_id is found
        
        # Process each key and yield responses
        for response_id in response_ids:
            responses = await app.redis.lrange(response_id, 0, -1)
            
            for response_data in responses:
                response = json.loads(response_data)
                if "timestamp_processed" in response:   
                    logging.info(f'Found response with request_id: {request_id}. Yielding chunk to output streamgenerator: {response["vapi_response"]}')
                    yield f"data: {response['vapi_response']}\n\n"  # Yield the response data
                    
                    
                    # Check if this response has the specific request_id
                    if response_id.endswith(f":{request_id}"):
                        found_request_id = True
                    
                    # Remove the response after yielding
                    await app.redis.lrem(response_id, 1, json.dumps(response))
        
        if found_request_id:
            break  # Exit loop if the specific request_id is found
        
        retries += 1  # Increment retries if no data is found
        await asyncio.sleep(1)  # Throttle re-checks to avoid busy-waiting


def create_vapi_response(message, request_id=None, timestamp=None, end_of_conversation=False):
    # Generate UUID for response_id if not provided
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    # Use current time for timestamp if not provided
    if timestamp is None:
        timestamp = int(time.time())

    # Construct the response object
    response = {
        "id": request_id,
        "choices": [
            {
                "delta": {
                    "content": message,
                    "function_call": None,
                    "role": None,
                    "tool_calls": None
                },
                "finish_reason": "stop" if end_of_conversation else None,
                "index": 0,
                "logprobs": None
            }
        ],
        "created": timestamp,
        "model": "memgpt-custom-model",
        "object": "chat.completion.chunk",
        "system_fingerprint": None
    }
    
    # Convert to JSON and add data prefix for streaming
    json_data = json.dumps(response)
    return json_data

@app.post("/api/vapi")
async def vapi_call_handler(request: Request, x_vapi_secret: Optional[str] = Header(None)):
    if not x_vapi_secret:
        logging.error("x-vapi-secret header is missing")
        # Log all headers for debugging
        headers = dict(request.headers)
        logging.debug(f"All received headers: {headers}")
        raise HTTPException(status_code=400, detail="x-vapi-secret header missing")

    # Parse the x-vapi-secret to obtain the memgpt_user_api_key and default_agent_key
    try:
        memgpt_user_api_key, default_agent_key = x_vapi_secret.split(':')
    except ValueError:
        logging.error("Invalid x-vapi-secret format")
        raise HTTPException(status_code=400, detail="Invalid x-vapi-secret format")

    logging.info(f"User API Key: {memgpt_user_api_key}, Agent ID: {default_agent_key}")

    incoming_request_data = await request.json()
    logging.debug(f"Incoming data: {incoming_request_data}")
    #TBD: build out call end data handler, etc. here


@app.post("/stream-test")
async def receive_and_stream_voice_input(request: Request):
    data = await request.json()  # Get the JSON from the request
    user_id = str(uuid.uuid4())  # Generate a user ID
    # Correctly encode the entire data dictionary as JSON
    message_data = json.dumps({'data': data, 'user_id': user_id})

    logger.info(f"Received voice input: {data} for user ID: {user_id}")
    """Submit a new request and initiate SSE streaming for processed responses."""
    request_id = await queue_request(data)
    logger.info(f"Request ID: {request_id} queued for user ID:{user_id}")
    #return StreamingResponse(stream_all_responses(), media_type="text/event-stream")
    return StreamingResponse(stream_all_responses_chunked(request_id=request_id),media_type="text/event-stream")


@app.post("/memgpt-sse/chat/completions")
async def custom_memgpt_sse_handler(request: Request):
    try:
        server_url_secret, user_api_key, agent_id, latest_message = await extract_request_data(request)
        request_id = await queue_request(server_url_secret, user_api_key, agent_id, latest_message)
        logging.info(f"Received request - User API Key: {user_api_key}, Agent ID: {agent_id}, Latest Message: {latest_message}, Request ID: {request_id}")
        return StreamingResponse(stream_all_responses_chunked(request_id, server_url_secret), media_type="text/event-stream")
    except HTTPException as he:
        logging.error(f"Failed to extract request data: {he}")
        raise he
