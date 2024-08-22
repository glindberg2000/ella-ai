# # #gmail_service.py
import os
import asyncio
import logging
import base64
import re
from dotenv import load_dotenv
from fastapi import HTTPException
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.utils import parseaddr
from google_utils import GoogleEmailUtils
from memgpt_email_router import MemGPTEmailRouter
from ella_dbo.db_manager import get_user_data_by_field
from google_service_manager import google_service_manager

# Load environment variables from .env file
load_dotenv()

# Constants
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MemGPTEmailRouter
email_router = MemGPTEmailRouter()

async def decode_email_content(raw_message: str) -> str:
    try:
        return base64.urlsafe_b64decode(raw_message).decode('utf-8')
    except UnicodeDecodeError:
        return base64.urlsafe_b64decode(raw_message).decode('ISO-8859-1')

def parse_email_message(message: dict) -> dict:
    if 'payload' not in message or 'headers' not in message['payload']:
        return None

    headers = message['payload']['headers']
    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')
    from_header = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown Sender')
    to_header = next((header['value'] for header in headers if header['name'].lower() == 'to'), 'Unknown Recipient')

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

async def poll_gmail_notifications() -> None:
    logger.info("Starting Gmail polling task")
    
    try:
        service = google_service_manager.get_gmail_service()
        if not service:
            logger.error("Gmail service is not available. Exiting...")
            return

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
                        if not parsed_email['from'].endswith('@google.com'):
                            try:
                                from_email = parsed_email['from'].split('<')[-1].split('>')[0]
                                user_data = await read_user_by_email(from_email)
                                if user_data and user_data.get("default_agent_key"):
                                    default_agent_key = user_data['default_agent_key']
                                    memgpt_user_api_key = user_data['memgpt_user_api_key']
                                    context = {
                                        "message_id": message_id,
                                        "subject": parsed_email['subject'],
                                        "from": from_email,
                                        "body": parsed_email['body']
                                    }
                                    await email_router.generate_and_send_email(
                                        to_email=from_email,
                                        subject=f"Re: {parsed_email['subject']}",
                                        context=context,
                                        memgpt_user_api_key=memgpt_user_api_key,
                                        agent_key=default_agent_key,
                                        message_id=message_id,
                                        api_key=API_KEY  # Add API key here
                                    )
                                else:
                                    logger.warning(f"User not found or default agent key missing for email: {from_email}")
                            except Exception as e:
                                logger.error(f"Error processing email: {str(e)}")

                    service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()

            except RefreshError as e:
                logger.error(f"Token refresh error: {e}. Reinitializing Gmail service...")
                service = google_service_manager.get_gmail_service()
            except Exception as e:
                logger.error(f"Error during email processing: {str(e)}")

            logger.info("Finished checking for new emails. Waiting for 60 seconds before the next check.")
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"Error during Gmail polling: {str(e)}")
        await asyncio.sleep(60)
def extract_email_address(from_field: str) -> str:
    _, email_address = parseaddr(from_field)
    if not email_address:
        match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
        if match:
            email_address = match.group(0)
    return email_address

async def read_user_by_email(email: str) -> dict:
    """
    Asynchronously read user data by email using the updated db_manager.
    
    Args:
    email (str): The email address of the user to fetch.
    
    Returns:
    dict: User data if found.
    
    Raises:
    HTTPException: If user is not found or if a database error occurs.
    """
    logging.info(f"Attempting to read user by email: {email}")
    
    def db_operation():
        try:
            user_data = get_user_data_by_field("email", email)
            if user_data:
                logging.info(f"User data retrieved successfully: {user_data}")
                return user_data
            else:
                logging.warning(f"User not found for email: {email}")
                return None
        except Exception as e:
            logging.error(f"Database error occurred while fetching user: {e}")
            raise

    try:
        user_data = await asyncio.get_event_loop().run_in_executor(None, db_operation)
        if user_data is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Main function to run the polling task directly
if __name__ == "__main__":
    asyncio.run(poll_gmail_notifications())
# from http.client import HTTPException
# import os
# import asyncio
# import logging
# import base64
# import re
# from dotenv import load_dotenv
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from email.utils import parseaddr
# from google_utils import GoogleEmailUtils
# from memgpt_email_router import MemGPTEmailRouter
# from ella_dbo.db_manager import get_user_data_by_field

