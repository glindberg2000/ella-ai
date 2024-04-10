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


# @router.post("/openai-proxy")
# async def openai_proxy(request: httpx.Request):
#     async with httpx.AsyncClient() as client:
#         try:
#             openai_response = await client.post(
#                 "https://api.openai.com/v1/completions",
#                 headers={
#                     "Authorization": f"Bearer {OPENAI_API_KEY}",
#                     "Content-Type": "application/json",
#                 },
#                 content=await request.body(),
#                 stream=True
#             )

#             return StreamingResponse(openai_response.aiter_raw(), media_type=openai_response.headers["Content-Type"])

#         except httpx.HTTPStatusError as e:
#             raise HTTPException(status_code=e.response.status_code, detail="Error while contacting OpenAI API.")


# app = FastAPI()
# client = OpenAI()  # Assuming the client is initialized correctly

# @app.post("/api/openai-sse/chat/completions")
# async def custom_llm_openai_sse_handler(request: Request):
#     request_data = await request.json()
#     streaming = request_data.get('stream', False)

#     if streaming:
#         # Simulate a stream of responses
#         chat_completion_stream = client.chat.completions.create(**request_data)

#         async def generate_streaming_response(chat_completion_stream):
#             for part in chat_completion_stream:
#                 yield part.model_dump()  # Assuming a method to dump part of the stream

#         return StreamingResponse(generate_streaming_response(chat_completion_stream), media_type='text/event-stream')
#     else:
#         # Simulate a non-streaming response
#         chat_completion = client.chat.completions.create(**request_data)
#         return Response(content=chat_completion.model_dump_json(), media_type='application/json')


# async def fetch_openai_completion_stream(request_data: dict):
#     """
#     This coroutine sends the incoming request data to OpenAI's completions endpoint
#     and yields the streaming response as server-sent events.
#     """
#     url = "https://api.openai.com/v1/completions"
#     headers = {
#         "Authorization": f"Bearer {openai_api_key}",
#         "Content-Type": "application/json",
#     }

#     async with httpx.AsyncClient() as client:
#         response = await client.post(url, json=request_data, headers=headers)

#         async for line in response.aiter_lines():
#             # Assuming the line is a JSON string; customize as necessary
#             yield f"data: {line}\n\n"

# @app.post("/openai-sse/chat/completions")
# async def custom_llm_openai_sse_handler(request: Request):
#     request_data = await request.json()
#     streaming = request_data.get('stream', True)

#     if streaming:
#         # Generate and return the streaming response
#         chat_completion_stream = fetch_openai_completion_stream(request_data)
#         return StreamingResponse(chat_completion_stream, media_type='text/event-stream')
#     else:
#         # For non-streaming responses, fetch the complete response and return it.
#         # This part would be similar to fetching and returning a regular JSON response.
#         raise HTTPException(status_code=501, detail="Non-streaming mode is not implemented in this example.")

# @app.post("/openai/chat/completions")
# async def custom_model_openai(request: Request):
#     data = await request.json()
#     print("Raw input received from VAPI:", data)

#     # Use the messages from the VAPI request
#     user_messages = data.get('messages', [])

#     # Send request to OpenAI
#     completion = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=user_messages
#     )

#     # Use the json() method to get the response data in JSON serializable format
#     completion_data = completion.model_dump_json()

#     # Log the response being sent back for debugging
#     print("Sending OpenAI response back to VAPI:", completion_data)

#     # Return the OpenAI response directly
#     return JSONResponse(content=completion_data)


# @app.post("/dummy-model/chat/completions")
# async def custom_model_dummy(request: Request):
#     data = await request.json()
#         # Print the raw input received from VAPI for debugging
#     print("Raw input received from VAPI:", data)
#     user_message = data.get("messages", [{}])[-1].get("content", "")

#     # Dummy response mimicking the structured response from your custom AI model
#     response = {
#         "id": "customcmpl-0000XxXxx0XXxXx0x0X0XxX0x0X0000",
#         "object": "chat.completion",
#         "created": 1712373788,
#         "model": "my-custom-model-0001",
#         "choices": [
#             {
#                 "index": 0,
#                 "message": {
#                     "role": "assistant",
#                     "content": f"Received your message: {user_message}. This is a dummy response.",
#                 },
#                 "logprobs": None,
#                 "finish_reason": "stop",
#             }
#         ],
#         "usage": {
#             "prompt_tokens": len(user_message.split()),
#             "completion_tokens": 36,
#             "total_tokens": 60,
#         },
#         'system_fingerprint': 'dummy_fingerprint'  # Placeholder or dynamically generated value
#     }
#     print("Sending response back to VAPI:", json.dumps(response, indent=2))

#     return JSONResponse(content=response)


# Assuming handle_message_from_vapi is properly imported and available
# from your_message_handling_module import handle_message_from_vapi


# @app.post("/custom-model")
# async def custom_model_memgpt(request: Request):
#     data = await request.json()
#     user_message = data.get("messages", [{}])[-1].get("content", "")

#     # Call the function to handle the message and get memGPT's response
#     assistant_message = await handle_message_from_vapi(user_message)

#     # Construct a response in the expected format
#     response = {
#         "id": "customcmpl-0000XxXxx0XXxXx0x0X0XxX0x0X0000",
#         "object": "chat.completion",
#         "created": int(time.time()),  # Use current time for the 'created' field
#         "model": "my-custom-model-0001",
#         "choices": [
#             {
#                 "index": 0,
#                 "message": {
#                     "role": "assistant",
#                     "content": assistant_message,  # Use the actual response from memGPT
#                 },
#                 "logprobs": None,
#                 "finish_reason": "stop",
#             }
#         ],
#         "usage": {
#             "prompt_tokens": len(user_message.split()),
#             "completion_tokens": len(
#                 assistant_message.split()
#             ),  # Adjust based on actual response length
#             "total_tokens": len(user_message.split()) + len(assistant_message.split()),
#         },
#     }

#     return JSONResponse(content=response)
