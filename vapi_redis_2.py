from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
import uuid
import asyncio
import json
import time
import os
from redis.asyncio import Redis
from redis.exceptions import ResponseError
import logging
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

async def queue_request(request_data):
    """Queue a new request in Redis with a unique `request_id`."""
    request_id = str(uuid.uuid4())
    await app.redis.lpush("requests", json.dumps({
        "request_id": request_id,
        "data": request_data,
        "timestamp": time.time()
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
            continue
        
        request_id = request.get("request_id")
        if not request_id:
            logging.error("Request data missing 'request_id'.")
            continue
        
        logging.info(f"Found request with request_id: {request_id}. Processing...")

        # Simulate processing
        processed_response = await process_request(request)
        
        # Store the processed response with `request_id`
        await app.redis.rpush(f"responses:{request_id}", json.dumps({
            "response": processed_response,
            "timestamp": time.time()
        }))
        logging.info(f"Stored processed response with request_id: {request_id}.")



async def process_request(request):
    """Simulate processing a request with a backend LLM or other processing logic."""
    # Processing logic goes here
    logging.info("Processing request.....Done!")
    time.sleep(2)  # Simulate processing time
    return f"Processed data: {request['data']}"

async def stream_all_responses_chunked(message_data):
    """Stream all processed responses from Redis."""
    max_retries = 30  # Maximum retries before exiting the loop
    retries = 0  # Track the number of retries

    while retries < max_retries:
        logging.info(f"Retry Number: {retries}")
        keys = await app.redis.keys("responses:*")  # Get all response keys

        found_responses = False  # Flag to check if any data is found

        # Process each key and yield responses
        for key in keys:
            responses = await app.redis.lrange(key, 0, -1)

            if responses:
                found_responses = True  # Data is found

                # Yield all responses found in the key
                for response_data in responses:
                    response = json.loads(response_data)
                    if "response" in response:
                        yield f"data: {json.dumps(response['response'])}\n\n"  # Yield data

                    # Remove the response after yielding
                    await app.redis.lrem(key, 1, json.dumps(response))
        
        if found_responses:
            break  # Exit loop if responses are found and processed
        
        retries += 1  # Increment retries if no data is found
        await asyncio.sleep(1)  # Throttle re-checks to avoid busy-waiting



async def stream_all_responses_chunked2(request_id: str):
    """Stream all processed responses from Redis until the specific `request_id` is found."""
    max_retries = 30  # Maximum retries before exiting the loop
    retries = 0  # Track the number of retries

    while retries < max_retries:
        keys = await app.redis.keys("responses:*")  # Get all response keys
        
        found_request_id = False  # Flag to determine if request_id is found
        
        # Process each key and yield responses
        for key in keys:
            responses = await app.redis.lrange(key, 0, -1)
            
            for response_data in responses:
                response = json.loads(response_data)
                if "response" in response:
                    yield f"data: {json.dumps(response['response'])}\n\n"  # Yield the response data
                    
                    # Check if this response has the specific request_id
                    if key.endswith(f":{request_id}"):
                        found_request_id = True
                    
                    # Remove the response after yielding
                    await app.redis.lrem(key, 1, json.dumps(response))
        
        if found_request_id:
            break  # Exit loop if the specific request_id is found
        
        retries += 1  # Increment retries if no data is found
        await asyncio.sleep(1)  # Throttle re-checks to avoid busy-waiting




@app.post("/stream")
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
    return StreamingResponse(stream_all_responses_chunked2(request_id=request_id),media_type="text/event-stream")










# async def stream_all_responses():
#     """Stream all processed responses from Redis."""
#     max_retries = 30  # Maximum retries before exiting the loop
#     retries = 0  # Track the number of retries

#     while retries < max_retries:
#         logging.info(f"Retry Number: {retries}")
#         keys = await app.redis.keys("responses:*")  # Get all response keys

#         found_responses = False  # Flag to check if any data is found
#         all_responses = []  # Collect all responses

#         # Process each key and collect responses
#         for key in keys:
#             responses = await app.redis.lrange(key, 0, -1)

#             if responses:
#                 found_responses = True  # Data is found
#                 # Collect all responses found in the key
#                 for response_data in responses:
#                     response = json.loads(response_data)
#                     if "response" in response:
#                         all_responses.append(f"data: {json.dumps(response['response'])}\n\n")  # Add to collection

#                     # Remove the response after processing
#                     await app.redis.lrem(key, 1, json.dumps(response))

#         if found_responses:
#             yield "".join(all_responses)  # Yield all responses at once
#             break  # Exit loop if responses are found and processed
        
#         retries += 1  # Increment retries if no data is found
#         await asyncio.sleep(1)  # Throttle re-checks to avoid busy-waiting

# import json
# import logging
# import asyncio

# async def stream_all_responses():
#     """Stream all processed responses from Redis."""
#     max_retries = 30  # Maximum retries before exiting the loop
#     retries = 0  # Track the number of retries

#     while retries < max_retries:
#         logging.info(f"Retry Number: {retries}")
#         keys = await app.redis.keys("responses:*")  # Get all response keys

#         all_responses = []  # Collect all responses
#         for key in keys:
#             responses = await app.redis.lrange(key, 0, -1)

#             if responses:
#                 # Collect all responses found in the key
#                 for response_data in responses:
#                     response = json.loads(response_data)
#                     if "response" in response:
#                         logging.info(f"appending response: {response['response']}")
#                         all_responses.append(f"data: {json.dumps(response['response'])}\n\n")  # Add to collection

#                 # After collecting, remove the data
#                 await app.redis.ltrim(key, len(responses), -1)  # Remove all processed data

#         if all_responses:
#             retries = max_retries
#             yield "".join(all_responses)  # Yield all responses at once

#         retries += 1  # Increment retries if no data is found
#         await asyncio.sleep(1)  # Throttle re-checks to avoid busy-waiting

# # This never yields
# async def generate_streaming_response():
#     """
#     Generator function to simulate streaming data.
#     """
#     retry = 0
#     while True:
#         yield f"data: {retry}\n\n"
#         time.sleep
#         retry += 1

# #This only yields all of them at the end of 10 seconds even though the terminal shows it yielding every second
# async def generate_streaming_response2():
#     """
#     Generator function to simulate streaming data.
#     """
#     for message in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
#         yield f"data: {message}\n\n"
#         logging.info(f"Sent message: {message}")
#         time.sleep(1)  # You might adjust or remove this during debugging

# async def async_generator():
#     """Asynchronous generator to yield responses from Redis as a list."""
#     # Get all responses from Redis
#     responses = await app.redis.lrange("responses", 0, -1)  # Fetch all responses

#     if responses:
#         logging.info(f"Found Responses: {responses}")
#         # Yield the entire list of responses in one step
#         yield responses  # Yield as-is without further processing
    
#     await asyncio.sleep(1)  # Optional: Throttle rechecks to avoid busy-waiting



# async def streamer(generator):
#     """Streamer to handle the asynchronous generator without concatenation."""
#     try:
#         # Yield the entire list of responses from the asynchronous generator
#         async for data in generator():
#             # Convert the list to an appropriate format for StreamingResponse
#             logging.info(f"Streamer Data Received from generator: {data}")
#             for item in data:
#                 logging.info(f"Streamer Item: {item}")
#                 yield f"data: {item}\n\n"  # Stream each item from the list separately
    
#     except asyncio.CancelledError:
#         print("Stream cancelled")

# from typing import Generator
# # A generator function to stream data
# def stream_data() -> Generator:
#     for i in range(10):
#         time.sleep(1)  # Introduce a 1-second pause between each yield
#         yield f"data: {i}\n\n"
