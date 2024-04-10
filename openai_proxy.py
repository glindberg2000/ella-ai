# openai_proxy.py

import json
import os
import time

import httpx
from chainlit.server import app
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from openai import OpenAI
from starlette.responses import StreamingResponse

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

@app.post("/memgpt-sse/chat/completions")
async def custom_memgpt_sse_handler(request: Request):
    incoming_request_data = await request.json()
    print('incoming data:',incoming_request_data)
    latest_message = sanitize_request_for_memgpt(incoming_request_data)
    print('latest message:',latest_message)
    #latest_message = 'how is the weather today?'
    user_api_key = DEFAULT_API_KEY
    agent_id = DEFAULT_AGENT_ID
    user_api = ExtendedRESTClient(base_url, user_api_key)

    streaming = incoming_request_data.get("stream", True)
    if streaming:
        try:
            print('latest message from vapi received:',latest_message)
            memgpt_response_stream = user_api.send_message_to_agent_streamed(agent_id, latest_message)
            return StreamingResponse(
                generate_memgpt_streaming_response(memgpt_response_stream),
                media_type="text/event-stream",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Handle non-streaming scenario if applicable
        pass
# Step 3: Adapting the streaming response generation for MemGPT
# Redefining the updated generate_streaming_response function after the reset
import json

async def generate_memgpt_streaming_response(data_stream):
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
