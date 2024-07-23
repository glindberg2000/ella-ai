import os
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get paths from environment variables
CREDENTIALS_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'google_api_credentials.json')
GMAIL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gmail_token.json')

# Scopes required for Gmail API
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send"
]

# Initiate the OAuth flow to obtain new credentials for Gmail
def obtain_gmail_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"The credentials file does not exist at {CREDENTIALS_PATH}")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)

    # Ensure the directory exists
    os.makedirs(os.path.dirname(GMAIL_TOKEN_PATH), exist_ok=True)

    # Save the credentials to the specified path
    with open(GMAIL_TOKEN_PATH, "w") as token_file:
        token_file.write(creds.to_json())
    
    print(f"New credentials saved to {GMAIL_TOKEN_PATH}")

if __name__ == "__main__":
    # Run the function to reauthorize
    obtain_gmail_credentials()