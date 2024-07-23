import logging
import os
import traceback
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from dotenv import load_dotenv
# # Add the ella_dbo path to sys.path
import sys
ella_dbo_path = os.path.expanduser("~/dev/ella-ai/ella_dbo")
sys.path.insert(0, ella_dbo_path)
# # Attempt to import the db_manager functions
try:
    from db_manager import (
        create_connection,
        get_user_data_by_field,
        #get_all_user_data_by_memgpt_id,
        close_connection
    )
    print("Successfully imported from db_manager located in ~/dev/ella-ai/ella_dbo.")
except ImportError as e:
    print("Error: Unable to import db_manager. Check your path and module structure.")
    raise e
# Load environment variables from .env file
load_dotenv()
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send"
]
GMAIL_TOKEN_PATH = os.path.expanduser("~/.memgpt/gmail_token.json")

def send_email_message(self, memgpt_user_id: str, subject: str = "Hello!", body: str = "Hello, this is a test email.", message_id: str = None) -> str:
    """
    Send an email message via the Gmail API using a MemGPT user ID.

    Args:
        memgpt_user_id (str): The MemGPT user ID stored in the database.
        subject (str): The subject of the email. Default is "Hello!".
        body (str): The email message content to send. Default is "Hello, this is a test email."
        message_id (str, optional): The original message ID for referencing the original email thread. If provided, 
                                    this message will be considered a reply and the subject will be prefixed with 'RE:'.

    Returns:
        str: The status message indicating success or failure.
    """
    # Function to retrieve the sender's email address
    def get_sender_email(service):
        try:
            profile = service.users().getProfile(userId='me').execute()
            return profile['emailAddress']
        except Exception as e:
            logging.error(f"Error retrieving sender's email: {e}")
            traceback.print_exc()
            return None

    # Function to retrieve the original email subject and content
    def retrieve_original_email(service, msg_id):
        try:
            message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            parts = payload.get('parts', [])
            original_subject = "[Original subject not available]"
            original_body = "[Original email content not available]"

            # Extract original subject from headers
            for header in headers:
                if header.get('name', '').lower() == 'subject':
                    original_subject = header.get('value', "[Original subject not available]")

            # Extract original body
            if parts:
                data = parts[0].get('body', {}).get('data', '')
            else:
                data = payload.get('body', {}).get('data', '')

            if data:
                original_body = base64.urlsafe_b64decode(data).decode('utf-8')

            return original_subject, original_body
        except Exception as e:
            logging.error(f"Error retrieving original email: {e}")
            traceback.print_exc()
            return "[Original subject not available]", "[Failed to retrieve original email]"

    conn = create_connection()
    try:
        # Retrieve user data using MemGPT ID
        #user_data = get_all_user_data_by_memgpt_id(conn, memgpt_user_id)
        user_data = get_user_data_by_field(conn, "memgpt_user_id", memgpt_user_id)
        email = user_data.get('email', None) 
        if not user_data or not email:  
            logging.error("Could not retrieve a valid recipient email address from the database.")
            return "Message failed: No valid recipient email address available."

        recipient_email = email

        # Load Gmail API credentials
        if os.path.exists(GMAIL_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)
        else:
            logging.error("Gmail credentials file not found.")
            return "Message failed: Gmail credentials file not found."

        # Create Gmail API service instance
        service = build("gmail", "v1", credentials=creds)

        # Retrieve the sender's email address
        sender_email = get_sender_email(service)
        if not sender_email:
            logging.error("Could not retrieve the authenticated sender's email address.")
            return "Message failed: Could not retrieve sender email."

        # If a message ID is provided, fetch the original subject and content, then prepend "RE:" to the subject
        if message_id:
            original_subject, original_content = retrieve_original_email(service, message_id)
            subject = f"RE: {original_subject}"
            body = f"{body}\n\n--- Original Message ---\n{original_content}"

        # Build the email message
        message = {
            "raw": base64.urlsafe_b64encode(
                f"From: {sender_email}\nTo: {recipient_email}\nSubject: {subject}\n\n{body}".encode("utf-8")
            ).decode("utf-8")
        }

        try:
            # Send the message via the Gmail API
            sent_message = service.users().messages().send(userId="me", body=message).execute()
            logging.info(f"Message sent to {recipient_email}: {sent_message['id']}")
            return "Message was successfully sent."

        except Exception as e:
            logging.error(f"Failed to send message: {e}")
            traceback.print_exc()
            return f"Message failed to send with error: {str(e)}"

    finally:
        close_connection(conn)

# TEST
# import logging
# import argparse
# #from gmail_messaging import send_email_message

# # Configure logging for output visibility
# logging.basicConfig(level=logging.INFO)

# def main():
#     # Set up command-line argument parsing
#     parser = argparse.ArgumentParser(description="Test the send_email_message function.")
#     parser.add_argument("memgpt_user_id", help="The MemGPT user ID to look up in the database.")
#     parser.add_argument("subject", help="The subject of the email.")
#     parser.add_argument("body", help="The body of the email.")

#     args = parser.parse_args()

#     # Call the `send_email_message` function with arguments
#     result = send_email_message(
#         self=None,  # No `self` needed, pass `None`
#         memgpt_user_id=args.memgpt_user_id,
#         subject=args.subject,
#         body=args.body
#     )

#     logging.info(f"Result: {result}")

# if __name__ == "__main__":
#     main()
