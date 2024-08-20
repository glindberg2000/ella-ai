import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import logging
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)

# Constants
CREDENTIALS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ella_memgpt', 'credentials'))
GMAIL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gmail_token.json')
GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
CLIENT_SECRET_PATH = os.path.join(CREDENTIALS_PATH, 'client_secret.json')

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly"
]
GCAL_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events"
]

class GoogleServiceManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GoogleServiceManager, cls).__new__(cls)
                cls._instance._initialize_services()
            return cls._instance

    def _initialize_services(self):
        self.gmail_service = None
        self.calendar_service = None
        self.gmail_credentials = None
        self.calendar_credentials = None
        self.auth_email = None
        self._refresh_services()

    def _refresh_services(self):
        self.gmail_credentials = self._load_credentials(GMAIL_TOKEN_PATH, GMAIL_SCOPES)
        self.calendar_credentials = self._load_credentials(GCAL_TOKEN_PATH, GCAL_SCOPES)
        
        if self.gmail_credentials:
            self.gmail_service = build("gmail", "v1", credentials=self.gmail_credentials)
        if self.calendar_credentials:
            self.calendar_service = build("calendar", "v3", credentials=self.calendar_credentials)
        
        self.auth_email = self._get_auth_email()

    def _load_credentials(self, token_path, scopes):
        if not os.path.exists(token_path):
            logger.warning(f"Token file not found at {token_path}. Initiating new token flow.")
            return self._get_new_credentials(token_path, scopes)

        creds = Credentials.from_authorized_user_file(token_path, scopes)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"Refreshed credentials for {token_path}")
        return creds

    def _get_new_credentials(self, token_path, scopes):
        if not os.path.exists(CLIENT_SECRET_PATH):
            logger.error(f"Client secret file not found at {CLIENT_SECRET_PATH}")
            raise FileNotFoundError(f"Client secret file not found at {CLIENT_SECRET_PATH}")

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_PATH,
            scopes=scopes,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob')

        auth_url, _ = flow.authorization_url(prompt='consent')

        print(f'Please go to this URL and authorize the application: {auth_url}')
        code = input('Enter the authorization code: ')

        flow.fetch_token(code=code)
        creds = flow.credentials

        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        
        logger.info(f"New credentials obtained and saved to {token_path}")
        return creds

    def _get_auth_email(self):
        if self.gmail_service:
            try:
                profile = self.gmail_service.users().getProfile(userId='me').execute()
                return profile['emailAddress']
            except Exception as e:
                logger.error(f"Error retrieving authenticated email: {str(e)}", exc_info=True)
        return None

    def get_gmail_service(self):
        if not self.gmail_service or self.gmail_credentials.expired:
            self._refresh_services()
        return self.gmail_service

    def get_calendar_service(self):
        if not self.calendar_service or self.calendar_credentials.expired:
            self._refresh_services()
        return self.calendar_service

    def get_auth_email(self):
        if not self.auth_email:
            self._refresh_services()
        return self.auth_email



    
    def refresh_token(self, service):
        if service == 'gmail':
            creds = self.gmail_credentials
            token_path = GMAIL_TOKEN_PATH
            scopes = GMAIL_SCOPES
        elif service == 'calendar':
            creds = self.calendar_credentials
            token_path = GCAL_TOKEN_PATH
            scopes = GCAL_SCOPES
        else:
            logger.error(f"Unknown service: {service}")
            return f"Failed to refresh: Unknown service {service}"

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"Refreshed credentials for {service}")
                return f"Successfully refreshed {service} token"
            except Exception as e:
                logger.error(f"Error refreshing {service} token: {str(e)}", exc_info=True)
                return f"Failed to refresh {service} token: {str(e)}"
        else:
            logger.warning(f"No refresh needed or possible for {service}")
            return f"No refresh needed or possible for {service}"

    def get_token_expiry(self):
        gmail_expiry = self.gmail_credentials.expiry if self.gmail_credentials else None
        calendar_expiry = self.calendar_credentials.expiry if self.calendar_credentials else None
        
        now = datetime.utcnow()
        gmail_time_left = gmail_expiry - now if gmail_expiry else None
        calendar_time_left = calendar_expiry - now if calendar_expiry else None
        
        logger.info(f"Gmail token expires in: {gmail_time_left}")
        logger.info(f"Calendar token expires in: {calendar_time_left}")
        
        return {
            'gmail': gmail_expiry,
            'calendar': calendar_expiry
        }

    def refresh_all_tokens(self):
        logger.info("Refreshing all tokens")
        gmail_result = self.refresh_token('gmail')
        calendar_result = self.refresh_token('calendar')
        logger.info(f"Gmail refresh result: {gmail_result}")
        logger.info(f"Calendar refresh result: {calendar_result}")
        self._refresh_services()


# Create a singleton instance
google_service_manager = GoogleServiceManager()