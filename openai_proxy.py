# openai_proxy.py

import json
import os
import time

import httpx
from chainlit.server import app
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from openai import OpenAI
from starlette.responses import StreamingResponse
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from ella_memgpt.extendedRESTclient import ExtendedRESTClient

# Add other routes or routers as needed

# Load environment variables from .env file
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY", "defaultopenaikey")
# Load environment variables from .env file

base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8283")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")
# Define default values
DEFAULT_USER_ID = "d48465a1-8153-448d-9115-93fdaae4b290"
DEFAULT_API_KEY = "sk-614ca012fa835acffa3879729c364124eba195fca46b190b"
DEFAULT_AGENT_ID = "31b3722a-ebc1-418a-9056-4ef780d2f494"
DEFAULT_AGENT_CONFIG = {
    "name": "DefaultAgent5",
    "preset": "memgpt_chat",
    "human": "cs_phd",
    "persona": "anna_pa",
}
CHATBOT_NAME = "Ella"
# Initialize the OpenAI client
client = OpenAI()


router = APIRouter()


@app.get("/test")
async def test_endpoint():
    return {"message": "This is a test endpoint"}


def generate_streaming_response(data):
    """
    Generator function to simulate streaming data.
    """
    for message in data:
        json_data = message.model_dump_json()
        yield f"data: {json_data}\n\n"


def sanitize_request_for_openai(request_data):
    """
    Take the incoming request data and return a sanitized version
    that is compatible with OpenAI's API.
    """
    # Example of sanitization: Only keep the 'messages' field
    # and ensure 'stream' is set correctly.
    sanitized_request = {
        "model": "gpt-3.5-turbo-0613",  # Specify the model you want to use
        "messages": request_data.get("messages", []),
        "stream": request_data.get("stream", True),
    }
    return sanitized_request


@app.post("/openai-sse/chat/completions")
async def custom_llm_openai_sse_handler(request: Request):
    incoming_request_data = await request.json()
    request_data = sanitize_request_for_openai(incoming_request_data)

    streaming = request_data.get("stream", True)
    if streaming:
        # Simulate a stream of responses
        print("streaming output...")
        try:
            chat_completion_stream = client.chat.completions.create(**request_data)
            return StreamingResponse(
                generate_streaming_response(chat_completion_stream),
                media_type="text/event-stream",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Simulate a non-streaming response
        print("not streaming output.")
        chat_completion = client.chat.completions.create(**request_data)
        return chat_completion.model_dump_json()



# Step 1: Adjusting the request sanitization function for MemGPT

def sanitize_request_for_memgpt(request_data):
    """
    Extracts the latest user message from the incoming request data.
    Since MemGPT expects a simple string input, we return just the latest user message.
    """
    # Filter out messages where the role is 'user', then get the last one
    user_messages = [msg for msg in request_data.get("messages", []) if msg.get("role") == "user"]
    latest_message = user_messages[-1].get("content", "") if user_messages else ""
    return latest_message


# Step 2: Updating the endpoint handler to work with MemGPT
@app.post("/dummymemgpt-sse/chat/completions")
async def dummy_memgpt_sse_handler(request: Request):
    """
    Handles requests by forwarding them to MemGPT and returning the response.
    Adjusted to work with MemGPT's expectation of receiving a simple string as input.
    """
    incoming_request_data = await request.json()
    latest_message = sanitize_request_for_memgpt(incoming_request_data)

    streaming = incoming_request_data.get("stream", True)
    if streaming:
        print("Streaming output...")
        try:
            # Simulate making a call to MemGPT with the latest message
            # And receiving a stream of responses (for the sake of example, we simulate this)
            memgpt_response_stream = [{"assistant_message": "Simulated response from MemGPT."}]
            return StreamingResponse(
                generate_memgpt_streaming_response(memgpt_response_stream),
                media_type="text/event-stream",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        print("Not streaming output.")
        # Simulate a non-streaming response from MemGPT
        memgpt_response = {"assistant_message": "Simulated response from MemGPT."}
        return JSONResponse(content=memgpt_response)

# @app.post("/memgpt-sse/chat/completions")
# async def custom_memgpt_sse_handler(request: Request):
#     incoming_request_data = await request.json()
#     print('incoming data:',incoming_request_data)
#     latest_message = sanitize_request_for_memgpt(incoming_request_data)
#     print('latest message:',latest_message)
#     #latest_message = 'how is the weather today?'
#     user_api_key = DEFAULT_API_KEY
#     agent_id = DEFAULT_AGENT_ID
#     user_api = ExtendedRESTClient(base_url, user_api_key)

#     streaming = incoming_request_data.get("stream", True)
#     if streaming:
#         try:
#             print('latest message from vapi received:',latest_message)
#             memgpt_response_stream = user_api.send_message_to_agent_streamed(agent_id, latest_message)
#             return StreamingResponse(
#                 generate_memgpt_streaming_response(memgpt_response_stream),
#                 media_type="text/event-stream",
#             )
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))
#     else:
#         # Handle non-streaming scenario if applicable
#         pass

