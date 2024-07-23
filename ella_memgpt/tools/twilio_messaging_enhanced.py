# Download the helper library from https://www.twilio.com/docs/python/install
import re
import os
import logging
import traceback
from twilio.rest import Client
from dotenv import load_dotenv
from typing import Optional

# Add the ella_dbo path to sys.path
import sys
ella_dbo_path = os.path.expanduser("~/dev/ella-ai/ella_dbo")
sys.path.insert(0, ella_dbo_path)

# Attempt to import the db_manager functions
try:
    from db_manager import (
        create_connection,
        get_all_user_data_by_memgpt_id,
        close_connection
    )
    print("Successfully imported from db_manager located in ~/dev/ella-ai/ella_dbo.")
except ImportError as e:
    print("Error: Unable to import db_manager. Check your path and module structure.")
    raise e

# Load environment variables from .env file
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Initialize Twilio client once for reuse
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_number = os.getenv("TWILIO_FROM_NUMBER")
client = Client(account_sid, auth_token)

def send_text_message(self, memgpt_user_id: str, phone_number: Optional[str] = None, message: str = "Hello!") -> str:
    """Send an SMS message via Twilio using a MemGPT user ID or a specific phone number.

    This function will first validate the provided phone number. If a valid number is not given or None is specified,
    it will attempt to retrieve the user's phone number from the database using the provided MemGPT user ID.
    If successful, an SMS message is sent using the Twilio API.

    Args:
        memgpt_user_id (str): The MemGPT user ID, stored in the DB as a string (UUID format).
        phone_number (Optional[str]): The recipient's phone number in any format. If None, look up from the DB.
        message (str): The SMS message content to send. Default is "Hello!".

    Returns:
        str: The status message indicating success or failure.
    """
    def clean_phone_number_inline(phone: Optional[str]) -> str | None:
        """Cleans and normalizes a phone number to the E.164 format.

        Args:
            phone (Optional[str]): The raw phone number.

        Returns:
            str or None: The cleaned phone number in E.164 format or None if invalid.
        """
        if phone is None:
            return None

        digits_only = re.sub(r'\D', '', phone)
        if len(digits_only) == 10:
            return f"+1{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            return f"+{digits_only}"
        else:
            return None

    conn = create_connection()
    try:
        if phone_number is None or clean_phone_number_inline(phone_number) is None:
            user_data = get_all_user_data_by_memgpt_id(conn, memgpt_user_id)
            if user_data and user_data[3]:
                phone_number = clean_phone_number_inline(user_data[3])
            else:
                logging.error("Could not retrieve a valid phone number from the database.")
                return "Message failed: No valid phone number available."
        else:
            phone_number = clean_phone_number_inline(phone_number)

        if not phone_number:
            logging.error("Phone number is invalid.")
            return "Message failed: Invalid phone number."

        try:
            message_status = client.messages.create(
                body=str(message),
                from_=from_number,
                to=phone_number
            )
            logging.info(f"Message sent to {phone_number}: {message_status.sid}")
            return "Message was successfully sent."

        except Exception as e:
            traceback.print_exc()
            return f"Message failed to send with error: {str(e)}"

    finally:
        close_connection(conn)

