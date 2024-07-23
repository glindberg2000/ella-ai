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
import base64

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
    # def __init__(self, user_id: str, token_path: str, credentials_path: str, scopes: list):
    #     self.user_id = user_id
    #     self.token_path = token_path
    #     self.credentials_path = credentials_path
    #     self.scopes = scopes
    #     self.service = None
    #     self.user_email = None
    #     self.calendar_id = None

    #     try:
    #         self.service = self._authenticate()
    #         if self.service is None:
    #             logger.error("Failed to authenticate Google service")
    #             return

    #         self.user_email = self.get_user_email()
    #         if self.user_email is None:
    #             logger.warning(f"Unable to retrieve email for user_id: {self.user_id}")
    #             return

    #         self.calendar_id = self.get_or_create_user_calendar()
    #         if self.calendar_id is None:
    #             logger.warning(f"Unable to get or create calendar for user_id: {self.user_id}")
    #     except Exception as e:
    #         logger.error(f"Error during GoogleUtils initialization: {str(e)}", exc_info=True)

    # def _authenticate(self):
    #     creds = None
    #     try:
    #         if os.path.exists(self.token_path):
    #             creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
    #         if not creds or not creds.valid:
    #             if creds and creds.expired and creds.refresh_token:
    #                 creds.refresh(Request())
    #             else:
    #                 flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.scopes)
    #                 creds = flow.run_local_server(port=0)
    #             with open(self.token_path, "w") as token:
    #                 token.write(creds.to_json())
    #         return build("calendar", "v3", credentials=creds)
    #     except Exception as e:
    #         logger.error(f"Error during authentication: {str(e)}", exc_info=True)
    #         return None
    def __init__(self, user_id: str, token_path: str, credentials_path: str, scopes: list):
        self.user_id = user_id
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.scopes = scopes
        self.service = None
        self.gmail_service = None
        self.user_email = None
        self.calendar_id = None
        self._authenticate()

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
            self.service = build("calendar", "v3", credentials=creds)
            self.gmail_service = build("gmail", "v1", credentials=creds)
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}", exc_info=True)

    def send_email(self, recipient_email: str, subject: str, body: str, message_id: Optional[str] = None) -> Dict[str, str]:
        """
        Send an email message via the Gmail API.

        Args:
            recipient_email (str): The email address of the recipient.
            subject (str): The subject of the email.
            body (str): The email message content to send.
            message_id (Optional[str]): The original message ID for referencing the original email thread.

        Returns:
            Dict[str, str]: A dictionary containing the status and message ID of the sent email.
        """
        if not self.gmail_service:
            logger.error("Gmail service is not authenticated")
            return {"status": "failed", "message": "Gmail service is not authenticated"}

        try:
            # Get the sender's email address
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            sender_email = profile['emailAddress']

            # If a message ID is provided, fetch the original subject and content
            if message_id:
                original_message = self.gmail_service.users().messages().get(userId='me', id=message_id, format='full').execute()
                original_subject = next((header['value'] for header in original_message['payload']['headers'] if header['name'].lower() == 'subject'), 'No Subject')
                subject = f"RE: {original_subject}"
                
                # Extract original body (simplified, might need more complex parsing for different email formats)
                original_body = base64.urlsafe_b64decode(original_message['payload']['body']['data']).decode('utf-8')
                body = f"{body}\n\n--- Original Message ---\n{original_body}"

            # Build the email message
            message = {
                "raw": base64.urlsafe_b64encode(
                    f"From: {sender_email}\nTo: {recipient_email}\nSubject: {subject}\n\n{body}".encode("utf-8")
                ).decode("utf-8")
            }

            # Send the message
            sent_message = self.gmail_service.users().messages().send(userId="me", body=message).execute()
            logger.info(f"Message sent to {recipient_email}: {sent_message['id']}")
            return {"status": "success", "message_id": sent_message['id']}

        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return {"status": "failed", "message": str(error)}

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
            return {
                'event_id': created_event['id'],
                'htmlLink': created_event.get('htmlLink')
            }
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
                    "event_id": event["id"],
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
        
    def update_calendar_event(self, event_id: str, title: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, description: Optional[str] = None) -> Optional[str]:
        """
        Update an existing event in the user's Google Calendar.

        Args:
            event_id (str): The unique event identifier.
            title (Optional[str]): New event name (if provided).
            start (Optional[str]): New start time in ISO 8601 format.
            end (Optional[str]): New end time in ISO 8601 format.
            description (Optional[str]): New expanded description of the event.

        Returns:
            Optional[str]: The HTML link to the updated event, or None if the update failed.
        """
        if not self.service or not self.calendar_id:
            logger.error("Missing required attributes for updating calendar event")
            return None
        try:
            event = self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()

            if title:
                event['summary'] = title
            if start:
                event['start']['dateTime'] = start
            if end:
                event['end']['dateTime'] = end
            if description:
                event['description'] = description

            updated_event = self.service.events().update(calendarId=self.calendar_id, eventId=event_id, body=event).execute()
            logger.info(f"Event updated successfully: {updated_event.get('htmlLink')}")
            return updated_event.get('htmlLink')
        except Exception as e:
            logger.error(f"Error updating calendar event: {str(e)}", exc_info=True)
            return None

    def delete_calendar_event(self, event_id: str) -> bool:
        """
        Delete an event from the user's Google Calendar.

        Args:
            event_id (str): The unique event identifier.

        Returns:
            bool: True if the event was successfully deleted, False otherwise.
        """
        if not self.service or not self.calendar_id:
            logger.error("Missing required attributes for deleting calendar event")
            return False
        try:
            self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
            logger.info(f"Event {event_id} successfully deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting calendar event: {str(e)}", exc_info=True)
            return False    
        
    