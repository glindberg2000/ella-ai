import os
import sys
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, Dict, List, Union
import datetime

# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

class UserDataManager:
    @staticmethod
    def get_user_email(memgpt_user_id: str) -> Optional[str]:
        from ella_dbo.db_manager import create_connection, get_user_data_by_field, close_connection
        conn = create_connection()
        try:
            user_data = get_user_data_by_field(conn, 'memgpt_user_id', memgpt_user_id)
            logger.debug(f"User data retrieved: {user_data}")
            if user_data is None:
                logger.warning(f"No user data found for user_id: {memgpt_user_id}")
                return None
            email = user_data.get('email')
            if email is None:
                logger.warning(f"No email found for user_id: {memgpt_user_id}")
            return email
        except Exception as e:
            logger.error(f"Error retrieving user email: {str(e)}", exc_info=True)
            return None
        finally:
            close_connection(conn)

class GoogleAuthBase:
    def __init__(self, token_path: str, credentials_path: str, scopes: list):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.scopes = scopes
        self.creds = None
        self.auth_email = None
        self._authenticate()

    def _authenticate(self):
        try:
            if os.path.exists(self.token_path):
                self.creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.scopes)
                    self.creds = flow.run_local_server(port=0)
                with open(self.token_path, "w") as token:
                    token.write(self.creds.to_json())
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}", exc_info=True)

    def _get_auth_email(self) -> Optional[str]:
        # This method should be implemented by derived classes if needed
        return None

