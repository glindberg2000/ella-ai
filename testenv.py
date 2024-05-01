from dotenv import load_dotenv
import os
import logging

# Load environment variables from a .env file
load_dotenv()

# Ensure logging is set up to print out debug information
logging.basicConfig(level=logging.DEBUG)

def get_phone_from_email(email):
    # Convert the email to a format suitable for environment variable names
    key = 'USER_' + email.replace('@', '_').replace('.', '_') + '_PHONE'
    # Convert the entire key to upper case
    key = key.upper()
    # Log the generated key to help with debugging
    logging.debug(f"Generated environment variable key: {key}")
    phone = os.getenv(key)
    if phone:
        logging.info(f"Phone number retrieved for {email}: {phone}")
    else:
        logging.warning(f"No phone number found for {email} using key {key}")
    return phone

# Example usage
email = 'realcryptoplato@gmail.com'
phone = get_phone_from_email(email)
