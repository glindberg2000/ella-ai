# Download the helper library from https://www.twilio.com/docs/python/install
import os
import logging
import traceback
import re
from twilio.rest import Client
from dotenv import load_dotenv
from uuid import UUID

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

# Load environment variables from .env file
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Initialize Twilio client once for reuse
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_number = os.getenv("TWILIO_FROM_NUMBER")
client = Client(account_sid, auth_token)

def clean_phone_number(phone_number: str) -> str | None:
    """Cleans and normalizes a phone number to the E.164 format.

    Args:
        phone_number (str): The raw phone number, possibly including country codes and punctuation.

    Returns:
        str or None: The cleaned phone number in E.164 format (e.g., +11234567890), or None if invalid.
    """
    digits_only = re.sub(r'\D', '', phone_number)
    if len(digits_only) == 10:
        return f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        return f"+{digits_only}"
    else:
        return None

def send_text_message(memgpt_user_id: UUID, phone_number: str | None = None, message: str = "Hello!") -> str:
    """Send an SMS message via Twilio using a MemGPT user ID (UUID) or a specific phone number.

    The function will first validate the provided phone number. If a valid number is not given or None is specified,
    it will attempt to retrieve the user's phone number from the database using the provided MemGPT user ID.
    If successful, an SMS message is sent using the Twilio API.

    Args:
        memgpt_user_id (UUID): The MemGPT user ID for which to find the phone number if not provided.
        phone_number (str or None): The recipient's phone number in any format. If None, look up from the DB.
        message (str): The SMS message content to send. Default is "Hello!".

    Returns:
        str: The status message indicating success or failure.
    """
    conn = create_connection()
    try:
        if phone_number is None or clean_phone_number(phone_number) is None:
            user_data = get_all_user_data_by_memgpt_id(conn, str(memgpt_user_id))
            if user_data and user_data[3]:
                phone_number = clean_phone_number(user_data[3])
            else:
                logging.error("Could not retrieve a valid phone number from the database.")
                return "Message failed: No valid phone number available."
        else:
            phone_number = clean_phone_number(phone_number)

        if not phone_number:
            logging.error("Phone number is invalid.")
            return "Message failed: Invalid phone number."

        try:
            # Send the SMS message using Twilio
            message_status = client.messages.create(
                body=str(message),
                from_=from_number,
                to=phone_number
            )
            logging.info(f"Message sent to {phone_number}: {message_status.sid}")
            # Placeholder for updating the database, if required
            # e.g., update_message_status_in_db(conn, memgpt_user_id, message_status.sid)
            return "Message was successfully sent."

        except Exception as e:
            traceback.print_exc()
            return f"Message failed to send with error: {str(e)}"

    finally:
        close_connection(conn)



# def send_text_message(self, phone_number: str, message: str) -> str:
#     """
#     Sends an SMS message to the specified phone number.

#     Args:
#         phone_number (str): The phone number to which the message will be sent.
#         message (str): The contents of the message to send.

#     Returns:
#         str: The status of the text message.
#     """
#     # Load environment variables from .env file
#     load_dotenv()
#     # Set up basic configuration for logging
#     logging.basicConfig(level=logging.INFO)

#     try:
#         # Retrieve environment variables
#         account_sid = os.environ["TWILIO_ACCOUNT_SID"]
#         auth_token = os.environ["TWILIO_AUTH_TOKEN"]

#         # Log the actual values for testing
#         logging.info(f"Twilio account SID: {account_sid}")
#         logging.info(f"Twilio auth token: {auth_token}")

#         # Initialize the Twilio client
#         client = Client(account_sid, auth_token)
#         logging.info("Twilio client initialized successfully.")

#     except KeyError as e:
#         # Log an error message if the environment variables are not set
#         logging.error(f"Environment variable missing: {e}")
#     except Exception as ex:
#         # Log any other errors that may occur
#         logging.error(f"An error occurred: {ex}")


#     from_number = os.getenv("TWILIO_FROM_NUMBER")
#     assert from_number, "From number is not set in the environment."
#     assert phone_number, "No phone number provided to send the message."

#     try:
#         message = client.messages.create(
#             body=str(message),
#             from_=from_number,
#             to=phone_number,  # Use the phone_number argument instead of from the environment
#         )
#         return "Message was successfully sent."

#     except Exception as e:
#         traceback.print_exc()
#         return f"Message failed to send with error: {str(e)}"



# import os
# import traceback

# from twilio.rest import Client


# def send_text_message(self, message: str) -> str:
#     """
#     Sends an SMS message to the user's phone / cellular device.

#     Args:
#         message (str): The contents of the message to send.

#     Returns:
#         str: The status of the text message.
#     """
#     # Find your Account SID and Auth Token at twilio.com/console
#     # and set the environment variables. See http://twil.io/secure
#     account_sid = os.environ["TWILIO_ACCOUNT_SID"]
#     auth_token = os.environ["TWILIO_AUTH_TOKEN"]
#     client = Client(account_sid, auth_token)

#     from_number = os.getenv("TWILIO_FROM_NUMBER")
#     to_number = os.getenv("TWILIO_TO_NUMBER")
#     assert from_number and to_number
#     # assert from_number.startswith("+1") and len(from_number) == 12, from_number
#     # assert to_number.startswith("+1") and len(to_number) == 12, to_number

#     try:
#         message = client.messages.create(
#             body=str(message),
#             from_=from_number,
#             to=to_number,
#         )
#         return "Message was successfully sent."

#     except Exception as e:
#         traceback.print_exc()

#         return f"Message failed to send with error: {str(e)}"
