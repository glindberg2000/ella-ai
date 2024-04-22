from fastapi import FastAPI, Request, HTTPException

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

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()

# Redis connection
redis_url = f"redis://:{os.getenv('REDIS_PASSWORD')}@localhost:6379"

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

async def queue_request(latest_message, server_url_secret: Optional[str] = None):
    """Queue a new request in Redis with a unique `request_id`."""
    request_id = str(uuid.uuid4()) #Poetentially extract from VAPI instead
    await app.redis.lpush("requests", json.dumps({
        "request_id": request_id,
        "incoming_message": latest_message,
        "timestamp_created": time.time(),
        "server_url_secret": server_url_secret,
        "raw_message_placeholder": None #Placeholder if you want to save the entire request
    }))
    return request_id



async def worker_process():
    """Background worker process to consume requests, process them, and store responses."""
    while True:
        logging.info("Checking for requests in Redis...")

        # Use `rpop` to retrieve the latest request by `request_id`
        request_data = await app.redis.rpop("requests")

        if not request_data:
            logging.info("No requests found. Sleeping for 1 second.")
            await asyncio.sleep(1)
            continue
        
        try:
            request = json.loads(request_data)
        except json.JSONDecodeError:
            logging.error("Failed to decode request data.")
            logging.error(f"Request data: {request_data}")
            continue
        
        request_id = request.get("request_id")
        if not request_id:
            logging.error("Request data missing 'request_id'.")
            continue
        
        logging.info(f"Found request with request_id: {request_id}. Processing...")

        # Simulate processing e.g. sending message to memgpt and checking for resopnse
        processed_response = await process_request(request)
        
        # Store the processed response with `request_id`
        await app.redis.rpush(f"responses:{request_id}", json.dumps({
            **processed_response
        }))
        logging.info(f"Stored processed response with request_id: {request_id}.")


async def process_request(request):
    """Simulate processing a request with a backend LLM or other processing logic."""
    logging.info("Processing request...")

    # Simulate processing time
    time.sleep(2)

    # Add a timestamp to indicate when the processing was completed
    timestamp_processed = time.time()
    
    # Include the timestamp in the request data
    response = request.copy()  # Create a copy of the original request
    response["timestamp_processed"] = timestamp_processed
    response["response_message"]=f"Processed message with Reqeust ID {request.get('request_id')} and incoming message: {request.get('incoming_message')}"
    response["vapi_response"] = create_vapi_response(response["response_message"])
    logging.info("Request processing completed.")

    return response



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
        request_id = await queue_request(latest_message, server_url_secret)
        logging.info(f"Received request - User API Key: {user_api_key}, Agent ID: {agent_id}, Latest Message: {latest_message}, Request ID: {request_id}")
        return StreamingResponse(stream_all_responses_chunked(request_id, server_url_secret), media_type="text/event-stream")
    except HTTPException as he:
        logging.error(f"Failed to extract request data: {he}")
        raise he