# # Load environment variables from .env file
# load_dotenv()

# # Constants
# base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
# GMAIL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gmail_token.json')
# GOOGLE_CREDENTIALS_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'google_api_credentials.json')
# GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# # Logging configuration
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Initialize the MemGPTEmailRouter
# email_router = MemGPTEmailRouter()

# async def decode_email_content(raw_message: str) -> str:
#     try:
#         return base64.urlsafe_b64decode(raw_message).decode('utf-8')
#     except UnicodeDecodeError:
#         return base64.urlsafe_b64decode(raw_message).decode('ISO-8859-1')

# def parse_email_message(message: dict) -> dict:
#     if 'payload' not in message or 'headers' not in message['payload']:
#         return None

#     headers = message['payload']['headers']
#     subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')
#     from_header = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown Sender')
#     to_header = next((header['value'] for header in headers if header['name'].lower() == 'to'), 'Unknown Recipient')

#     body = message['payload'].get('body', {}).get('data', '')
#     if body:
#         body = base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
#     else:
#         parts = message['payload'].get('parts', [])
#         for part in parts:
#             if part['mimeType'] == 'text/plain':
#                 body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
#                 break

#     return {
#         'subject': subject,
#         'from': from_header,
#         'to': to_header,
#         'body': body
#     }

# async def poll_gmail_notifications() -> None:
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
#                         if not parsed_email['from'].endswith('@google.com'):
#                             try:
#                                 from_email = parsed_email['from'].split('<')[-1].split('>')[0]
#                                 user_data = await read_user_by_email(from_email)
#                                 if user_data and user_data.get("default_agent_key"):
#                                     default_agent_key = user_data['default_agent_key']
#                                     memgpt_user_api_key = user_data['memgpt_user_api_key']
#                                     context = {
#                                         "message_id": message_id,
#                                         "subject": parsed_email['subject'],
#                                         "from": from_email,
#                                         "body": parsed_email['body']
#                                     }
#                                     await email_router.generate_and_send_email(
#                                         to_email=from_email,
#                                         subject=f"Re: {parsed_email['subject']}",
#                                         context=context,
#                                         memgpt_user_api_key=memgpt_user_api_key,
#                                         agent_key=default_agent_key,
#                                         message_id=message_id,
#                                         #is_reply=True  # Ensure we're treating this as a reply
#                                     )
#                                 else:
#                                     logger.warning(f"User not found or default agent key missing for email: {from_email}")
#                             except Exception as e:
#                                 logger.error(f"Error processing email: {str(e)}")

#                     service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()

#             except Exception as e:
#                 logger.error(f"Error during email processing: {str(e)}")

#             logger.info("Finished checking for new emails. Waiting for 60 seconds before the next check.")
#             await asyncio.sleep(60)
#     except Exception as e:
#         logger.error(f"Error during Gmail polling: {str(e)}")
#         await asyncio.sleep(60)

# def extract_email_address(from_field: str) -> str:
#     _, email_address = parseaddr(from_field)
#     if not email_address:
#         match = re.search(r'[\w\.-]+@[\w\.-]+', from_field)
#         if match:
#             email_address = match.group(0)
#     return email_address


# async def read_user_by_email(email: str) -> dict:
#     """
#     Asynchronously read user data by email using the updated db_manager.
    
#     Args:
#     email (str): The email address of the user to fetch.
    
#     Returns:
#     dict: User data if found.
    
#     Raises:
#     HTTPException: If user is not found or if a database error occurs.
#     """
#     logging.info(f"Attempting to read user by email: {email}")
    
#     def db_operation():
#         try:
#             user_data = get_user_data_by_field("email", email)
#             if user_data:
#                 logging.info(f"User data retrieved successfully: {user_data}")
#                 return user_data
#             else:
#                 logging.warning(f"User not found for email: {email}")
#                 return None
#         except Exception as e:
#             logging.error(f"Database error occurred while fetching user: {e}")
#             raise

#     try:
#         user_data = await asyncio.get_event_loop().run_in_executor(None, db_operation)
#         if user_data is None:
#             raise HTTPException(status_code=404, detail="User not found")
#         return user_data
#     except HTTPException:
#         raise
#     except Exception as e:
#         logging.error(f"An unexpected error occurred: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")

# # Main function to run the polling task directly
# if __name__ == "__main__":
#     asyncio.run(poll_gmail_notifications())

