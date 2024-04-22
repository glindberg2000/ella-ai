
import asyncio
import json
from fastapi import FastAPI, Response, Request
from starlette.responses import StreamingResponse
import json
import asyncio
import os
import dotenv
from redis.asyncio import Redis
from redis.exceptions import ResponseError
from typing import Optional, List

app = FastAPI()

redis_url = f"redis://:{os.getenv('REDIS_PASSWORD')}@localhost:6379"

@app.on_event("startup")
async def startup_event():
    app.redis = Redis.from_url(redis_url, decode_responses=True, encoding='utf-8')
    asyncio.create_task(process_requests())  # Start the worker as a background task

async def enqueue_request(request_data: dict):
    await app.redis.xadd("request_stream", request_data)

@app.post("/v1/completions")
async def completion_endpoint(request_data: dict, response: Response):
    await enqueue_request(request_data)

    # Set the appropriate headers for Server-Sent Events
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"

    # Return a StreamingResponse to send the SSE back to the client
    return StreamingResponse(get_response(request_data["id"]), response=response)

async def process_requests():
    while True:
        # Get the pending requests from the request_stream
        request = await app.redis.xread({"request_stream": "0-0"}, count=1, block=0)

        if request:
            request_data = request[0][1]

            # Process the request data and generate a response
            # ... (your custom processing logic here)

            response_data = {
                "id": request_data["id"],
                "response": "The generated completion text",
            }

            # Add the response to the response_stream
            await app.redis.xadd("response_stream", response_data)



async def get_response(request_id: str):
    while True:
        # Get the responses from the response_stream
        response = await app.redis.xread({"response_stream": f"{request_id}"}, count=1, block=0)

        if response:
            response_data = response[0][1]

            if response_data["id"] == request_id:
                yield f"data: {json.dumps(response_data['response'])}\n\n"
                break

        await asyncio.sleep(0.1)



@app.on_event("startup")
async def startup():
    asyncio.create_task(process_requests())