class GoogleCalendarUtils(GoogleAuthBase):
    def __init__(self, token_path: str, credentials_path: str):
        super().__init__(token_path, credentials_path, ["https://www.googleapis.com/auth/calendar"])
        self.service = build("calendar", "v3", credentials=self.creds)

    def get_or_create_user_calendar(self, user_id: str) -> Optional[str]:
        try:
            user_email = UserDataManager.get_user_email(user_id)
            if not user_email:
                logger.error(f"Unable to retrieve email for user_id: {user_id}")
                return None

            calendar_summary = f"User-{user_id}-Calendar"
            calendars = self.service.calendarList().list().execute()
            for calendar in calendars.get("items", []):
                if calendar["summary"] == calendar_summary:
                    logger.info(f"Calendar {calendar_summary} already exists.")
                    return calendar["id"]

            # Create new calendar
            new_calendar = {"summary": calendar_summary, "timeZone": "America/Los_Angeles"}
            created_calendar = self.service.calendars().insert(body=new_calendar).execute()
            logger.info(f"Created new calendar: {created_calendar['id']}")
            
            # Set permissions
            self.set_calendar_permissions(created_calendar['id'], user_email)
            
            return created_calendar['id']
        except Exception as e:
            logger.error(f"Error in get_or_create_user_calendar: {str(e)}", exc_info=True)
            return None

    def create_calendar_event(self, calendar_id: str, event_data: dict) -> dict:
        try:
            event = self.service.events().insert(calendarId=calendar_id, body=event_data).execute()
            return {"success": True, "id": event['id'], "htmlLink": event.get('htmlLink')}
        except HttpError as e:
            logger.error(f"Error creating calendar event: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error creating event: {str(e)}"}

    # def fetch_upcoming_events(self, user_id: str, max_results: int = 10, time_min: Optional[str] = None) -> List[Dict]:
    #     try:
    #         calendar_id = self.get_or_create_user_calendar(user_id)
    #         if not calendar_id:
    #             logger.error(f"Unable to get calendar for user_id: {user_id}")
    #             return []

    #         if not time_min:
    #             time_min = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

    #         events_result = self.service.events().list(
    #             calendarId=calendar_id,
    #             timeMin=time_min,
    #             maxResults=max_results,
    #             singleEvents=True,
    #             orderBy='startTime'
    #         ).execute()

    #         events = events_result.get('items', [])
    #         return events
    #     except Exception as e:
    #         logger.error(f"Error fetching events: {str(e)}", exc_info=True)
    #         return []

    def fetch_upcoming_events(
        self, 
        user_id: str, 
        max_results: int = 10, 
        time_min: Optional[str] = None,
        page_token: Optional[str] = None
    ) -> dict:
        try:
            calendar_id = self.get_or_create_user_calendar(user_id)
            if not calendar_id:
                logger.error(f"Unable to get calendar for user_id: {user_id}")
                return {"items": [], "nextPageToken": None, "prevPageToken": None}

            if not time_min:
                time_min = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()

            events = events_result.get('items', [])
            next_page_token = events_result.get('nextPageToken')
            prev_page_token = events_result.get('prevPageToken')
            
            return {"items": events, "nextPageToken": next_page_token, "prevPageToken": prev_page_token}
        except Exception as e:
            logger.error(f"Error fetching events: {str(e)}", exc_info=True)
            return {"items": [], "nextPageToken": None, "prevPageToken": None}


    def delete_calendar_event(self, user_id: str, event_id: str, delete_series: bool = False) -> dict:
        try:
            calendar_id = self.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return {"success": False, "message": "Unable to get or create user calendar"}

            try:
                if delete_series:
                    event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
                    if 'recurringEventId' in event:
                        series_id = event['recurringEventId']
                        self.service.events().delete(calendarId=calendar_id, eventId=series_id).execute()
                        return {"success": True, "message": f"Event series deleted successfully. ID: {series_id}"}
                self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
                return {"success": True, "message": "Event deleted successfully"}
            except HttpError as error:
                if error.resp.status == 404:
                    return {"success": False, "message": f"Event not found: {event_id}"}
                else:
                    return {"success": False, "message": f"Error deleting event: {str(error)}"}
        except Exception as e:
            logger.error(f"Error in delete_calendar_event: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error deleting event: {str(e)}"}

    def set_calendar_permissions(self, calendar_id: str, user_email: str):
        try:
            rule = {
                'scope': {
                    'type': 'user',
                    'value': user_email
                },
                'role': 'writer'
            }
            self.service.acl().insert(calendarId=calendar_id, body=rule).execute()
            logger.info(f"Set calendar permissions for {user_email} on calendar {calendar_id}")
        except Exception as e:
            logger.error(f"Error setting calendar permissions: {str(e)}", exc_info=True)

    def update_calendar_event(self, user_id: str, event_id: str, event_data: dict, update_series: bool = False) -> dict:
        try:
            calendar_id = self.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return {"success": False, "message": "Unable to get or create user calendar"}

            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()

            if update_series and 'recurringEventId' in event:
                series_id = event['recurringEventId']
                updated_event = self.service.events().patch(calendarId=calendar_id, eventId=series_id, body=event_data).execute()
                return {"success": True, "message": f"Event series updated successfully. ID: {series_id}", "event": updated_event}
            else:
                updated_event = self.service.events().patch(calendarId=calendar_id, eventId=event_id, body=event_data).execute()
                return {"success": True, "message": "Event updated successfully", "event": updated_event}
        except HttpError as e:
            logger.error(f"Error in update_calendar_event: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error updating event: {str(e)}"}


class GoogleEmailUtils(GoogleAuthBase):
    def __init__(self, token_path: str, credentials_path: str):
        super().__init__(token_path, credentials_path, [
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly"
        ])
        self.service = build("gmail", "v1", credentials=self.creds)
        self.auth_email = self._get_auth_email()

    def _get_auth_email(self) -> Optional[str]:
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile['emailAddress']
        except Exception as e:
            logger.error(f"Error retrieving authenticated email: {str(e)}", exc_info=True)
            return None

    def send_email(self, recipient_email: str, subject: str, body: str, message_id: Optional[str] = None) -> Dict[str, str]:
        try:
            message = self._create_message(recipient_email, subject, body, message_id)
            sent_message = self.service.users().messages().send(userId="me", body=message).execute()
            logger.info(f"Message sent to {recipient_email}: {sent_message['id']}")
            return {"status": "success", "message_id": sent_message['id']}
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}", exc_info=True)
            return {"status": "failed", "message": str(e)}

    def _create_message(self, to, subject, body, message_id=None):
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message['to'] = to
        message['from'] = self.auth_email
        message['subject'] = subject
        if message_id:
            message['In-Reply-To'] = message_id
            message['References'] = message_id

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}