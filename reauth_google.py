import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Path to client secrets file (usually named credentials.json)
CREDENTIALS_PATH = os.path.expanduser("~/.memgpt/google_api_credentials.json")

# Path where the new token.json file will be saved
GMAIL_TOKEN_PATH = os.path.expanduser("~/.memgpt/gmail_token.json")

# Scopes required for Gmail API
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

# Initiate the OAuth flow to obtain new credentials
def obtain_gmail_credentials():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the credentials to the specified path
    with open(GMAIL_TOKEN_PATH, "w") as token_file:
        token_file.write(creds.to_json())
    print(f"New credentials saved to {GMAIL_TOKEN_PATH}")

# Run the function to reauthorize
obtain_gmail_credentials()
