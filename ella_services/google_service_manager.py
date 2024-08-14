# File: google_service_manager.py

import os
import os.path
from typing import Optional
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
from google.auth.transport.requests import Request
import logging


# Load environment variables
load_dotenv()

# Constants
CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH', '')
GMAIL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gmail_token.json')
#GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'ella-ai-420020-9cc117656551.json')
GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.readonly"]
GCAL_SCOPES = [
    "https://www.googleapis.com/auth/calendar",  # This scope allows read/write access
    "https://www.googleapis.com/auth/calendar.events"  # This scope allows creating and updating events
]

logger = logging.getLogger(__name__)

class GoogleServiceManager:
    """
    A manager class for initializing and providing Google services (Gmail and Calendar).
    
    This class handles the authentication and creation of Gmail and Google Calendar
    services, which can be used by different parts of the application.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GoogleServiceManager, cls).__new__(cls)
            cls._instance._initialize_services()
            if not cls._instance.are_services_initialized():
                logger.error("Failed to initialize Google services.")
                return None
        return cls._instance

    def _initialize_services(self):
        """
        Initialize Gmail and Google Calendar services.
        """
        self.gmail_service = self._create_gmail_service()
        self.calendar_service = self._create_calendar_service()
        self.auth_email = self._get_auth_email()

    def are_services_initialized(self):
        """
        Check if both Gmail and Calendar services are initialized.

        Returns:
            bool: True if both services are initialized, False otherwise.
        """
        return self.gmail_service is not None and self.calendar_service is not None
    
    def reinitialize_services(self):
        """
        Reinitialize Gmail and Calendar services.

        This method can be called if services fail or need to be refreshed.
        """
        logger.info("Reinitializing Google services...")
        self._initialize_services()
        if self.are_services_initialized():
            logger.info("Services reinitialized successfully.")
        else:
            logger.error("Failed to reinitialize services.")


    def refresh_credentials(self):
        """
        Refresh the credentials for both Gmail and Calendar services.
        """
        try:
            #cal_creds = ServiceAccountCredentials.from_service_account_file(GCAL_TOKEN_PATH, scopes=GCAL_SCOPES)
            cal_creds = UserCredentials.from_authorized_user_file(GCAL_TOKEN_PATH, GCAL_SCOPES)
            if cal_creds and cal_creds.expired and cal_creds.refresh_token:
                cal_creds.refresh(Request())
                with open(GCAL_TOKEN_PATH, 'w') as token:
                    token.write(cal_creds.to_json())
                logger.info("Calendar credentials refreshed successfully.")
            
            self.calendar_service = self._create_calendar_service()
            if self.calendar_service:
                logger.info("Calendar service reinitialized successfully.")
            else:
                logger.error("Failed to reinitialize Calendar service.")
        except Exception as e:
            logger.error(f"Error refreshing credentials: {str(e)}", exc_info=True)

    def _create_gmail_service(self):
        try:
            if not os.path.exists(GMAIL_TOKEN_PATH):
                logger.error(f"Gmail token file not found at {GMAIL_TOKEN_PATH}")
                return None
            creds = UserCredentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)
            return build("gmail", "v1", credentials=creds)
        except Exception as e:
            logger.error(f"Error creating Gmail service: {str(e)}", exc_info=True)
            return None

    def _create_calendar_service(self):
        try:
            if not os.path.exists(GCAL_TOKEN_PATH):
                logger.error(f"Calendar token file not found at {GCAL_TOKEN_PATH}")
                return None
            creds = UserCredentials.from_authorized_user_file(GCAL_TOKEN_PATH, GCAL_SCOPES)
            # creds = ServiceAccountCredentials.from_service_account_file(GCAL_TOKEN_PATH, scopes=GCAL_SCOPES)
            if "https://www.googleapis.com/auth/calendar" not in creds.scopes:
                logger.warning("Calendar service initialized with read-only scope. Calendar updates will not be possible.")
            return build("calendar", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"Error creating Calendar service: {str(e)}", exc_info=True)
            return None

    def _get_auth_email(self) -> Optional[str]:
        """
        Retrieve the authenticated email address.

        Returns:
            Optional[str]: The authenticated email address or None if retrieval fails.
        """
        try:
            if self.gmail_service:
                profile = self.gmail_service.users().getProfile(userId='me').execute()
                return profile['emailAddress']
            else:
                logger.error("Gmail service not initialized")
                return None
        except Exception as e:
            logger.error(f"Error retrieving authenticated email: {str(e)}", exc_info=True)
            return None

    def get_gmail_service(self):
        """
        Get the Gmail service object.

        Returns:
            The Gmail service object.
        """
        return self.gmail_service

    def get_calendar_service(self):
        """
        Get the Google Calendar service object.

        Returns:
            The Google Calendar service object.
        """
        return self.calendar_service

    def get_auth_email(self) -> Optional[str]:
        """
        Get the authenticated email address.

        Returns:
            Optional[str]: The authenticated email address.
        """
        return self.auth_email

# Create a singleton instance
google_service_manager = GoogleServiceManager()