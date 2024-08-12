#google_utils.py
import os
import sys
import logging
import aiosqlite  # Add this import
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Any, Optional, Dict, List, Tuple, Union
import pytz
from datetime import datetime, timedelta, timezone
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class UserDataManager:
    @staticmethod
    def get_user_data(memgpt_user_id: str) -> dict:
        """
        Retrieve all data for a given user.
        
        Args:
            memgpt_user_id (str): The MemGPT user ID.
        
        Returns:
            dict: A dictionary containing all user data.
        """
        from ella_dbo.db_manager import get_user_data_by_field, create_connection, close_connection
        conn = create_connection()
        try:
            logging.info(f"Attempting to retrieve data for user_id: {memgpt_user_id}")
            user_data = get_user_data_by_field(conn, 'memgpt_user_id', memgpt_user_id)
            return user_data if user_data else {}
        except Exception as e:
            logging.error(f"Error retrieving user data: {str(e)}", exc_info=True)
            return {}
        finally:
            close_connection(conn)

    @staticmethod
    def get_user_timezone(memgpt_user_id: str) -> str:
        """
        Retrieve the timezone for a given user.
        
        Args:
            memgpt_user_id (str): The MemGPT user ID.
        
        Returns:
            str: The user's timezone if found, 'America/Los_Angeles' as default otherwise.
        """
        from ella_dbo.db_manager import get_user_data_by_field, create_connection, close_connection
        conn = create_connection()
        try:
            logging.info(f"Attempting to retrieve timezone for user_id: {memgpt_user_id}")
            user_data = get_user_data_by_field(conn, 'memgpt_user_id', memgpt_user_id)
            if user_data and 'local_timezone' in user_data:
                return user_data['local_timezone']
            logging.warning(f"No timezone found for user {memgpt_user_id}. Using default: America/Los_Angeles")
            return 'America/Los_Angeles'
        except Exception as e:
            logging.error(f"Error retrieving user timezone: {str(e)}", exc_info=True)
            return 'America/Los_Angeles'
        finally:
            close_connection(conn)

    @staticmethod
    def get_user_email(memgpt_user_id: str) -> Optional[str]:
        """
        Retrieve the email for a given user.
        
        Args:
            memgpt_user_id (str): The MemGPT user ID.
        
        Returns:
            Optional[str]: The user's email if found, None otherwise.
        """
        from ella_dbo.db_manager import get_user_data_by_field, create_connection, close_connection
        conn = create_connection()
        try:
            logging.info(f"Attempting to retrieve email for user_id: {memgpt_user_id}")
            user_data = get_user_data_by_field(conn, 'memgpt_user_id', memgpt_user_id)
            if user_data and 'email' in user_data:
                return user_data['email']
            logging.warning(f"No email found for user {memgpt_user_id} in user_data: {user_data}")
            default_email = "default@example.com"
            logging.warning(f"Using default email {default_email} for user_id: {memgpt_user_id}")
            return default_email
        except Exception as e:
            logging.error(f"Error retrieving user email: {str(e)}", exc_info=True)
            return None
        finally:
            close_connection(conn)

    @staticmethod
    def get_user_reminder_prefs(memgpt_user_id: str) -> Dict[str, Union[int, str]]:
        """
        Retrieve the default reminder preferences for a given user.
        
        Args:
            memgpt_user_id (str): The MemGPT user ID.
        
        Returns:
            Dict[str, Union[int, str]]: A dictionary containing 'default_reminder_time' and 'reminder_method'.
        """
        from ella_dbo.db_manager import get_user_data_by_field, create_connection, close_connection
        conn = create_connection()
        try:
            user_data = get_user_data_by_field(conn, 'memgpt_user_id', memgpt_user_id)
            if user_data:
                return {
                    'default_reminder_time': user_data.get('default_reminder_time', 15),
                    'reminder_method': user_data.get('reminder_method', 'email,sms')
                }
            return {'default_reminder_time': 15, 'reminder_method': 'email,sms'}
        except Exception as e:
            logging.error(f"Error retrieving user reminder preferences: {str(e)}", exc_info=True)
            return {'default_reminder_time': 15, 'reminder_method': 'email,sms'}
        finally:
            close_connection(conn)


    @staticmethod
    def get_user_phone(memgpt_user_id: str) -> Optional[str]:
        from ella_dbo.db_manager import get_user_data_by_field, create_connection, close_connection
        
        conn = create_connection()
        try:
            logging.info(f"Attempting to retrieve phone number for user_id: {memgpt_user_id}")
            user_data = get_user_data_by_field(conn, 'memgpt_user_id', memgpt_user_id)
            if user_data and 'phone' in user_data:
                return user_data['phone']
            logging.warning(f"No phone number found for user {memgpt_user_id}")
            return None
        except Exception as e:
            logging.error(f"Error retrieving user phone number: {str(e)}", exc_info=True)
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

    def prepare_event_data(
        self,
        user_id: str,
        title: str,
        start: str,
        end: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        reminders: Optional[str] = None,
        recurrence: Optional[str] = None,
        local_timezone: str = 'America/Los_Angeles'
    ) -> Dict[str, Any]:
        """
        Prepare event data with proper handling of reminders and time zones.

        Args:
            user_id (str): The unique identifier for the user.
            title (str): The title of the event.
            start (str): The start time in ISO 8601 format.
            end (str): The end time in ISO 8601 format.
            description (Optional[str]): The description of the event.
            location (Optional[str]): The location of the event.
            reminders (Optional[str]): JSON string representation of reminders.
            recurrence (Optional[str]): Recurrence rule in RRULE format.
            local_timezone (str): The timezone for the event.

        Returns:
            Dict[str, Any]: Prepared event data ready to be used for creating or updating an event.
        """
        start_time = parse_datetime(start, local_timezone)
        end_time = parse_datetime(end, local_timezone)
        current_time = datetime.now(pytz.timezone(local_timezone))

        event_data = {
            'summary': title,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': local_timezone},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': local_timezone},
            'description': description,
            'location': location,
        }

        if recurrence:
            event_data['recurrence'] = [recurrence]

        # Handle reminders
        if reminders:
            reminders_list = json.loads(reminders)
            standard_reminders = []
            custom_reminders = []
            for reminder in reminders_list:
                if reminder['type'] in ['email', 'popup', 'sms']:
                    standard_reminders.append({'method': reminder['type'], 'minutes': reminder['minutes']})
                else:
                    custom_reminders.append(reminder)
            
            event_data['reminders'] = {
                'useDefault': False,
                'overrides': standard_reminders
            }
            
            if custom_reminders:
                event_data['extendedProperties'] = {
                    'private': {
                        'customReminders': json.dumps(custom_reminders)
                    }
                }
        else:
            # Use default reminders if none specified
            event_data['reminders'] = {'useDefault': True}

        # Ensure at least one valid reminder
        time_until_event = start_time - current_time
        if time_until_event > timedelta(0):
            if not event_data['reminders'].get('overrides') and event_data['reminders'].get('useDefault', True):
                user_prefs = UserDataManager.get_user_reminder_prefs(user_id)
                default_reminder_time = user_prefs['default_reminder_time']
                default_method = user_prefs['reminder_method'].split(',')[0]
                
                if time_until_event < timedelta(minutes=default_reminder_time):
                    # If the event is too soon for the default reminder, set an immediate reminder
                    immediate_reminder_minutes = max(0, time_until_event.total_seconds() // 60)
                    event_data['reminders'] = {
                        'useDefault': False,
                        'overrides': [{'method': default_method, 'minutes': int(immediate_reminder_minutes)}]
                    }

        return event_data
    
    def check_conflicts(
        self,
        user_id: str,
        start: str,
        end: str,
        event_id: Optional[str] = None,
        local_timezone: str = 'America/Los_Angeles'
    ) -> Dict[str, Any]:
        """
        Check for conflicting events in the user's calendar.

        Args:
            user_id (str): The unique identifier for the user.
            start (str): The start time of the event in ISO 8601 format.
            end (str): The end time of the event in ISO 8601 format.
            event_id (Optional[str]): The ID of the event being updated (if applicable).
            local_timezone (str): The timezone for the event.

        Returns:
            Dict[str, Any]: A dictionary containing information about conflicts and suggested alternative times.
        """
        calendar_id = self.get_or_create_user_calendar(user_id)
        if not calendar_id:
            return {"success": False, "message": "Unable to get or create user calendar"}

        start_time = parse_datetime(start, local_timezone)
        end_time = parse_datetime(end, local_timezone)

        # Fetch existing events
        events = self.fetch_upcoming_events(
            user_id=user_id,
            max_results=50,
            time_min=start_time.isoformat(),
            time_max=end_time.isoformat(),
            local_timezone=local_timezone
        )

        conflicting_events = []
        for event in events.get('items', []):
            if event.get('id') == event_id:
                continue  # Skip the event being updated (if applicable)
            event_start = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), local_timezone)
            event_end = parse_datetime(event['end'].get('dateTime', event['end'].get('date')), local_timezone)
            if (event_start < end_time and event_end > start_time):
                conflicting_events.append({
                    "id": event['id'],
                    "summary": event['summary'],
                    "start": event['start'].get('dateTime', event['start'].get('date')),
                    "end": event['end'].get('dateTime', event['end'].get('date'))
                })

        if conflicting_events:
            # Generate alternative times
            alternative_times = self.suggest_alternative_times(start_time, end_time, conflicting_events, local_timezone)
            return {
                "success": False,
                "message": "Conflicting events found.",
                "conflicts": conflicting_events,
                "suggested_times": alternative_times
            }
        else:
            return {"success": True, "message": "No conflicts found."}

    def suggest_alternative_times(
        self,
        start_time: datetime,
        end_time: datetime,
        conflicting_events: List[Dict[str, Any]],
        local_timezone: str
    ) -> List[Tuple[str, str]]:
        """
        Suggest alternative times for an event based on conflicts.

        Args:
            start_time (datetime): The original start time of the event.
            end_time (datetime): The original end time of the event.
            conflicting_events (List[Dict[str, Any]]): List of conflicting events.
            local_timezone (str): The timezone for the event.

        Returns:
            List[Tuple[str, str]]: A list of tuples containing suggested start and end times.
        """
        event_duration = end_time - start_time
        buffer = timedelta(minutes=15)  # Add a 15-minute buffer between events
        alternative_times = []

        # Suggest a time before the first conflict
        first_conflict = min(conflicting_events, key=lambda e: parse_datetime(e['start'], local_timezone))
        first_conflict_start = parse_datetime(first_conflict['start'], local_timezone)
        if start_time < first_conflict_start:
            suggested_end = first_conflict_start - buffer
            suggested_start = suggested_end - event_duration
            if suggested_start > start_time - timedelta(days=1):  # Don't suggest times more than a day earlier
                alternative_times.append((suggested_start.isoformat(), suggested_end.isoformat()))

        # Suggest times between conflicts
        sorted_conflicts = sorted(conflicting_events, key=lambda e: parse_datetime(e['start'], local_timezone))
        for i in range(len(sorted_conflicts) - 1):
            current_end = parse_datetime(sorted_conflicts[i]['end'], local_timezone)
            next_start = parse_datetime(sorted_conflicts[i+1]['start'], local_timezone)
            if current_end + buffer + event_duration + buffer <= next_start:
                suggested_start = current_end + buffer
                suggested_end = suggested_start + event_duration
                alternative_times.append((suggested_start.isoformat(), suggested_end.isoformat()))

        # Suggest a time after the last conflict
        last_conflict = max(conflicting_events, key=lambda e: parse_datetime(e['end'], local_timezone))
        last_conflict_end = parse_datetime(last_conflict['end'], local_timezone)
        suggested_start = last_conflict_end + buffer
        suggested_end = suggested_start + event_duration
        if suggested_end < end_time + timedelta(days=1):  # Don't suggest times more than a day later
            alternative_times.append((suggested_start.isoformat(), suggested_end.isoformat()))

        return alternative_times

    def create_calendar_event(self, user_id: str, event_data: dict, local_timezone: str) -> dict:
        try:
            calendar_id = self.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return {"success": False, "message": "Unable to get or create user calendar"}

            # Convert event times to user's timezone
            start_time = self._localize_time(event_data['start']['dateTime'], local_timezone)
            end_time = self._localize_time(event_data['end']['dateTime'], local_timezone)

            event_data['start'] = {'dateTime': start_time.isoformat(), 'timeZone': local_timezone}
            event_data['end'] = {'dateTime': end_time.isoformat(), 'timeZone': local_timezone}

            # Handle reminders
            if 'reminders' not in event_data:
                event_data['reminders'] = {'useDefault': True}

            # Handle custom reminders in extendedProperties
            if 'extendedProperties' in event_data and 'private' in event_data['extendedProperties']:
                custom_reminders = event_data['extendedProperties']['private'].get('customReminders')
                if custom_reminders:
                    # Ensure the customReminders are properly formatted as a JSON string
                    if isinstance(custom_reminders, str):
                        try:
                            json.loads(custom_reminders)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in customReminders: {custom_reminders}")
                            del event_data['extendedProperties']['private']['customReminders']
                    elif isinstance(custom_reminders, list):
                        event_data['extendedProperties']['private']['customReminders'] = json.dumps(custom_reminders)
                    else:
                        logger.warning(f"Unexpected type for customReminders: {type(custom_reminders)}")
                        del event_data['extendedProperties']['private']['customReminders']

            # Log the event data being sent
            logging.info(f"Sending event data: {json.dumps(event_data, indent=2)}")

            event = self.service.events().insert(calendarId=calendar_id, body=event_data).execute()
            return {"success": True, "id": event['id'], "htmlLink": event.get('htmlLink')}
        except HttpError as e:
            logging.error(f"Error creating calendar event: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error creating event: {str(e)}"}
         

    def fetch_upcoming_events(
        self, 
        user_id: str, 
        max_results: int = 10, 
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        local_timezone: str = 'America/Los_Angeles'
    ) -> dict:
        try:
            calendar_id = self.get_or_create_user_calendar(user_id)
            logging.debug(f"Calendar ID for user {user_id}: {calendar_id}")
            
            if not calendar_id:
                logging.error(f"Unable to get calendar for user_id: {user_id}")
                return {"items": []}

            if not time_min:
                time_min = datetime.now(pytz.timezone(local_timezone)).isoformat()
            if not time_max:
                time_max = (datetime.now(pytz.timezone(local_timezone)) + timedelta(days=1)).isoformat()

            params = {
                'calendarId': calendar_id,
                'timeMin': time_min,
                'timeMax': time_max,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime',
                'timeZone': local_timezone
            }

            logging.debug(f"Calendar API request params: {params}")

            events_result = self.service.events().list(**params).execute()

            logging.debug(f"Raw Calendar API response: {events_result}")

            events = events_result.get('items', [])
            
            logging.debug(f"Number of events fetched: {len(events)}")

            # Convert event times to user's timezone and ensure all necessary fields are present
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                event['start']['dateTime'] = self._localize_time(start, local_timezone).isoformat()
                event['end']['dateTime'] = self._localize_time(end, local_timezone).isoformat()

                # Ensure reminders field is present
                if 'reminders' not in event:
                    event['reminders'] = {'useDefault': True}

                # Ensure extendedProperties field is present
                if 'extendedProperties' not in event:
                    event['extendedProperties'] = {'private': {}}

            return {"items": events}
        except Exception as e:
            logging.error(f"Error fetching events: {str(e)}", exc_info=True)
            return {"items": []}
            

    def update_calendar_event(self, user_id: str, event_id: str, event_data: dict, update_series: bool = False, local_timezone: str = 'America/Los_Angeles') -> dict:
        try:
            calendar_id = self.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return {"success": False, "message": "Unable to get or create user calendar"}

            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()

            # Update event times if provided
            if 'start' in event_data:
                start_time = self._localize_time(event_data['start']['dateTime'], local_timezone)
                event_data['start'] = {'dateTime': start_time.isoformat(), 'timeZone': local_timezone}
            if 'end' in event_data:
                end_time = self._localize_time(event_data['end']['dateTime'], local_timezone)
                event_data['end'] = {'dateTime': end_time.isoformat(), 'timeZone': local_timezone}

            # Handle custom reminders in extendedProperties
            if 'extendedProperties' in event_data and 'private' in event_data['extendedProperties']:
                custom_reminders = event_data['extendedProperties']['private'].get('customReminders')
                if custom_reminders:
                    # Ensure the customReminders are properly formatted as a JSON string
                    if isinstance(custom_reminders, str):
                        try:
                            json.loads(custom_reminders)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in customReminders: {custom_reminders}")
                            del event_data['extendedProperties']['private']['customReminders']
                    elif isinstance(custom_reminders, list):
                        event_data['extendedProperties']['private']['customReminders'] = json.dumps(custom_reminders)
                    else:
                        logger.warning(f"Unexpected type for customReminders: {type(custom_reminders)}")
                        del event_data['extendedProperties']['private']['customReminders']

            if update_series and 'recurringEventId' in event:
                series_id = event['recurringEventId']
                updated_event = self.service.events().patch(calendarId=calendar_id, eventId=series_id, body=event_data).execute()
                return {"success": True, "message": f"Event series updated successfully. ID: {series_id}", "event": updated_event}
            else:
                updated_event = self.service.events().patch(calendarId=calendar_id, eventId=event_id, body=event_data).execute()
                return {"success": True, "message": "Event updated successfully", "event": updated_event}
        except HttpError as e:
            logging.error(f"Error in update_calendar_event: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error updating event: {str(e)}"}


    def _localize_time(self, time_str: str, timezone: str) -> datetime:
        """Convert a time string to a timezone-aware datetime object."""
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt.astimezone(pytz.timezone(timezone))


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

    def update_reminder_status(self, user_id: str, event_id: str, reminder_key: str) -> bool:
        """
        Update the reminder status for a specific event in Google Calendar.

        Args:
            user_id (str): The unique identifier for the user.
            event_id (str): The ID of the event.
            reminder_key (str): A unique key identifying the specific reminder.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        try:
            calendar_id = self.get_or_create_user_calendar(user_id)
            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()

            if 'extendedProperties' not in event:
                event['extendedProperties'] = {'private': {}}
            elif 'private' not in event['extendedProperties']:
                event['extendedProperties']['private'] = {}

            sent_reminders = json.loads(event['extendedProperties']['private'].get('sentReminders', '[]'))
            if reminder_key not in sent_reminders:
                sent_reminders.append(reminder_key)

            event['extendedProperties']['private']['sentReminders'] = json.dumps(sent_reminders)

            updated_event = self.service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
            return 'sentReminders' in updated_event.get('extendedProperties', {}).get('private', {})
        except Exception as e:
            logger.error(f"Error updating reminder status: {str(e)}", exc_info=True)
            return False

    def check_reminder_status(self, user_id: str, event_id: str, reminder_key: str) -> bool:
        """
        Check if a specific reminder has been sent for an event.

        Args:
            user_id (str): The unique identifier for the user.
            event_id (str): The ID of the event.
            reminder_key (str): A unique key identifying the specific reminder.

        Returns:
            bool: True if the reminder has been sent, False otherwise.
        """
        try:
            calendar_id = self.get_or_create_user_calendar(user_id)
            event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()

            sent_reminders = json.loads(event.get('extendedProperties', {}).get('private', {}).get('sentReminders', '[]'))
            return reminder_key in sent_reminders
        except Exception as e:
            logger.error(f"Error checking reminder status: {str(e)}", exc_info=True)
            return False

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

    def _create_message(self, to: str, subject: str, body: str, message_id: Optional[str] = None) -> Dict[str, str]:
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = self.auth_email
        message['subject'] = subject

        # Create the plain text part
        text_part = MIMEText(body, 'plain')
        # Specify the character set to ensure proper encoding
        text_part.set_charset('utf-8')
        
        message.attach(text_part)

        if message_id:
            message['In-Reply-To'] = message_id
            message['References'] = message_id

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}



def is_valid_timezone(timezone_str):
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False

def parse_datetime(dt_str, timezone):
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        return pytz.timezone(timezone).localize(dt)
    return dt.astimezone(pytz.timezone(timezone))