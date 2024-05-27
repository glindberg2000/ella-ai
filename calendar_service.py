from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv

from ella_memgpt.extendedRESTclient import ExtendedRESTClient
from memgpt.client.client import RESTClient as memgpt_client
from ella_dbo.db_manager import (
    create_connection,
    get_all_user_data_by_memgpt_id,
    close_connection
)

calendar_app = FastAPI()

# MemGPT connection
load_dotenv()
# Load environment variables from .env file
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
# Load environment variables from .env file
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

debug = True  # Turn on debug mode to see detailed logs
# Context manager to handle the lifespan of the app

# Initialize FastAPI app for Calendar service
calendar_app = FastAPI()

@asynccontextmanager
async def calendar_app_lifespan(calendar_app: FastAPI):
    # Connect to the database
    await create_connection()
    print("Database connected for calendar service.")

    # Here, you could also start any background tasks if needed
    # task = asyncio.create_task(some_background_task())

    try:
        yield
    finally:
        # Cleanup actions
        # if task:
        #     task.cancel()
        #     try:
        #         await task
        #     except asyncio.CancelledError:
        #         print("Background task cancelled.")

        # Disconnect the database
        await close_connection()
        print("Database disconnected for calendar service.")



async def process_with_llm(user_data, notification):
    # Implement LLM processing logic here
    return {"status": "LLM processed", "details": f"Processed notification for user {user_data['username']}"}

# Set the lifespan context for the calendar app
calendar_app.router.lifespan_context = calendar_app_lifespan
