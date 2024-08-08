#twilio_service.py
#handles SMS message endpoint, looksup user info by phone number, sends to LLM for response


from fastapi import FastAPI, Request, HTTPException, Depends
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
import os
import logging
import asyncio
import httpx
from dotenv import load_dotenv

from ella_dbo.db_manager import (
    create_connection,
    get_user_data_by_phone,
    close_connection
)

twilio_app = FastAPI()

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


@asynccontextmanager
async def twilio_app_lifespan(app: FastAPI):
    print("Twilio app initialization tasks")
    # Example: Connect to a database or start a background task
    try:
        yield
    finally:
        print("Twilio app cleanup tasks")
        # Example: Disconnect from a database or stop a background task

@twilio_app.post("/test")
async def test(request: Request):
    headers = await request.headers.items()
    print(headers)
    return JSONResponse(content={"message": "Headers received. Check your console."})

@twilio_app.post("/sms-status")
async def sms_status(request: Request):
    data = await request.json()  # Asynchronously get JSON payload from the request
    logging.info(f"SMS Status Update: {data}")  # Log the data to console or a log file
    return JSONResponse(status_code=200, content={"message": "Status received successfully"})

async def read_user_by_phone(phone_number: str):
    logging.info(f"Attempting to read user by phone: {phone_number}")
    conn = await asyncio.to_thread(create_connection)
    try:
        user_data = await asyncio.to_thread(get_user_data_by_phone, conn, phone_number)
        if user_data:
            logging.info(f"User data retrieved successfully: {user_data}")
            return dict(zip(["memgpt_user_id", "memgpt_user_api_key", "email", "phone", "default_agent_key", "vapi_assistant_id"], user_data))
        else:
            logging.error("User not found")
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise e
    finally:
        logging.info("Closing database connection")
        await asyncio.to_thread(close_connection, conn)



@twilio_app.post("/sms")
async def sms_reply(request: Request):
    form_data = await request.form()
    message_body = form_data.get("Body")
    from_number = form_data.get("From")
    logging.info(f"Received SMS from {from_number}: {message_body}")

    # Extract user data using the phone number
    try:
        user_data = await read_user_by_phone(from_number)
        logging.info(f"User data retrieved successfully within /sms endpoint: {user_data}")
        if not user_data or not user_data.get("default_agent_key"):
            logging.error(f"User not found or default agent key missing for phone number: {from_number}")
            raise HTTPException(status_code=404, detail="User not found or default agent key missing")
        
        default_agent_key = user_data['default_agent_key']
        memgpt_user_api_key=user_data['memgpt_user_api_key']
        logging.info(f"Routing message to agent with default agent key: {default_agent_key}")
        
        # Now we have the default agent key, we can route the message
        await route_reply_to_memgpt_api(message_body, memgpt_user_api_key, default_agent_key)
        return JSONResponse(status_code=200, content={"status": "OK"})
    except HTTPException as he:
        logging.error(f"HTTP error during SMS processing: {he.detail}")
        return JSONResponse(status_code=he.status_code, content={"detail": he.detail})


async def route_reply_to_memgpt_api(message, memgpt_user_api_key, agent_key):
    url = f"{base_url}/api/agents/{agent_key}/messages"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {memgpt_user_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "stream": False,
        "role": "system",
        "message": f"[SMS MESSAGE NOTIFICATION - you MUST use send_text_message NOT send_message if you want to reply to the text thread] {message}",
    }
    timeout = httpx.Timeout(20.0)  # Increase the timeout to 20 seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            print("Got response:", response.text)
        except Exception as e:
            print("Sending message failed:", str(e))