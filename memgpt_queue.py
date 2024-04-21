import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException, Header
from starlette.responses import HTMLResponse
from typing import Optional, List
import json
import time
import httpx



from fastapi.responses import StreamingResponse
from collections import defaultdict
import uuid
import os
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8283")

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# In-memory queue and response storage
request_queue = asyncio.Queue()

processed_responses_obj = {}  # Dictionary keyed by user_api_key with values as dictionaries of message_id to message

processed_responses_list = defaultdict(list)

### Imported from main app ###
# Used for context, end of calls, etc. Protected by memgpt user and agent keys
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

    return user_api_key, default_agent_id, latest_message


def create_response_chunk(content, end_of_conversation=False):
    response_id = str(uuid.uuid4())
    response_timestamp = int(time.time())
    response = {
        "id": response_id,
        "choices": [
            {
                "delta": {
                    "content": content,
                    "function_call": None,
                    "role": None,
                    "tool_calls": None
                },
                "finish_reason": "stop" if end_of_conversation else None,
                "index": 0,
                "logprobs": None
            }
        ],
        "created": response_timestamp,
        "model": "memgpt-custom-model",
        "object": "chat.completion.chunk",
        "system_fingerprint": None
    }
    json_data = json.dumps(response)
    return f"data: {json_data}\n\n"



### end import from main app ###

### REDIS QUEU app ###

# Background worker function
async def process_requests():
    while True:
        user_api_key, agent_id, latest_message, request_id = await request_queue.get()
        logging.info(f"Starting to process message for request ID: {request_id}")
        # Simulate processing the message
        await asyncio.sleep(2)  # simulate delay
        processed_response = f"Processed {latest_message} for {user_api_key} with {agent_id}"
        processed_responses_list[user_api_key].append((request_id, processed_response))
        request_queue.task_done()
        logging.info(f"Completed processing message for request ID: {request_id}")

@app.post("/memgpt-sse-1/chat/completions")
async def custom_memgpt_sse_handler(request: Request):
    try:
        user_api_key, agent_id, latest_message = await extract_request_data(request)
        request_id = str(uuid.uuid4())
        logging.info(f"Received request - User API Key: {user_api_key}, Agent ID: {agent_id}, Latest Message: {latest_message}, Request ID: {request_id}")
        await request_queue.put((user_api_key, agent_id, latest_message, request_id))
        return StreamingResponse(event_generator(user_api_key, request_id), media_type="text/event-stream")
    except HTTPException as he:
        logging.error(f"Failed to extract request data: {he}")
        raise he

# Assuming the create_response_chunk and processed_responses are defined elsewhere in your code

# async def event_generator(user_api_key, request_id):
#     last_sent_index = 0  # track the last sent index
#     try:
#         logging.info(f"Starting SSE stream for request ID: {request_id}")
#         while True:
#             await asyncio.sleep(1)  # check for new data every second
#             if user_api_key in processed_responses:
#                 responses = processed_responses[user_api_key]
#                 # Only send new responses
#                 for idx in range(last_sent_index, len(responses)):
#                     rid, response = responses[idx]
#                     if rid == request_id:
#                         logging.info(f"Sending response: {response} for request ID: {request_id}")
#                         chunk = create_response_chunk(response, end_of_conversation=False)
#                         logging.info(f"sending chunk: {chunk}")
#                         yield chunk
#                         last_sent_index = idx + 1  # update the last sent index
#                     else:
#                         logging.debug(f"Skipped response for different request ID: {rid} expected: {request_id}")
#             else:
#                 logging.info(f"No new messages, sending placeholder for request ID: {request_id}")
#                 yield create_response_chunk("No new messages at the moment.", end_of_conversation=True)
#     except Exception as e:
#         logging.error(f"Error in SSE stream for request ID: {request_id}: {str(e)}")
#     finally:
#         logging.info(f"Closing SSE stream for request ID: {request_id}")


### Debugging version ###

# import asyncio
# import logging
# from fastapi import FastAPI, Request, HTTPException
# from fastapi.responses import StreamingResponse
# import json
# import uuid

# app = FastAPI()

# # Setting up a basic asyncio queue for requests
# request_queue = asyncio.Queue()

