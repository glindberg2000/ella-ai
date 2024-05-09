from fastapi import FastAPI, HTTPException,BackgroundTasks
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import asyncio
import httpx
from email import message_from_bytes
import base64
from ella_dbo.db_manager import (
    create_connection,
    get_user_data_by_email,
    close_connection
)
from dotenv import load_dotenv
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
gmail_app = FastAPI()
logger = logging.getLogger(__name__)

GMAIL_TOKEN_PATH = os.path.expanduser("~/.memgpt/gmail_token.json")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Decode base64url-encoded Gmail message
def decode_base64url(data):
    data += "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data)

import re
from email.utils import parseaddr

def extract_email_address(from_field):
    """
    Extract only the email address from the 'From' field, which may contain a name.
    """
    # Use parseaddr from the email.utils module
    _, email_address = parseaddr(from_field)

    # Alternatively, if additional filtering is needed, use a regex pattern
    if not email_address:
        match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
        if match:
            email_address = match.group(0)

    return email_address

def parse_email(message):
    msg_bytes = decode_base64url(message["raw"])
    email_message = message_from_bytes(msg_bytes)

    # Extract key information
    from_field = email_message["From"]
    from_address = extract_email_address(from_field)
    to_address = email_message["To"]
    subject = email_message["Subject"]
    full_body = ""

    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                full_body += str(part.get_payload(decode=True).decode("utf-8"))
            elif part.get_content_type() == "text/html":
                continue  # Optionally handle HTML parts differently
    else:
        full_body = email_message.get_payload(decode=True).decode("utf-8")

    return {
        "from": from_address,
        "to": to_address,
        "subject": subject,
        "full_body": full_body
    }


async def read_user_by_email(email: str):
    logging.info(f"Attempting to read user by email: {email}")
    conn = await asyncio.to_thread(create_connection)
    try:
        user_data = await asyncio.to_thread(get_user_data_by_email, conn, email)
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

# Asynchronous function for Gmail polling
async def poll_gmail_notifications():
    creds = None
    if os.path.exists(GMAIL_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)

    service = build("gmail", "v1", credentials=creds)
    seen_ids = set()

    while True:
        try:
            messages_result = service.users().messages().list(userId="me", q="is:unread", maxResults=5).execute()
            messages = messages_result.get("messages", [])
            for message in messages:
                if message["id"] not in seen_ids:
                    seen_ids.add(message["id"])
                    msg = service.users().messages().get(userId="me", id=message["id"], format="raw").execute()
                    parsed_email = parse_email(msg)
                    from_email = parsed_email["from"]
                    # Log key information
                    logger.info(f"New Email - From: {from_email}, To: {parsed_email['to']}, "
                                f"Subject: {parsed_email['subject']}, Body: {parsed_email['full_body']}")
                    # Extract user data using the phone number
                    try:
                        user_data = await read_user_by_email(from_email)
                        logging.info(f"User data retrieved successfully within email service: {user_data}")
                        if not user_data or not user_data.get("default_agent_key"):
                            logging.error(f"User not found or default agent key missing for email: {from_email}")
                            continue  # Instead of raising an exception
                        
                        default_agent_key = user_data['default_agent_key']
                        memgpt_user_api_key = user_data['memgpt_user_api_key']
                        logging.info(f"Routing message to agent with default agent key: {default_agent_key}")
                        
                        # Now we have the default agent key, we can route the message
                        await route_reply_to_memgpt_api(parsed_email['full_body'], memgpt_user_api_key, default_agent_key)
                    except HTTPException as he:
                        logging.error(f"HTTP error during Email processing: {he.detail}")
                    except Exception as e:
                        logging.error(f"Unexpected error: {e}")

            await asyncio.sleep(60)  # Wait before next polling attempt
        except Exception as e:
            logger.error(f"Error during Gmail polling: {e}")
            await asyncio.sleep(60)  # Wait before retrying in case of an error

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
        "message": f"[EMAIL MESSAGE NOTIFICATION - you MUST use send_email_message NOT send_message if you want to reply to the text thread] {message}",
    }
    timeout = httpx.Timeout(20.0)  # Increase the timeout to 20 seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            print("Got response:", response.text)
        except Exception as e:
            print("Sending message failed:", str(e))

@asynccontextmanager
async def gmail_app_lifespan(app: FastAPI):
    logger.info("Gmail app startup tasks")
    # Create the background task for polling Gmail notifications
    task = asyncio.create_task(poll_gmail_notifications())
    try:
        yield
    finally:
        logger.info("Gmail app cleanup tasks")
        task.cancel()
