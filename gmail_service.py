#gmail_service.py
#polls for gmail messages and sends to LLM for response

from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import logging
import os
import asyncio
from functools import partial
import base64
import json
import re
from email.utils import parseaddr
from email.header import decode_header
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from memgpt.client.client import RESTClient, UserMessageResponse
from ella_memgpt.tools.google_utils import GoogleEmailUtils
from typing import Optional, Dict, Union


from ella_dbo.db_manager import (
    create_connection,
    get_user_data_by_field,
    close_connection
)

# Load environment variables from .env file
load_dotenv()

# Constants
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")
GMAIL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gmail_token.json')
GOOGLE_CREDENTIALS_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'google_api_credentials.json')
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
gmail_app = FastAPI()

async def decode_email_content(raw_message: str) -> str:
    """
    Decode the raw email content.
    """
    try:
        # Attempt UTF-8 decoding first
        return base64.urlsafe_b64decode(raw_message).decode('utf-8')
    except UnicodeDecodeError:
        # If UTF-8 fails, try decoding with 'ISO-8859-1'
        return base64.urlsafe_b64decode(raw_message).decode('ISO-8859-1')

def parse_email_message(message: dict) -> dict:
    """
    Parse the email message and extract relevant information.
    """
    if 'payload' not in message or 'headers' not in message['payload']:
        return None

    headers = message['payload']['headers']
    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')
    from_header = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown Sender')
    to_header = next((header['value'] for header in headers if header['name'].lower() == 'to'), 'Unknown Recipient')

    # Decode subject if necessary
    subject = decode_header(subject)[0][0]
    if isinstance(subject, bytes):
        subject = subject.decode('utf-8', errors='ignore')

    body = message['payload'].get('body', {}).get('data', '')
    if body:
        body = base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
    else:
        parts = message['payload'].get('parts', [])
        for part in parts:
            if part['mimeType'] == 'text/plain':
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                break

    return {
        'subject': subject,
        'from': from_header,
        'to': to_header,
        'body': body
    }

# async def poll_gmail_notifications() -> None:
#     """
#     Poll Gmail for new messages and process them.
#     """
#     logger.info("Starting Gmail polling task")
#     creds = None
#     if os.path.exists(GMAIL_TOKEN_PATH):
#         try:
#             creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)
#             logger.info("Successfully loaded credentials from file.")
#         except Exception as e:
#             logger.error(f"Error loading credentials: {e}")
#             return
#     else:
#         logger.error(f"Credentials file not found at path: {GMAIL_TOKEN_PATH}")
#         return

#     if not creds or not creds.valid:
#         logger.error("Gmail Service: Invalid or missing credentials. Ensure you have a valid token.")
#         return

#     try:
#         service = build("gmail", "v1", credentials=creds, cache_discovery=False)
#         user_profile = service.users().getProfile(userId="me").execute()
#         email_address = user_profile.get("emailAddress")
#         logger.info(f"Authenticated Gmail account: {email_address}")

#         while True:
#             try:
#                 logger.info("Checking for new emails...")
#                 messages_result = service.users().messages().list(userId="me", q="is:unread", maxResults=25).execute()
#                 messages = messages_result.get("messages", [])
#                 for message in messages:
#                     message_id = message["id"]
#                     msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
#                     parsed_email = parse_email_message(msg)

#                     if parsed_email:
#                         logger.info(f"New Email - From: {parsed_email['from']}, To: {parsed_email['to']}, "
#                                     f"Subject: {parsed_email['subject']}, Body: {parsed_email['body'][:100]}...")

#                         # Only process emails not from system accounts
#                         if not parsed_email['from'].endswith('@google.com'):
#                             try:
#                                 from_email = parsed_email['from'].split('<')[-1].split('>')[0]
#                                 user_data = await read_user_by_email(from_email)
#                                 if user_data and user_data.get("default_agent_key"):
#                                     default_agent_key = user_data['default_agent_key']
#                                     memgpt_user_api_key = user_data['memgpt_user_api_key']
#                                     await route_reply_to_memgpt_api(parsed_email['body'], parsed_email['subject'],
#                                                                     message_id, memgpt_user_api_key, default_agent_key)
#                                 else:
#                                     logger.warning(f"User not found or default agent key missing for email: {from_email}")
#                             except Exception as e:
#                                 logger.error(f"Error processing email: {str(e)}")

