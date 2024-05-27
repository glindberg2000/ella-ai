import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Path to the client_secrets.json file
CREDENTIALS_PATH = os.path.expanduser("~/.memgpt/google_api_credentials.json")

# Path where the new token.json file will be saved
GCAL_TOKEN_PATH = os.path.expanduser("~/.memgpt/gcal_token.json")

# Scopes required for Google Calendar API
GCAL_SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]

# Initiate the OAuth flow to obtain new credentials for Google Calendar
def obtain_gcal_credentials():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GCAL_SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the credentials to the specified path
    with open(GCAL_TOKEN_PATH, "w") as token_file:
        token_file.write(creds.to_json())
    print(f"New credentials saved to {GCAL_TOKEN_PATH}")

# Run the function to reauthorize
obtain_gcal_credentials()

