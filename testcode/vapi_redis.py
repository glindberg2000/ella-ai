import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from redis.exceptions import ResponseError
import os
import uuid
import json
import asyncio
import time
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

redis_url = f"redis://:{os.getenv('REDIS_PASSWORD')}@localhost:6379"

@app.on_event("startup")
async def startup_event():
    app.redis = Redis.from_url(redis_url, decode_responses=True, encoding='utf-8')
    logger.info("Application startup, Redis connection established.")

    # Create consumer groups, handling the case where they already exist
    try:
        await app.redis.xgroup_create('voice_inputs', 'processing_group', mkstream=True)
    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info("Consumer group 'processing_group' already exists.")
        else:
            raise e

    try:
        await app.redis.xgroup_create('processed_outputs', 'output_group', mkstream=True)
    except ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info("Consumer group 'output_group' already exists.")
        else:
            raise e
    logging.info("Starting background worker task...")
    asyncio.create_task(worker_process())  # Start the worker as a background task

@app.on_event("shutdown")
async def shutdown_event():
    await app.redis.close()
    logger.info("Application shutdown, Redis connection closed.")

@app.post("/voice-input")
async def receive_and_stream_voice_input(request: Request):
    data = await request.json()  # Get the JSON from the request
    user_id = str(uuid.uuid4())  # Generate a user ID
    # Correctly encode the entire data dictionary as JSON
    message_data = json.dumps({'data': data, 'user_id': user_id})

    logger.info(f"Received voice input: {data} for user ID: {user_id}")
    await app.redis.xadd('voice_inputs', {'data': message_data})  # Publish JSON as a string under 'data' key
    logger.info(f"Published to voice_inputs stream: {message_data}")

    return StreamingResponse(results_generator(user_id), media_type="text/event-stream")
    return StreamingResponse(f"data: {json.dumps(message_data)}\n\n", media_type="text/event-stream")


async def results_generator_basic_test(user_id):
    yield "data: init\n\n"
    yield f"data: User ID is {user_id}\n\n"
    
    # Simple fetch from Redis to see if interaction causes issue
    message_data = await app.redis.get('message_id')  # Ensure 'some_key' exists for this test
    if message_data:
        yield f"data: Fetched {message_data}\n\n"

async def results_generator(user_id):
    yield "data: init\n\n"  # Initial message to establish SSE connection

    try:
        start_time = time.time()
        while True:
            # Simulated fetch from Redis or another data source
            await asyncio.sleep(5)  # Simulate data processing/waiting time

            # Here you would typically fetch data, for now, we simulate
            processed_data = f"Processed message for user {user_id}"
            yield f"data: {json.dumps(processed_data)}\n\n"

            # Keep-alive or no-data message
            yield ": keepalive\n\n"

            # Check if 10 seconds have elapsed
            if time.time() - start_time >= 10:
                break

    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"  # Send error details to the client
        logger.error(f"Error in SSE generator: {e}")





  

async def results_generator_bonked(user_id):
    yield "data: init\n\n"  # Initial message to establish SSE connection
    
    stream_name = 'processed_outputs'  # The actual name of your stream for processed results
    group_name = 'output_group'  # The name of the consumer group for this stream
    consumer_name = f'consumer_{user_id}'  # A unique consumer name for each SSE connection (if needed)

    last_id = '>'  # Read only new messages for this consumer

    try:
        while True:
            # Fetch new messages from the processed outputs stream
            messages = await app.redis.xreadgroup(group_name, consumer_name, {stream_name: last_id}, block=1000, count=1)
            if messages:
                for message in messages:
                    _, message_list = message
                    for message_id, values in message_list:
                        # Assuming data is directly the processed result
                        if values.get('user_id') == user_id:  # Optional: filter messages for this user only
                            processed_data = values.get('result', '')
                            yield f"data: {json.dumps(processed_data)}\n\n"
                            # Acknowledge message processing
                            await app.redis.xack(stream_name, group_name, message_id)
            # Wait a bit before querying again to prevent a busy loop if there are no new messages
            await asyncio.sleep(1)
    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"
        logger.error(f"Error in SSE generator: {e}")




async def worker_process():
    while True:
        try:
            messages = await app.redis.xreadgroup('processing_group', 'worker1', streams={'voice_inputs': '>'}, count=1, block=1000)
            for message in messages:
                stream, message_details = message
                for msg_detail in message_details:
                    message_id, data = msg_detail
                    message_data = json.loads(data['data'])  # Decode the JSON string from the 'data' key
                    text = message_data['data']['text']  # Access the 'text' key safely
                    process_result = f"Processed: {text}"
                    await app.redis.xadd('processed_outputs', {'result': process_result, 'user_id': message_data['user_id']})
                    await app.redis.xack('voice_inputs', 'processing_group', message_id)
                    logger.info(f"Processed and published: {process_result}")
        except KeyError as e:
            logger.error(f"Missing key {e} in message data")
        except Exception as e:
            logger.error(f"Error processing message: {e}")



async def results_generator2(user_id):
    # Initial yield to establish the connection
    yield "data: init\n\n" 
    yield f"data: {user_id}\n\n"  # Debugging output

    try:
        while True:
            # Fetch messages intended for this user_id from Redis
            messages = await app.redis.xreadgroup('output_group', user_id, {'processed_outputs': '>'}, count=1, block=1000)
            for message in messages:
                stream, message_details = message
                for message_id, values in message_details:
                    if values['user_id'] == user_id:
                        result = values['result']
                        logger.info(f"Streaming data: {result} for user ID: {user_id}")
                        yield f"data: {json.dumps(result)}\n\n"
                        # Acknowledge the message after successful yield
                        await app.redis.xack('processed_outputs', 'output_group', message_id)
    except Exception as e:
        logger.error(f"Error in SSE generator: {e}")



# async def main():
#     async for data in results_generator("user_id"):
#         # Send the data to the client
#         print(data)

# asyncio.run(main())