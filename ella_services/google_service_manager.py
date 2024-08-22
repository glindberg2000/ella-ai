import os
import json
import time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from threading import Lock
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Constants (same as before)
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
        self.gmail_credentials = None
        self.calendar_credentials = None
        self.gmail_service = None
        self.calendar_service = None
        self.auth_email = None
        self._refresh_gmail_service()
        self._refresh_calendar_service()

    def _refresh_gmail_service(self):
        try:
            self.gmail_credentials = self._load_and_refresh_credentials(GMAIL_TOKEN_PATH, GMAIL_SCOPES, 'Gmail')
            if self.gmail_credentials:
                self.gmail_service = build("gmail", "v1", credentials=self.gmail_credentials)
                self.auth_email = self._get_auth_email()
            else:
                logger.warning("Gmail credentials are not available.")
        except Exception as e:
            logger.error(f"Error refreshing Gmail service: {str(e)}")
            self.gmail_service = None

    def _refresh_calendar_service(self):
        try:
            self.calendar_credentials = self._load_and_refresh_credentials(GCAL_TOKEN_PATH, GCAL_SCOPES, 'Calendar')
            if self.calendar_credentials:
                self.calendar_service = build("calendar", "v3", credentials=self.calendar_credentials)
            else:
                logger.warning("Calendar credentials are not available.")
        except Exception as e:
            logger.error(f"Error refreshing Calendar service: {str(e)}")
            self.calendar_service = None


    def _refresh_services(self):
        self.gmail_credentials = self._load_and_refresh_credentials(GMAIL_TOKEN_PATH, GMAIL_SCOPES, 'Gmail')
        self.calendar_credentials = self._load_and_refresh_credentials(GCAL_TOKEN_PATH, GCAL_SCOPES, 'Calendar')
        
        if self.gmail_credentials:
            self.gmail_service = build("gmail", "v1", credentials=self.gmail_credentials)
        if self.calendar_credentials:
            self.calendar_service = build("calendar", "v3", credentials=self.calendar_credentials)
        
        self.auth_email = self._get_auth_email()

    def _load_and_refresh_credentials(self, token_path, scopes, service_name):
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info(f"Refreshing {service_name} token...")
                try:
                    creds.refresh(Request())
                    self._save_credentials(creds, token_path)
                    logger.info(f"{service_name} token refreshed. New expiry: {creds.expiry}")
                except Exception as e:
                    logger.error(f"Error refreshing {service_name} token: {str(e)}")
                    return None
            else:
                logger.info(f"Obtaining new {service_name} credentials...")
                try:
                    creds = self._get_new_credentials(token_path, scopes)
                    logger.info(f"New {service_name} credentials obtained. Expiry: {creds.expiry}")
                except Exception as e:
                    logger.error(f"Error obtaining new {service_name} credentials: {str(e)}")
                    return None
        else:
            logger.info(f"{service_name} token is still valid. Expiry: {creds.expiry}")
        
        return creds

    def _get_new_credentials(self, token_path, scopes):
        if not os.path.exists(CLIENT_SECRET_PATH):
            raise FileNotFoundError(f"Client secret file not found at {CLIENT_SECRET_PATH}")

        flow = Flow.from_client_secrets_file(CLIENT_SECRET_PATH, scopes=scopes)
        flow.run_local_server(port=0)
        
        creds = flow.credentials
        self._save_credentials(creds, token_path)
        return creds

    def _save_credentials(self, creds, token_path):
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        logger.info(f"Credentials saved to {token_path}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, HttpError))
    )
    def _get_auth_email(self):
        if self.gmail_service:
            try:
                profile = self.gmail_service.users().getProfile(userId='me').execute()
                return profile['emailAddress']
            except HttpError as e:
                if e.resp.status in [403, 429]:  # Rate limiting errors
                    logger.warning(f"Rate limit hit when retrieving auth email. Retrying...")
                    time.sleep(5)  # Wait for 5 seconds before retry
                    raise
                else:
                    logger.error(f"HTTP error retrieving authenticated email: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Error retrieving authenticated email: {str(e)}", exc_info=True)
                raise
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, HttpError))
    )
    def get_gmail_service(self):
        if not self.gmail_service or not self.gmail_credentials.valid:
            self._refresh_services()
        return self.gmail_service

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, HttpError))
    )
    def get_calendar_service(self):
        if not self.calendar_service or not self.calendar_credentials.valid:
            self._refresh_services()
        return self.calendar_service

    def get_auth_email(self):
        if not self.auth_email:
            self._refresh_services()
        return self.auth_email

    def refresh_all_tokens(self):
        logger.info("Refreshing all tokens")
        self._refresh_services()

    def get_token_expiry(self):
        gmail_expiry = self.gmail_credentials.expiry if self.gmail_credentials else None
        calendar_expiry = self.calendar_credentials.expiry if self.calendar_credentials else None
        return {
            'gmail': gmail_expiry,
            'calendar': calendar_expiry
        }

# Create a singleton instance
google_service_manager = GoogleServiceManager()