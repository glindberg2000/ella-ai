import logging
import os
import traceback
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
# Add the ella_dbo path to sys.path
import sys
ella_dbo_path = os.path.expanduser("~/dev/ella_ai/ella_dbo")
sys.path.insert(0, ella_dbo_path)

# Attempt to import the db_manager functions
try:
    from db_manager import (
        create_connection,
        get_all_user_data_by_memgpt_id,
        close_connection
    )
    print("Successfully imported from db_manager located in ~/dev/ella_ai/ella_dbo.")
except ImportError as e:
    print("Error: Unable to import db_manager. Check your path and module structure.")
    raise e
import os
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]
GMAIL_TOKEN_PATH = os.path.expanduser("~/.memgpt/gmail_token.json")
#DEFAULT_SENDER_EMAIL = os.getenv("DEFAULT_SENDER_EMAIL", "default@example.com")

def send_email_message(self, memgpt_user_id: str, subject: str = "Hello!", body: str = "Hello, this is a test email.") -> str:
    """
    Send an email message via the Gmail API using a MemGPT user ID.

    Args:
        memgpt_user_id (str): The MemGPT user ID stored in the database.
        subject (str): The subject of the email. Default is "Hello!".
        body (str): The email message content to send. Default is "Hello, this is a test email."

    Returns:
        str: The status message indicating success or failure.
    """
    # Function to retrieve the sender's email address from the Gmail profile
    def get_sender_email(service):
        """
        Retrieve the authenticated sender's email address using the Gmail API.

        Args:
            service: The Gmail API service instance.

        Returns:
            str: The authenticated user's email address.
        """
        try:
            # Use the 'users.getProfile' endpoint to get the authenticated user's email address
            profile = service.users().getProfile(userId='me').execute()
            sender_email = profile['emailAddress']
            return sender_email

        except Exception as e:
            logging.error(f"Error retrieving sender's email: {e}")
            traceback.print_exc()
            return None

    conn = create_connection()
    try:
        # Retrieve the user data associated with the MemGPT user ID
        user_data = get_all_user_data_by_memgpt_id(conn, memgpt_user_id)
        if not user_data or not user_data[2]:  # Assuming recipient email is at index 2 in user data
            logging.error("Could not retrieve a valid recipient email address from the database.")
            return "Message failed: No valid recipient email address available."

        recipient_email = user_data[2]

        # Load the Gmail API credentials
        if os.path.exists(GMAIL_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)
        else:
            logging.error("Gmail credentials file not found.")
            return "Message failed: Gmail credentials file not found."

        # Create a Gmail API service instance
        service = build("gmail", "v1", credentials=creds)

        # Retrieve the sender's email address
        sender_email = get_sender_email(service)
        if not sender_email:
            logging.error("Could not retrieve the authenticated sender's email address.")
            return "Message failed: Could not retrieve sender email."

        # Build the email message
        message = {
            "raw": base64.urlsafe_b64encode(
                f"From: {sender_email}\nTo: {recipient_email}\nSubject: {subject}\n\n{body}".encode("utf-8")
            ).decode("utf-8")
        }

        try:
            # Send the message using the Gmail API
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
