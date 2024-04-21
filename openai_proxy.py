# openai_proxy.py

import json
import os
import time
import uuid
import httpx
from chainlit.server import app
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from openai import OpenAI
from starlette.responses import StreamingResponse
from typing import Optional
import asyncio
import logging
import redis
from ella_memgpt.extendedRESTclient import ExtendedRESTClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

debug = True  # Turn on debug mode to see detailed logs

# Load environment variables from .env file
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY", "defaultopenaikey")
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
redis_client = redis.Redis(host='localhost', port=6379, db=0)

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

    # Extract and log the latest message
    try:
        latest_message = incoming_request_data['messages'][-1]['content']
        logging.info(f'Latest message from Vapi: {latest_message}')
    except (KeyError, IndexError, TypeError) as e:
        logging.error("Failed to extract the latest message due to improper data structure.")
        raise HTTPException(status_code=400, detail=f"Error in message data: {str(e)}")

    # Set up the API client using extracted credentials
    user_api = ExtendedRESTClient(base_url, user_api_key, debug)

    # Check for streaming and process accordingly
    streaming = incoming_request_data.get("stream", True)
    if streaming:
        try:
            memgpt_response_stream = user_api.send_message_to_agent_streamed(default_agent_id, latest_message)
            logging.info(f'Sending request to MEMGPT with agent ID {default_agent_id}')
            return StreamingResponse(
                #generate_memgpt_streaming_response(memgpt_response_stream),
                response_stream(memgpt_response_stream),
                media_type="text/event-stream",
            )
        except Exception as e:
            logging.error(f"Error during streaming response: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Handle non-streaming scenario if applicable
        logging.info(f'Streaming not set to True, handling non-streaming scenario: exiting')



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


async def response_stream(memgpt_response_stream):
    max_retries = 10
    retry_count = 0
    while retry_count < max_retries:
        try:
            #memgpt_response_stream = user_api.send_message_to_agent_streamed(agent_id, message)
            async for chunk in memgpt_response_stream:
                data_content = json.loads(chunk.lstrip("data: "))
                
                # Checking for the presence of an 'internal_error' key
                if 'internal_error' in data_content:
                    error_message = data_content['internal_error']
                    if "423: Agent" in error_message:
                        yield create_response_chunk('Agent is currently busy, please wait...')
                        await asyncio.sleep(2)  # Wait before retrying
                        break  # Break the current stream and retry
                    else:
                        yield create_response_chunk('An unnamed error occurred: ' + error_message)
                elif 'assistant_message' in data_content:
                    yield create_response_chunk(data_content['assistant_message'], data_content.get("end_of_conversation", False))
                elif 'function_call' in data_content:
                    yield create_response_chunk('Function Call')
                elif 'function_return':
                    yield create_response_chunk('Function Return')
                elif 'internal_monologue' in data_content:
                    yield create_response_chunk('Internal Monologue')
                else:
                    yield create_response_chunk('Processing...') #probably can skip this or just log it

        except Exception as e:
            yield create_response_chunk(f'Unexpected error, trying again: {str(e)}')
            await asyncio.sleep(2)

        retry_count += 1

    if retry_count >= max_retries:
        yield create_response_chunk('Failed after multiple attempts')


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

async def fetch_new_messages(user_api: ExtendedRESTClient, agent_id: uuid.UUID, last_message_id: uuid.UUID, interval=5):
    while True:
        response = user_api.get_messages(agent_id, after=last_message_id, limit=10)  # Fetch new messages
        if 'messages' in response and response['messages']:
            last_message_id = response['messages'][-1]['id']  # Update last_message_id to the latest
            user_facing_messages = extract_assistant_messages(response['messages'])

            for message in user_facing_messages:
                formatted_message = create_response_chunk(message)
                yield formatted_message

            if not user_facing_messages:
                # Optionally yield a message if no relevant assistant messages were found
                yield create_response_chunk("No new relevant messages at the moment.", end_of_conversation=True)

        else:
            # Send a completion event if no new messages are available
            yield create_response_chunk("No new messages at the moment.", end_of_conversation=True)
            break  # Break or keep alive depending on desired behavior

        await asyncio.sleep(interval)  # Polling interval

def extract_assistant_messages(messages):
    extracted_messages = []
    for message in messages:
        if message.get('role') == 'assistant' and message.get('tool_calls'):
            for tool_call in message['tool_calls']:
                if tool_call.get('type') == 'function' and tool_call['function']['name'] == 'send_message':
                    try:
                        function_args = json.loads(tool_call['function']['arguments'])
                        user_message = function_args.get('message')
                        if user_message:
                            extracted_messages.append(user_message)
                    except json.JSONDecodeError:
                        print("Error decoding the function arguments JSON.")
    return extracted_messages

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




@app.post("/memgpt-sse-old2/chat/completions")
async def custom_memgpt_sse_handler(request: Request):
    # Extract the full incoming request data
    # incoming_request_data = await request.json()
    # logging.info(f'Full incoming request data: {incoming_request_data}')
    try:
        user_api_key, agent_id, latest_message = await extract_request_data(request)
        logging.info("Extracted data - User API Key: %s, Default Agent ID: %s, Latest Message: %s",
                     user_api_key, agent_id, latest_message)
    except HTTPException as he:
        logging.error("Failed to extract request data: %s", str(he))
        raise he

    # Set up the API client using extracted credentials
    user_api = ExtendedRESTClient(base_url, user_api_key, debug)


    try:
        # Fetch the latest message to determine the last_message_id to start streaming from
        try:
            latest_messages_response =  await user_api.aget_messages(agent_id, limit=1)
            if latest_messages_response is None or 'messages' not in latest_messages_response or not latest_messages_response['messages']:
                logging.warning("No messages fetched or empty messages list")
                last_message_id = None
            else:
                try:
                    last_message_id = uuid.UUID(latest_messages_response['messages'][-1]['id'])
                    logging.info("Latest message ID: %s", last_message_id)
                except (ValueError, TypeError, KeyError) as e:
                    logging.error(f"Error converting last message ID to UUID: {str(e)}")
                    last_message_id = None
                    logging.warning("No messages found for agent_id: %s", agent_id)
        except Exception as e:
            logging.error("Failed to fetch latest messages: %s", str(e))
            raise HTTPException(status_code=500, detail="Failed to fetch latest messages")

        # Send a new message based on the latest context
        send_message_task = asyncio.create_task(
            user_api.asend_message(agent_id, latest_message, "user", False)
        )

        # Start streaming response immediately after fetching the latest message ID
        streaming_response = StreamingResponse(
            fetch_new_messages(user_api, agent_id, last_message_id, interval=2),
            media_type="text/event-stream"
        )

        # Optionally, await the send_message_task if you need to ensure it completes successfully
        try:
            response = await send_message_task
            if not response or 'id' not in response:
                logging.error("Failed to send message or invalid response: %s", response)
                await user_api.close()
                raise HTTPException(status_code=500, detail="Failed to send message or fetch message ID")
        except Exception as e:
            logging.error("Error during message sending task: %s", str(e))
            raise HTTPException(status_code=500, detail="Error during message sending task")

        logging.info("Streaming response setup completed.")
        return streaming_response
    except Exception as e:
        logging.error("Error during custom_memgpt_sse_handler: %s", str(e))
        raise HTTPException(status_code=500, detail="Error during custom_memgpt_sse_handler")
    finally:
        await user_api.close()



### REDIS based queue version ###
### REDIS QUEU app ###
