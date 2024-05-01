import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

import base64
from email.mime.text import MIMEText



def get_credentials(SCOPES):
    """Load or create new credentials"""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    return creds

def list_labels(service):
    """List all labels in the user's mailbox."""
    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        if not labels:
            print("No labels found.")
        else:
            print("Labels:")
            for label in labels:
                print(label["name"])
    except HttpError as error:
        print(f"Error occurred while listing labels: {error}")

def list_messages(service):
    """List recent messages in the user's mailbox."""
    try:
        results = service.users().messages().list(userId="me", maxResults=10).execute()
        messages = results.get("messages", [])
        if not messages:
            print("No messages found.")
        else:
            print("\nRecent Message IDs:")
            for message in messages:
                print(message["id"])
    except HttpError as error:
        print(f"Error occurred while listing messages: {error}")

def get_messages_from_sender(service, sender_email):
    """Retrieve all messages from a specific sender."""
    try:
        search_query = f'from:{sender_email}'
        results = service.users().messages().list(userId="me", q=search_query).execute()
        messages = results.get("messages", [])
        if not messages:
            print(f"No messages found from {sender_email}.")
        else:
            print(f"\nMessages from {sender_email}:")
            for message in messages:
                print(message["id"])
    except HttpError as error:
        print(f"Error occurred while fetching messages from {sender_email}: {error}")

def send_message(service, to_email, subject, message_text):
    """Send an email message."""
    try:
        message = MIMEText(message_text)
        message['to'] = to_email
        message['from'] = "me"
        message['subject'] = subject
        encoded_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
        
        sent_message = service.users().messages().send(userId="me", body=encoded_message).execute()
        print(f"Message sent successfully: {sent_message['id']}")
    except HttpError as error:
        print(f"Failed to send message: {error}")

def main():
    """Shows basic usage of the Gmail API."""
    #SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

    creds = get_credentials(SCOPES)
    service = build("gmail", "v1", credentials=creds)

    list_labels(service)
    list_messages(service)
    get_messages_from_sender(service, "greglindberg@gmail.com")
    send_message(service, "greglindberg@gmail.com", "Hello", "This is a test email from the Gmail API.")


if __name__ == '__main__':
    main()
