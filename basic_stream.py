from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse
import asyncio
from typing import Generator


app = FastAPI()

async def stream_data():
    for i in range(10):
        await asyncio.sleep(1)  # 1-second delay between yields
        yield f"data: {i}\n\n"

@app.get("/stream/")
async def stream():
    return StreamingResponse(stream_data(), media_type="text/event-stream")






# Generator function to stream data with a counter and delay
async def stream_data_counter(counter_start: int) -> Generator:
    for i in range(counter_start, counter_start + 10):
        await asyncio.sleep(1)  # 1-second delay between yields
        yield f"data: {i}\n\n"

# Define a POST endpoint that streams back the data
@app.post("/stream/")
async def stream_post(data: dict = Body(...)):
    counter_start = data.get("counter_start", 0)
    return StreamingResponse(stream_data_counter(counter_start), media_type="text/event-stream")


