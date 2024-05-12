

from fastapi import FastAPI, HTTPException, BackgroundTasks
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

# Load environment variables from .env file
load_dotenv()
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
#Context manager to handle the lifespan of the app
gmail_app = FastAPI()
# Constants
GMAIL_TOKEN_PATH = os.path.expanduser("~/.memgpt/gmail_token.json")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Decode base64url-encoded Gmail message
def decode_base64url(data):
    data += "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data)

import re
from email.utils import parseaddr

def extract_email_address(from_field):
    _, email_address = parseaddr(from_field)

    if not email_address:
        match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
        if match:
            email_address = match.group(0)

    return email_address

def parse_email(message):
    msg_bytes = decode_base64url(message["raw"])
    email_message = message_from_bytes(msg_bytes)

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
                continue
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

async def poll_gmail_notifications():
    creds = None
    if os.path.exists(GMAIL_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)

    service = build("gmail", "v1", credentials=creds)

    while True:
        try:
            messages_result = service.users().messages().list(userId="me", q="is:unread", maxResults=25).execute()
            messages = messages_result.get("messages", [])
            for message in messages:
                message_id = message["id"]
                msg = service.users().messages().get(userId="me", id=message_id, format="raw").execute()
                parsed_email = parse_email(msg)
                parsed_email["id"] = message_id
                from_email = parsed_email["from"]
                logger.info(f"New Email - From: {from_email}, To: {parsed_email['to']}, "
                            f"Subject: {parsed_email['subject']}, Body: {parsed_email['full_body']}")

                # Try to read user data, but mark as read even if not found
                try:
                    user_data = await read_user_by_email(from_email)
                    logging.info(f"User data retrieved successfully within email service: {user_data}")
                    if not user_data or not user_data.get("default_agent_key"):
                        logging.error(f"User not found or default agent key missing for email: {from_email}")
                    else:
                        default_agent_key = user_data['default_agent_key']
                        memgpt_user_api_key = user_data['memgpt_user_api_key']
                        logging.info(f"Routing message to agent with default agent key: {default_agent_key}")
                        await route_reply_to_memgpt_api(parsed_email['full_body'], parsed_email['subject'], message_id, memgpt_user_api_key, default_agent_key)
                except HTTPException as he:
                    logging.error(f"HTTP error during Email processing: {he.detail}")
                except Exception as e:
                    logging.error(f"Unexpected error: {e}")

                # Mark the message as read regardless of the database lookup result
                service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()

            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error during Gmail polling: {e}")
            await asyncio.sleep(60)

async def route_reply_to_memgpt_api(message, subject, message_id, memgpt_user_api_key, agent_key):
    url = f"{base_url}/api/agents/{agent_key}/messages"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {memgpt_user_api_key}",
        "Content-Type": "application/json",
    }

    # Embed the original subject and message ID in the text
    formatted_message = (
        f"[EMAIL MESSAGE NOTIFICATION - you MUST use send_email_message NOT send_message if you want to reply to the thread] "
        f"[message_id: {message_id}] "
        f"[subject: {subject}] "
        f"[message: {message}] "
    )

    data = {
        "stream": False,
        "role": "system",
        "message": formatted_message
    }
    timeout = httpx.Timeout(20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            print("Got response:", response.text)
        except Exception as e:
            print("Sending message failed:", str(e))


@asynccontextmanager
async def gmail_app_lifespan(app: FastAPI):
    logger.info("Gmail app startup tasks")
    task = asyncio.create_task(poll_gmail_notifications())
    try:
        yield
    finally:
        logger.info("Gmail app cleanup tasks")
        task.cancel()

