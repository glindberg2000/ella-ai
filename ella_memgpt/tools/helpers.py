# logic_module.py

import os
import os.path
import traceback
from typing import Optional
import datetime
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
# SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = os.path.expanduser("~/.memgpt/gcal_token.json")
CREDENTIALS_PATH = os.path.expanduser("~/.memgpt/google_api_credentials.json")

# Add the ella_dbo path to sys.path
import sys
ella_dbo_path = os.path.expanduser("~/dev/ella-ai/ella_dbo")
sys.path.insert(0, ella_dbo_path)
# Configure logging at the start of your application
logging.basicConfig(
    level=logging.INFO,  # Adjust the logging level as needed
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Setup logger
logger = logging.getLogger(__name__)
# Attempt to import the db_manager functions
try:
    from db_manager import (
        create_connection,
        get_user_data_by_field,
        upsert_user,
        close_connection
    )
    print("Successfully imported from db_manager located in ~/dev/ella-ai/ella_dbo.")
except ImportError as e:
    print("Error: Unable to import db_manager. Check your path and module structure.")
    raise e
    

class GoogleUtils:
    def __init__(self, user_id: str):
        self.user_id = user_id
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())

        self.service = build("calendar", "v3", credentials=creds)
        self.user_email = self.get_user_email()
        self.calendar_id = self.get_or_create_user_calendar()

    def public_method(self):
        result = self._helper_method(self.user_id)
        return result

    def _helper_method(self, user_id):
        # Process and return
        modified_arg = user_id + 1
        return modified_arg
    
    def get_or_create_user_calendar(self) -> str:
        calendar_summary = f"User-{self.user_id}-Calendar"
        calendars = self.service.calendarList().list().execute()
        for calendar in calendars["items"]:
            if calendar["summary"] == calendar_summary:
                logger.info(f"Calendar {calendar_summary} already exists.")
                return calendar["id"]
        new_calendar = {"summary": calendar_summary, "timeZone": "America/Los_Angeles"}
        created_calendar = self.service.calendars().insert(body=new_calendar).execute()

        # Upsert the updated user data into the database
        conn=create_connection()
        upsert_user(
            conn,
            "memgpt_user_id",
            self.user_id,
            calendar_id=created_calendar["id"]
        )
        close_connection(conn)
        logger.info(f"Successfully created calendar {created_calendar['id']}")
        return created_calendar["id"]
    
    def set_calendar_permissions(self):
        acl_rule = {'scope': {'type': 'user', 'value': self.user_email}, 'role': 'writer'}
        self.service.acl().insert(calendarId=self.calendar_id, body=acl_rule).execute()
        logger.info(f"Successfully shared calendar {self.calendar_id} with user {self.user_email}")

    def get_user_email(self) -> Optional[str]:
        conn = create_connection()
        try:
            user_data = get_user_data_by_field(conn, 'memgpt_user_id', self.user_id)
            email = user_data.get('email', None)
            return email
        finally:
            close_connection(conn)

    def create_calendar_event(self, title, start, end, description):
        event = {
            "summary": title,
            "start": {"dateTime": start, "timeZone": "America/Los_Angeles"},
            "end": {"dateTime": end, "timeZone": "America/Los_Angeles"}
        }
        if description:
            event["description"] = description
        created_event = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
        return created_event.get('htmlLink')

# # function_file.py
# from logic_module import LogicHandler

# def exposed_function(self, arg):
#     handler = LogicHandler(arg)
#     return handler.public_method()
