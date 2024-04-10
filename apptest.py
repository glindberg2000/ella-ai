import asyncio
import json
import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from starlette.responses import StreamingResponse

app = FastAPI()


api_key = os.getenv("OPENAI_API_KEY", "defaultopenaikey")

from fastapi import FastAPI, HTTPException, Request
from openai import OpenAI
from starlette.responses import StreamingResponse

app = FastAPI()
client = OpenAI()


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


# # Initialize HTTPX client globally if you're planning on making asynchronous HTTP requests
# httpx_client = httpx.AsyncClient()

# def sanitize_request_for_openai(request_data: dict) -> dict:
#     """
#     Sanitize the incoming request data for compatibility with OpenAI's API.
#     """
#     sanitized_request = {
#         "model": "gpt-3.5-turbo",  # Adjust according to your needs
#         "messages": request_data.get('messages', []),
#         "stream": True,  # Enable streaming
#     }
#     return sanitized_request

# async def generate_streaming_response(request_data: dict):
#     """
#     Stream responses from OpenAI API.
#     """
#     sanitized_request = sanitize_request_for_openai(request_data)
#     print(sanitized_request)
#     headers = {"Authorization": f"Bearer {api_key}"}
#     async with httpx_client.post('https://api.openai.com/v1/chat/completions', json=sanitized_request, headers=headers) as response:
#         async for line in response.aiter_lines():
#             if line.startswith('data:'):
#                 yield line + "\n\n"

# @app.post("/api/openai-sse/chat/completions")
# async def custom_llm_openai_sse_handler(request: Request):
#     print('received request...')
#     try:
#         print('trying to parse request...',request,'end request...')
#         request_data = await request.json()
#         streaming_response_generator = generate_streaming_response(request_data)
#         return StreamingResponse(streaming_response_generator, media_type='text/event-stream')
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# async def stream_generator(request_data: dict):
#     # Placeholder: Simulate processing and streaming response
#     # In actual implementation, this should interact with your backend/stream source
#     try:
#         for message in ["Message 1", "Message 2", "Message 3"]:
#             # Simulating a delay in streaming messages
#             await asyncio.sleep(1)
#             yield f"data: {json.dumps({'assistant_message': message})}\n\n"
#     except Exception as e:
#         print(f"Error during streaming: {e}")

# @app.post("/api/streaming-endpoint")
# async def custom_streaming_endpoint(request: Request):
#     request_data = await request.json()
#     stream = stream_generator(request_data)  # Adjust based on actual data processing logic
#     return StreamingResponse(stream, media_type="text/event-stream")


# # Ensure to close the HTTPX client when the application shuts down
# @app.on_event("shutdown")
# async def shutdown_event():
#     await httpx_client.aclose()


# from fastapi import FastAPI, HTTPException
# from starlette.responses import StreamingResponse
# from openai import OpenAI
# import asyncio

# app = FastAPI()
# client = OpenAI()

# async def stream_openai_response():
#     try:
#         stream = client.chat.completions.create(
#             model="gpt-4",
#             messages=[{"role": "user", "content": "Say this is a test"}],
#             stream=True,
#         )
#         for chunk in stream:
#             if chunk.choices[0].delta.content is not None:
#                 print('chunk...',chunk.choices[0].delta.content)
#                 yield chunk.choices[0].delta.content
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# async def generate_response():
#     for i in range(5):
#         print(f"Yielding chunk {i}")
#         yield f"Chunk {i}\n"
#         await asyncio.sleep(1)

# def generate_streaming_response(data):
#   """
#   Generator function to simulate streaming data.
#   """
#   for message in data:
#     json_data = message.model_dump_json()
#     yield f"data: {json_data}\n\n"

# @app.post("/stream-data")
# async def stream_data():
#     print("Received request to stream data")
#     try:
#         return StreamingResponse(generate_streaming_response(), media_type="text/plain")
#     except Exception as e:
#         print(f"Error in stream_data: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# async def stream_openai_response():
#     try:
#         stream = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": "Tell me what the meaning of life is"}],
#             stream=True,
#         )
#         for chunk in stream:
#             if chunk.choices[0].delta.content is not None:
#                 print('chunk...',chunk.choices[0].delta.content)
#                 yield chunk.choices[0].delta.content
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/stream-data")
# async def stream_data():
#     print("Received request to stream data")
#     try:
#         return StreamingResponse(stream_openai_response(), media_type="text/plain")
#     except Exception as e:
#         print(f"Error in stream_data: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