@app.post("/memgpt-sse/chat/completions")
async def custom_memgpt_sse_handler(request: Request):
    # Extract the full incoming request data
    incoming_request_data = await request.json()
    logging.info(f'Full incoming request data: {incoming_request_data}')

    # Directly extract serverUrlSecret from the top-level 'call' object
    try:
        server_url_secret = incoming_request_data['call']['serverUrlSecret']
        logging.info(f'Extracted serverUrlSecret: {server_url_secret}')
    except KeyError as e:
        logging.error(f'serverUrlSecret not found in the expected call configuration: {str(e)}')
        raise HTTPException(status_code=400, detail="serverUrlSecret is missing from the call configuration")

    # Extracting user API key and default agent ID from serverUrlSecret
    try:
        user_api_key, default_agent_id = server_url_secret.split(':')
        logging.info(f'Extracted user API key: {user_api_key} and default agent ID: {default_agent_id}')
    except ValueError:
        logging.error("Invalid serverUrlSecret format. Expected format 'user_api_key:default_agent_id'")
        raise HTTPException(status_code=400, detail="Invalid serverUrlSecret format")

    # Set up the API client using extracted credentials
    user_api = ExtendedRESTClient(base_url, user_api_key)

    # Extract and log the latest message
    try:
        latest_message = incoming_request_data['messages'][-1]['content']
        logging.info(f'Latest message from Vapi: {latest_message}')
    except (KeyError, IndexError, TypeError) as e:
        logging.error("Failed to extract the latest message due to improper data structure.")
        raise HTTPException(status_code=400, detail=f"Error in message data: {str(e)}")

    # Check for streaming and process accordingly
    streaming = incoming_request_data.get("stream", True)
    if streaming:
        try:
            memgpt_response_stream = user_api.send_message_to_agent_streamed(default_agent_id, latest_message)
            logging.info(f'Sending request to MEMGPT with agent ID {default_agent_id}')
            return StreamingResponse(
                generate_memgpt_streaming_response(memgpt_response_stream),
                media_type="text/event-stream",
            )
        except Exception as e:
            logging.error(f"Error during streaming response: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Handle non-streaming scenario if applicable
        logging.info(f'Streaming not set to True, handling non-streaming scenario: exiting')

import time
import uuid
import json

async def generate_memgpt_streaming_response(data_stream):
    """
    Asynchronous generator function to process and yield only 'assistant_message' data from MemGPT.
    Filters out other message types like 'internal_monologue' and 'function_call' unless needed.
    Each response includes a unique ID and a timestamp.
    """
    async for data_line in data_stream:
        if data_line.startswith("data: "):
            data_content = data_line[6:]  # Extract JSON content
            message_part = json.loads(data_content)  # Convert string to dictionary
            print('full message:',message_part)
            # Check and handle only 'assistant_message' types
            if "assistant_message" in message_part:
                print('assistant message found in message part:',message_part['assistant_message'])
                response_id = str(uuid.uuid4())  # Generate a unique ID for each response
                response_timestamp = int(time.time())  # Get current Unix time in seconds
                response = {
                    "id": response_id,
                    "choices": [
                        {
                            "delta": {
                                "content": message_part["assistant_message"],
                                "function_call": None,
                                "role": None,
                                "tool_calls": None
                            },
                            "finish_reason": "stop" if message_part.get("end_of_conversation", False) else None,
                            "index": 0,
                            "logprobs": None
                        }
                    ],
                    "created": response_timestamp,  # Dynamic timestamp when the response was created
                    "model": "memgpt-custom-model",
                    "object": "chat.completion.chunk",
                    "system_fingerprint": None
                }
                json_data = json.dumps(response)
                yield f"data: {json_data}\n\n"

# async def generate_memgpt_streaming_response(data_stream):
    """
    Asynchronous generator function to process and yield MemGPT response data.
    It checks the type of each message part (e.g., assistant_message, function_call)
    and handles it accordingly in an asynchronous context.
    """
    async for data_line in data_stream:
        if data_line.startswith("data: "):
            data_content = data_line[6:]  # Extract JSON content
            message_part = json.loads(data_content)  # Convert string to dictionary
            
            # Handle different types of messages
            if "assistant_message" in message_part:
                # Construct response similar to the simulated OpenAI response for compatibility
                response = {
                    "id": "memgpt-chatcmpl-XXXXX",
                    "choices": [
                        {
                            "delta": {
                                "content": message_part["assistant_message"],
                                "function_call": None,
                                "role": None,
                                "tool_calls": None
                            },
                            "finish_reason": "stop" if message_part.get("end_of_conversation", False) else None,
                            "index": 0,
                            "logprobs": None
                        }
                    ],
                    "created": 1712776130,  # This would be dynamic in a real scenario
                    "model": "memgpt-custom-model",
                    "object": "chat.completion.chunk",
                    "system_fingerprint": None
                }
                json_data = json.dumps(response)
                yield f"data: {json_data}\n\n"
            # Add elif blocks here for other message_part types as needed, e.g., function_call

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



# # Protected by memgpt user and agent keys
# @app.post("/memgpt-sse/chat/completions")
# async def custom_memgpt_sse_handler(request: Request, x_vapi_secret: Optional[str] = Header(None)):
#     if not x_vapi_secret:
#         logging.error("x-vapi-secret header is missing")
#         # Log all headers for debugging
#         headers = dict(request.headers)
#         logging.debug(f"All received headers: {headers}")
#         raise HTTPException(status_code=400, detail="x-vapi-secret header missing")

#     # Parse the x-vapi-secret to obtain the memgpt_user_api_key and default_agent_key
#     try:
#         memgpt_user_api_key, default_agent_key = x_vapi_secret.split(':')
#     except ValueError:
#         logging.error("Invalid x-vapi-secret format")
#         raise HTTPException(status_code=400, detail="Invalid x-vapi-secret format")

#     logging.info(f"User API Key: {memgpt_user_api_key}, Agent ID: {default_agent_key}")

#     incoming_request_data = await request.json()
#     logging.debug(f"Incoming data: {incoming_request_data}")
#     latest_message = sanitize_request_for_memgpt(incoming_request_data)
#     logging.info(f"Latest message: {latest_message}")

#     user_api = ExtendedRESTClient(base_url, memgpt_user_api_key)

#     streaming = incoming_request_data.get("stream", True)
#     if streaming:
#         try:
#             logging.info(f"Latest message from vapi received: {latest_message}")
#             memgpt_response_stream = user_api.send_message_to_agent_streamed(default_agent_key, latest_message)
#             return StreamingResponse(
#                 generate_memgpt_streaming_response(memgpt_response_stream),
#                 media_type="text/event-stream",
#             )
#         except Exception as e:
#             logging.error(f"Error processing the streaming request: {str(e)}")
#             raise HTTPException(status_code=500, detail=str(e))
#     else:
#         # Handle non-streaming scenario if applicable
#         pass

