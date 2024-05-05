from fastapi import FastAPI, Request, status, HTTPException, Depends
from fastapi.responses import JSONResponse
import requests
import os
import sys
import logging
import sqlite3
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
    conn = await asyncio.to_thread(create_connection)
    try:
        user_data = await asyncio.to_thread(get_user_data_by_phone, conn, phone_number)
        if user_data:
            return dict(zip(["memgpt_user_id", "api_key", "email", "phone", "default_agent_key", "vapi_assistant_id"], user_data))
        else:
            raise HTTPException(status_code=404, detail="User not found")
    finally:
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
        if not user_data or not user_data.get("default_agent_key"):
            logging.error(f"User not found or default agent key missing for phone number: {from_number}")
            raise HTTPException(status_code=404, detail="User not found or default agent key missing")
        
        default_agent_key = user_data['default_agent_key']
        logging.info(f"Routing message to agent with default agent key: {default_agent_key}")
        
        # Now we have the default agent key, we can route the message
        await route_reply_to_memgpt_api(message_body, default_agent_key)
        return JSONResponse(status_code=200, content={"status": "OK"})
    except HTTPException as he:
        logging.error(f"HTTP error during SMS processing: {he.detail}")
        return JSONResponse(status_code=he.status_code, content={"detail": he.detail})


async def route_reply_to_memgpt_api(message, agent_key):
    url = f"{base_url}/api/agents/{agent_key}/messages"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {master_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "stream": False,
        "role": "system",
        "message": f"[SMS MESSAGE NOTIFICATION - you MUST use send_text_message NOT send_message if you want to reply to the text thread] {message}",
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            print("Got response:", response.text)
        except Exception as e:
            print("Sending message failed:", str(e))
# async def read_user_by_phone(phone_number: str):
#     conn = await asyncio.to_thread(create_connection)
#     try:
#         user_data = await asyncio.to_thread(get_user_data_by_phone, conn, phone_number)
#         if user_data:
#             return { "user_data": dict(zip(["memgpt_user_id", "api_key", "email", "phone", "default_agent_key", "vapi_assistant_id"], user_data)) }
#         raise HTTPException(status_code=404, detail="User not found")
#     finally:
#         await asyncio.to_thread(close_connection, conn)

# @twilio_app.post("/sms")
# async def sms_reply(request: Request):
#     form_data = await request.form()
#     message_body = form_data.get("Body")
#     from_number = form_data.get("From")

#     msg_str = f"New message from {from_number}: {message_body}"
#     print(msg_str)

#     route_reply_to_memgpt_api(msg_str)
#     return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "OK"})


# def route_reply_to_memgpt_api(message):
#     url = f"{MEMGPT_SERVER_URL}/api/agents/{MEMGPT_AGENT_ID}/messages"
#     headers = {
#         "accept": "application/json",
#         "authorization": f"Bearer {MEMGPT_TOKEN}",
#         "content-type": "application/json",
#     }
#     data = {
#         "stream": False,
#         "role": "system",
#         "message": f"[SMS MESSAGE NOTIFICATION - you MUST use send_text_message NOT send_message if you want to reply to the text thread] {message}",
#     }

#     try:
#         response = requests.post(url, headers=headers, json=data)
#         print("Got response:", response.text)
#     except Exception as e:
#         print("Sending message failed:", str(e))
#         logger.error("Sending message failed:", exc_info=True)