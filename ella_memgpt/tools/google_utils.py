# ella_memgpt/tools/google_utils.py

import os
import sys
from typing import Optional, List, Dict
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime

# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import from ella_dbo using an absolute import
from ella_dbo.db_manager import (
    create_connection,
    get_user_data_by_field,
    upsert_user,
    close_connection
)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class GoogleUtils:
    def __init__(self, user_id: str, token_path: str, credentials_path: str, scopes: list):
        self.user_id = user_id
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.scopes = scopes
        self.service = None
        self.user_email = None
        self.calendar_id = None

        try:
            self.service = self._authenticate()
            if self.service is None:
                logger.error("Failed to authenticate Google service")
                return

            self.user_email = self.get_user_email()
            if self.user_email is None:
                logger.warning(f"Unable to retrieve email for user_id: {self.user_id}")
                return

            self.calendar_id = self.get_or_create_user_calendar()
            if self.calendar_id is None:
                logger.warning(f"Unable to get or create calendar for user_id: {self.user_id}")
        except Exception as e:
            logger.error(f"Error during GoogleUtils initialization: {str(e)}", exc_info=True)

    def _authenticate(self):
        creds = None
        try:
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.scopes)
                    creds = flow.run_local_server(port=0)
                with open(self.token_path, "w") as token:
                    token.write(creds.to_json())
            return build("calendar", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}", exc_info=True)
            return None

    def get_or_create_user_calendar(self) -> Optional[str]:
        if not self.service:
            logger.error("Google service is not authenticated")
            return None
        try:
            calendar_summary = f"User-{self.user_id}-Calendar"
            calendars = self.service.calendarList().list().execute()
            if not calendars or "items" not in calendars:
                logger.error("Failed to retrieve calendar list")
                return None
            for calendar in calendars["items"]:
                if calendar.get("summary") == calendar_summary:
                    logger.info(f"Calendar {calendar_summary} already exists.")
                    return calendar.get("id")
            new_calendar = {"summary": calendar_summary, "timeZone": "America/Los_Angeles"}
            created_calendar = self.service.calendars().insert(body=new_calendar).execute()
            if not created_calendar or "id" not in created_calendar:
                logger.error("Failed to create new calendar")
                return None
            conn = create_connection()
            try:
                upsert_user(
                    conn,
                    "memgpt_user_id",
                    self.user_id,
                    calendar_id=created_calendar["id"]
                )
            finally:
                close_connection(conn)
            logger.info(f"Successfully created calendar {created_calendar['id']}")
            return created_calendar["id"]
        except Exception as e:
            logger.error(f"Error in get_or_create_user_calendar: {str(e)}", exc_info=True)
            return None

    def set_calendar_permissions(self):
        if not self.service or not self.user_email or not self.calendar_id:
            logger.error("Missing required attributes for setting calendar permissions")
            return
        try:
            acl_rule = {'scope': {'type': 'user', 'value': self.user_email}, 'role': 'writer'}
            self.service.acl().insert(calendarId=self.calendar_id, body=acl_rule).execute()
            logger.info(f"Successfully shared calendar {self.calendar_id} with user {self.user_email}")
        except Exception as e:
            logger.error(f"Error setting calendar permissions: {str(e)}", exc_info=True)

    def get_user_email(self) -> Optional[str]:
        conn = create_connection()
        try:
            user_data = get_user_data_by_field(conn, 'memgpt_user_id', self.user_id)
            logger.debug(f"User data retrieved: {user_data}")
            if user_data is None:
                logger.warning(f"No user data found for user_id: {self.user_id}")
                return None
            email = user_data.get('email')
            if email is None:
                logger.warning(f"No email found for user_id: {self.user_id}")
            return email
        except Exception as e:
            logger.error(f"Error retrieving user email: {str(e)}", exc_info=True)
            return None
        finally:
            close_connection(conn)

    def create_calendar_event(self, title, start, end, description):
        if not self.service or not self.calendar_id:
            logger.error("Missing required attributes for creating calendar event")
            return None
        try:
            event = {
                "summary": title,
                "start": {"dateTime": start, "timeZone": "America/Los_Angeles"},
                "end": {"dateTime": end, "timeZone": "America/Los_Angeles"}
            }
            if description:
                event["description"] = description
            created_event = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
            return created_event.get('htmlLink')
        except Exception as e:
            logger.error(f"Error creating calendar event: {str(e)}", exc_info=True)
            return None
        
    def fetch_upcoming_events(self, max_results: int = 100, time_min: Optional[str] = None) -> List[Dict]:
        """
        Fetch upcoming events from the user's Google Calendar.

        Args:
            max_results (int): Maximum number of events to retrieve. Default is 100.
            time_min (Optional[str]): Minimum time filter for events in ISO 8601 format.
                If not provided, defaults to the current time.

        Returns:
            List[Dict]: A list of dictionaries containing event details, or an empty list if an error occurs.
        """
        if not self.service or not self.calendar_id:
            logger.error("Missing required attributes for fetching events")
            return []

        try:
            if not time_min:
                time_min = datetime.datetime.now(datetime.timezone.utc).isoformat()

            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = events_result.get("items", [])
            formatted_events = [
                {
                    "id": event["id"],
                    "summary": event.get("summary", "No Title"),
                    "start": event["start"].get("dateTime", event["start"].get("date")),
                    "end": event["end"].get("dateTime", event["end"].get("date")),
                    "description": event.get("description", "No Description"),
                    "attendees": [attendee["email"] for attendee in event.get("attendees", [])],
                    "location": event.get("location", "No Location")
                }
                for event in events
            ]
            return formatted_events
        except Exception as e:
            logger.error(f"Error fetching upcoming events: {str(e)}", exc_info=True)
            return []