#                     # Mark the message as read
#                     service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()

#             except Exception as e:
#                 logger.error(f"Error during email processing: {str(e)}")

#             logger.info("Finished checking for new emails. Waiting for 60 seconds before the next check.")
#             await asyncio.sleep(60)
#     except Exception as e:
#         logger.error(f"Error during Gmail polling: {str(e)}")
#         await asyncio.sleep(60)

async def poll_gmail_notifications() -> None:
    """
    Poll Gmail for new messages and process them.
    """
    logger.info("Starting Gmail polling task")
    creds = None
    if os.path.exists(GMAIL_TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)
            logger.info("Successfully loaded credentials from file.")
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return
    else:
        logger.error(f"Credentials file not found at path: {GMAIL_TOKEN_PATH}")
        return

    if not creds or not creds.valid:
        logger.error("Gmail Service: Invalid or missing credentials. Ensure you have a valid token.")
        return

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        user_profile = service.users().getProfile(userId="me").execute()
        email_address = user_profile.get("emailAddress")
        logger.info(f"Authenticated Gmail account: {email_address}")

        while True:
            try:
                logger.info("Checking for new emails...")
                messages_result = service.users().messages().list(userId="me", q="is:unread", maxResults=25).execute()
                messages = messages_result.get("messages", [])
                for message in messages:
                    message_id = message["id"]
                    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
                    parsed_email = parse_email_message(msg)
                    if parsed_email:
                        logger.info(f"New Email - From: {parsed_email['from']}, To: {parsed_email['to']}, "
                                    f"Subject: {parsed_email['subject']}, Body: {parsed_email['body'][:100]}...")
                        # Only process emails not from system accounts
                        if not parsed_email['from'].endswith('@google.com'):
                            try:
                                from_email = parsed_email['from'].split('<')[-1].split('>')[0]
                                user_data = await read_user_by_email(from_email)
                                if user_data and user_data.get("default_agent_key"):
                                    default_agent_key = user_data['default_agent_key']
                                    memgpt_user_api_key = user_data['memgpt_user_api_key']
                                    await route_reply_to_memgpt_api(
                                        parsed_email['body'],
                                        parsed_email['subject'],
                                        message_id,
                                        from_email,
                                        memgpt_user_api_key,
                                        default_agent_key
                                    )
                                else:
                                    logger.warning(f"User not found or default agent key missing for email: {from_email}")
                            except Exception as e:
                                logger.error(f"Error processing email: {str(e)}")

                    # Mark the message as read
                    service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()

            except Exception as e:
                logger.error(f"Error during email processing: {str(e)}")

            logger.info("Finished checking for new emails. Waiting for 60 seconds before the next check.")
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"Error during Gmail polling: {str(e)}")
        await asyncio.sleep(60)

        
def extract_email_address(from_field: str) -> str:
    """
    Extract the email address from the 'from' field.
    """
    _, email_address = parseaddr(from_field)

    if not email_address:
        match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
        if match:
            email_address = match.group(0)

    return email_address


async def read_user_by_email(email: str) -> dict:
    """
    Read user data by email from the database in a thread-safe manner.
    """
    logging.info(f"Attempting to read user by email: {email}")
    
    def db_operation():
        conn = create_connection()
        try:
            user_data = get_user_data_by_field(conn, "email", email)
            if user_data:
                logging.info(f"User data retrieved successfully: {user_data}")
                return user_data
            else:
                logging.error("User not found")
                return None
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise e
        finally:
            logging.info("Closing database connection")
            close_connection(conn)

    try:
        # Run the database operation in the default thread pool
        user_data = await asyncio.get_event_loop().run_in_executor(None, db_operation)
        if user_data is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user_data
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# async def route_reply_to_memgpt_api(message: str, subject: str, message_id: str, memgpt_user_api_key: str, default_agent_key: str) -> None:
#     """
#     Route the email reply to the MemGPT API using the RESTClient.
#     """
#     client = RESTClient(base_url=base_url, token=memgpt_user_api_key)
#     formatted_message = (
#         f"[EMAIL MESSAGE NOTIFICATION - you MUST use send_email function call if you want to reply to the thread to the user] "
#         f"[message_id: {message_id}] "
#         f"[subject: {subject}] "
#         f"[message: {message}] "
#     )