@app.post("/memgpt-sse/chat/completions")
async def custom_memgpt_sse_handler(request: Request):
    # Extract the full incoming request data
    incoming_request_data = await request.json()
    logging.info(f'Full incoming request data: {incoming_request_data}')

    try:
        user_api_key, agent_id, latest_message = await extract_request_data(request)
        
        request_id = str(uuid.uuid4())
        logging.info(f"Received request - User API Key: {user_api_key}, Agent ID: {agent_id}, Latest Message: {latest_message}, Request ID: {request_id}")
        
         # Use the new enqueue function to handle data formatting and queuing
        await enqueue_data(request_queue, agent_id, latest_message, user_api_key, request_id)
        logging.info('Request has been enqueued')
        

    except HTTPException as he:
        logging.error(f"Failed to extract request data: {he}")
        raise he

    # Immediately return a SSE response
    return StreamingResponse(generate_streaming_response({"Once upon a time","there","were","three", "little","pigs"}), media_type="text/event-stream")
    #return StreamingResponse(event_generator(user_api_key), media_type="text/event-stream")

def generate_streaming_response(data):
    """
    Generator function to simulate streaming data.
    """
    for message in data:
        yield create_response_chunk(message, False)
        time.sleep(.1)  # You might adjust or remove this during debugging

# def generate_streaming_response(data):
#     """
#     Generator function to simulate streaming data.
#     """
#     for message in data:
#         json_data = message.model_dump_json()
#         yield f"data: {json_data}\n\n"



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


async def enqueue_data(request_queue, agent_id, message, user_api_key, request_id):
    if isinstance(agent_id, str) and isinstance(message, str) and isinstance(user_api_key, str) and isinstance(request_id, str):
        request_data = {
            'agent_id': agent_id,
            'message': message,
            'user_api_key': user_api_key,
            'request_id': request_id
        }
        await request_queue.put(request_data)
        logging.info('Request has been enqueued')
    else:
        logging.error("Attempted to enqueue data with incorrect format")
        raise ValueError("Provided data does not meet the required format specifications.")



# Repeats no new messages uses list
async def event_generator_repeatlist(user_api_key):
    logging.info(f"Starting SSE stream for {user_api_key}")
    last_index_sent = 0  # Maintain the last index sent to ensure continuity

    try:
        while True:
            # Debug log to see if this part of the loop is reached
            logging.debug("Checking for new messages...")
            
            if user_api_key in processed_responses_list and last_index_sent < len(processed_responses_list[user_api_key]):
                while last_index_sent < len(processed_responses_list[user_api_key]):
                    message = processed_responses_list[user_api_key][last_index_sent]
                    logging.info(f"Sending message: {message}")
                    yield create_response_chunk(message, end_of_conversation=False)
                    last_index_sent += 1
            else:
                # Send a keep-alive message or log if no new messages
                logging.debug("No new messages available to send.")
                yield create_response_chunk("No new messages at the moment.", end_of_conversation=False)
            
            # Wait for a short time before checking again to reduce CPU usage
            await asyncio.sleep(0.1)
    finally:
        logging.info(f"Closing SSE stream for {user_api_key}")

from collections import defaultdict
import logging

async def event_generator_latest(user_api_key):
    logging.info(f"Starting SSE stream for {user_api_key}")
    sent_ids = set()  # Keep track of sent message IDs

    try:
        while True:
            logging.debug("Checking for new messages...")

            if user_api_key in processed_responses_obj:
                messages = processed_responses_obj[user_api_key]
                for message_id, message in messages.items():
                    if message_id not in sent_ids:
                        logging.info(f"Sending message: {message}")
                        yield create_response_chunk(message, end_of_conversation=False)
                        sent_ids.add(message_id)
                
                # Clean up sent messages to avoid re-sending them
                for message_id in list(messages):
                    if message_id in sent_ids:
                        del messages[message_id]
                        logging.info(f"Deleted sent message ID {message_id} from the queue")  # Log message deletion


            if not messages:
                # Send a keep-alive message or log if no new messages
                logging.debug("No new messages available to send.")
                yield create_response_chunk("No new messages at the moment.", end_of_conversation=False)

            # Wait for a short time before checking again to reduce CPU usage
            await asyncio.sleep(1)

    finally:
        logging.info(f"Closing SSE stream for {user_api_key}")


def event_generator(user_api_key):
    logging.info(f"Starting SSE stream for {user_api_key}")
    sent_ids = set()  # Keep track of sent message IDs to avoid duplicates

    try:
        while True:
            # Log the current state before processing
            logging.debug(f"Current messages for {user_api_key}: {processed_responses_obj.get(user_api_key, {})}")

            messages = processed_responses_obj.get(user_api_key, {})
            if messages:
                for message_id, message in list(messages.items()):
                    if message_id not in sent_ids:
                        logging.info(f"Yielding new message ID {message_id}")
                        yield create_response_chunk(message, end_of_conversation=False)
                        sent_ids.add(message_id)
                        #del messages[message_id]  # Consider commenting this line during debugging

            # Log if no messages are found
            if not messages:
                logging.debug("No new messages available to send.")
                yield create_response_chunk("No new messages at the moment.", end_of_conversation=False)

            # Introduce a short pause to allow new messages to be processed
            #time.sleep(1)  # You might adjust or remove this during debugging

    except Exception as e:
        logging.error(f"Error in SSE stream for {user_api_key}: {str(e)}")
        yield f"data: ERROR: {str(e)}\n\n"

    finally:
        logging.info(f"Closing SSE stream for {user_api_key}")
        yield "event: close\ndata: Stream closed by server\n\n"



