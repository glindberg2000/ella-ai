import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Get paths from environment variables
CREDENTIALS_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'google_api_credentials.json')
GMAIL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gmail_token.json')

# Scopes required for Gmail API
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly"
]

# Initiate the OAuth flow to obtain new credentials for Gmail
def obtain_gmail_credentials(delete_cred_file=False):
    if delete_cred_file and os.path.exists(GMAIL_TOKEN_PATH):
        logging.info("Deleting existing credentials file.")
        os.remove(GMAIL_TOKEN_PATH)

    creds = None
    if os.path.exists(GMAIL_TOKEN_PATH):
        logging.info("Loading existing credentials from gmail_token.json")
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing access token using refresh token")
            creds.refresh(Request())
        else:
            logging.info("No valid credentials found. Initiating reauthorization process.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)

            # Ensure the directory exists
            os.makedirs(os.path.dirname(GMAIL_TOKEN_PATH), exist_ok=True)

            # Save the credentials to the specified path
            with open(GMAIL_TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())

            logging.info(f"New credentials saved to {GMAIL_TOKEN_PATH}")

    return creds

if __name__ == "__main__":
    # Set up argument parsing for the delete_cred_file flag
    parser = argparse.ArgumentParser(description="Obtain or refresh Gmail credentials.")
    parser.add_argument('--d', action='store_true', help="Delete the credentials file before obtaining new credentials.")
    args = parser.parse_args()

    # Run the function to obtain or refresh credentials
    creds = obtain_gmail_credentials(delete_cred_file=args.d)
    logging.info("Script completed successfully.")