#     try:
#         response = client.user_message(agent_id=default_agent_key, message=formatted_message)
#         logging.info(f"MemGPT API response: {response}")
#     except Exception as e:
#         logging.error(f"Sending message to MemGPT API failed: {str(e)}")





logger = logging.getLogger(__name__)

def extract_email_content(response: Union[UserMessageResponse, dict]) -> Optional[str]:
    """
    Extract email content from UserMessageResponse or dictionary response.
    """
    logger.info(f"Attempting to extract email content from response type: {type(response)}")
    
    if isinstance(response, UserMessageResponse):
        messages = response.messages
    elif isinstance(response, dict):
        messages = response.get('messages', [])
    else:
        logger.error(f"Unexpected response type: {type(response)}")
        return None

    for message in messages:
        if isinstance(message, dict) and 'function_call' in message:
            function_call = message['function_call']
            if function_call.get('name') == 'send_message':
                try:
                    arguments = json.loads(function_call['arguments'])
                    return arguments.get('message')
                except json.JSONDecodeError:
                    logger.error("Failed to parse function call arguments as JSON")
    
    logger.error(f"Failed to extract content. Full response: {response}")
    return None

async def route_reply_to_memgpt_api(body: str, subject: str, message_id: str, from_email: str, memgpt_user_api_key: str, agent_key: str) -> None:
    """
    Route the email reply to the MemGPT API for content generation, then send the email directly.
    """
    client = RESTClient(base_url=base_url, token=memgpt_user_api_key)
    
    # sender_name = from_email.split('@')[0].replace('.', ' ').title()
    
    formatted_message = (
        f"[EMAIL MESSAGE NOTIFICATION - Generate a personalized reply to the following email] "
        f"[message_id: {message_id}] "
        f"[subject: {subject}] "
        f"[from email address: {from_email}] "
        f"[message: {body}] "
        f"Please generate a thoughtful reply to this email. Address the sender by their real name, not email name, and respond directly to their question or comment. Do not include a subject line or any email sending instructions in your reply."
    )

    try:
        response = client.user_message(agent_id=agent_key, message=formatted_message)
        logger.info(f"MemGPT API response received: {response}")

        email_content = extract_email_content(response)

        if email_content:
            reply_subject = f"Re: {subject}"

            email_utils = GoogleEmailUtils(GMAIL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)
            result = email_utils.send_email(
                recipient_email=from_email,
                subject=reply_subject,
                body=email_content,
                message_id=message_id
            )

            if result['status'] == 'success':
                logger.info(f"Reply email sent successfully. Message ID: {result['message_id']}")
            else:
                logger.error(f"Failed to send reply email: {result['message']}")
        else:
            logger.error("Failed to extract email content from LLM response")

    except Exception as e:
        logger.error(f"Error in processing or sending reply email: {str(e)}", exc_info=True)

# ... (keep the rest of the code as is)
# ... (keep the rest of the code as is)

@asynccontextmanager
async def gmail_app_lifespan(app: FastAPI):
    """
    Lifespan context manager for the Gmail app.
    """
    logger.info("Gmail app startup tasks")
    background_tasks = BackgroundTasks()
    background_tasks.add_task(poll_gmail_notifications)
    yield {"background_tasks": background_tasks}
    logger.info("Gmail app cleanup tasks")

gmail_app.router.lifespan_context = gmail_app_lifespan

# You can add additional endpoints to the gmail_app if needed
@gmail_app.get("/status")
async def gmail_status():
    return {"status": "running"}


# Main function to run the polling task directly
if __name__ == "__main__":
    import asyncio

    async def main():
        await poll_gmail_notifications()

    asyncio.run(main())