#Best practice version
def event_generator_base(user_api_key):
    logging.info(f"Starting SSE stream for {user_api_key}")
    yield create_response_chunk("Hmmmm, interesting...", end_of_conversation=False)
    try:
        sent_ids = set()  # Keep track of sent message IDs to avoid duplicates

        while True:
            # Simulate fetching messages; replace this with actual data fetching logic
            messages = processed_responses_obj.get(user_api_key, {})
            if messages:
                yield create_response_chunk("New messages detected", end_of_conversation=False)
            # Send any new messages
            if messages:
                for message_id, message in list(messages.items()):
                    if message_id not in sent_ids:
                        #yield create_response_chunk(message, end_of_conversation=False)
                        yield create_response_chunk("Inside the nest I found New messages", end_of_conversation=False)
                        yield create_response_chunk(f"{message}", end_of_conversation=False)
                        sent_ids.add(message_id)
                        # After sending, delete the message from the global store if necessary
                        del messages[message_id]
                        logging.info(f"Sent and deleted message ID {message_id} from the queue")
            else:
                # If no messages, send a comment to keep the connection alive
                yield create_response_chunk("No new messages at the moment.", end_of_conversation=False)
                #yield ":keep-alive\n\n"
            # Simulate a delay to mimic async sleep in a synchronous environment
            #time.sleep(2)

            # Wait before the next check to reduce load
            #await asyncio.sleep(1)  # Adjust the sleep time based on your use case

    except Exception as e:
        # Handle any exceptions that may occur and log them
        logging.error(f"Error in SSE stream for {user_api_key}: {str(e)}")
        yield f"data: ERROR: {str(e)}\n\n"

        # Optionally, you could close the stream on error or try to recover
        yield "event: error\ndata: Stream encountered an error and will close.\n\n"

    finally:
        # Clean up resources and log the stream closing
        logging.info(f"Closing SSE stream for {user_api_key}")
        yield "event: close\ndata: Stream closed by server\n\n"




 


# #W orking for immeidately responding
# async def event_generator():
#     try:
#         logging.info("Starting SSE stream")
#         # Simulate generating a response
#         response_content = "This is a dummy response to test immediate streaming."
#         yield create_response_chunk(response_content, end_of_conversation=True)
#         logging.info("Sent SSE response")
#     finally:
#         logging.info("Closing SSE stream")




async def dummy_worker():
    while True:
        user_api_key = "sk-9de42a0a8262228362ae1c7fb57dabfb9229cdd65470218f"
        message_id = str(uuid.uuid4())
        message_content = "New processed message from dummy worker"

        if user_api_key not in processed_responses_obj:
            processed_responses_obj[user_api_key] = {}
        
        processed_responses_obj[user_api_key][message_id] = message_content
        logging.info("Dummy worker added a new message with ID: " + message_id)
        await asyncio.sleep(8)  # Simulate some work


async def send_messages_worker():
    while True:
        if not request_queue.empty():
            request_data = await request_queue.get()
            if isinstance(request_data, dict):
                agent_id = request_data['agent_id']
                message = request_data['message']
                user_api_key = request_data['user_api_key']
                request_id = request_data['request_id']

                retries = 5

                while retries > 0:
                    response = await send_message_to_agent(agent_id, message, user_api_key)
                    if response.status_code == 200:
                        data = response.json()
                        if "messages" in data:
                            logging.info(f"Message sent successfully: {data['messages']}")
                            break
                        else:
                            logging.error("Response format is incorrect, no 'messages' key found.")
                    else:
                        logging.error(f"Failed to send message, status code: {response.status_code}")
                        retries -= 1
                        await asyncio.sleep(5)

                    if retries == 0:
                        logging.error("Max retries reached, message sending failed.")

            else:
                logging.error("Incorrect data format received in queue")
        await asyncio.sleep(0.1)


@app.on_event("startup")
async def startup_event():
    logging.info("Starting background worker task...")
    asyncio.create_task(send_messages_worker())  # Start the worker as a background task
    asyncio.create_task(dummy_worker())  # Start the worker as a background task
