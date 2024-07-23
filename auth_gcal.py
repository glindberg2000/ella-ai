import os
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get paths from environment variables
CREDENTIALS_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'google_api_credentials.json')
GCAL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gcal_token.json')

# Scopes required for Google Calendar API
GCAL_SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]

# Initiate the OAuth flow to obtain new credentials for Google Calendar
def obtain_gcal_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"The credentials file does not exist at {CREDENTIALS_PATH}")

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GCAL_SCOPES)
    creds = flow.run_local_server(port=0)

    # Ensure the directory exists
    os.makedirs(os.path.dirname(GCAL_TOKEN_PATH), exist_ok=True)

    # Save the credentials to the specified path
    with open(GCAL_TOKEN_PATH, "w") as token_file:
        token_file.write(creds.to_json())
    
    print(f"New credentials saved to {GCAL_TOKEN_PATH}")

if __name__ == "__main__":
    # Run the function to reauthorize
    obtain_gcal_credentials()