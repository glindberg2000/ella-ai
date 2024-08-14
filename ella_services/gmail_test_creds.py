import os
import logging
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables from .env file
load_dotenv()

# Constants
GMAIL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gmail_token.json')
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gmail_credentials():
    """
    Test the Gmail credentials to ensure they are valid.
    """
    logger.info("Starting Gmail credentials test")
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
        logger.info("Gmail credentials are valid.")
    except HttpError as e:
        logger.error(f"HTTP error occurred: {e}")
    except Exception as e:
        logger.error(f"Error during Gmail credentials test: {str(e)}")

if __name__ == "__main__":
    test_gmail_credentials()
