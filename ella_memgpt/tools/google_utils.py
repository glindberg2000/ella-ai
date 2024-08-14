#google_utils.py

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import pytz
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from ella_dbo.db_manager import get_db_connection, get_user_data_by_field
from ella_memgpt.tools.google_service_manager import google_service_manager
from ella_memgpt.tools.memgpt_email_router import email_router


# Setup logging
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Constants
BASE_URL = os.getenv("MEMGPT_API_URL", "http://localhost:8080")

# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Load environment variables from .env file


class UserDataManager:
    @staticmethod
    def get_user_data(memgpt_user_id: str) -> dict:
        """Retrieve all data for a given user."""
        try:
            with get_db_connection() as conn:
                logging.info(f"Attempting to retrieve data for user_id: {memgpt_user_id}")
                user_data = get_user_data_by_field('memgpt_user_id', memgpt_user_id)
                return user_data if user_data else {}
        except Exception as e:
            logging.error(f"Error retrieving user data: {str(e)}", exc_info=True)
            return {}

    @staticmethod
    def get_user_timezone(memgpt_user_id: str) -> str:
        """Retrieve the timezone for a given user."""
        try:
            with get_db_connection() as conn:
                logging.info(f"Attempting to retrieve timezone for user_id: {memgpt_user_id}")
                user_data = get_user_data_by_field('memgpt_user_id', memgpt_user_id)
                if user_data and 'local_timezone' in user_data:
                    return user_data['local_timezone']
                logging.warning(f"No timezone found for user {memgpt_user_id}. Using default: America/Los_Angeles")
                return 'America/Los_Angeles'
        except Exception as e:
            logging.error(f"Error retrieving user timezone: {str(e)}", exc_info=True)
            return 'America/Los_Angeles'

    @staticmethod
    def get_user_email(memgpt_user_id: str) -> Optional[str]:
        """Retrieve the email for a given user."""
        try:
            with get_db_connection() as conn:
                logging.info(f"Attempting to retrieve email for user_id: {memgpt_user_id}")
                user_data = get_user_data_by_field('memgpt_user_id', memgpt_user_id)
                if user_data and 'email' in user_data:
                    return user_data['email']
                logging.warning(f"No email found for user {memgpt_user_id} in user_data: {user_data}")
                default_email = "default@example.com"
                logging.warning(f"Using default email {default_email} for user_id: {memgpt_user_id}")
                return default_email
        except Exception as e:
            logging.error(f"Error retrieving user email: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def get_user_reminder_prefs(memgpt_user_id: str) -> Dict[str, Union[int, str]]:
        """Retrieve the default reminder preferences for a given user."""
        try:
            with get_db_connection() as conn:
                user_data = get_user_data_by_field('memgpt_user_id', memgpt_user_id)
                if user_data:
                    return {
                        'default_reminder_time': user_data.get('default_reminder_time', 15),
                        'reminder_method': user_data.get('reminder_method', 'email,sms')
                    }
                return {'default_reminder_time': 15, 'reminder_method': 'email,sms'}
        except Exception as e:
            logging.error(f"Error retrieving user reminder preferences: {str(e)}", exc_info=True)
            return {'default_reminder_time': 15, 'reminder_method': 'email,sms'}

    @staticmethod
    def get_user_phone(memgpt_user_id: str) -> Optional[str]:
        """Retrieve the phone number for a given user."""
        try:
            with get_db_connection() as conn:
                logging.info(f"Attempting to retrieve phone number for user_id: {memgpt_user_id}")
                user_data = get_user_data_by_field('memgpt_user_id', memgpt_user_id)
                if user_data and 'phone' in user_data:
                    return user_data['phone']
                logging.warning(f"No phone number found for user {memgpt_user_id}")
                return None
        except Exception as e:
            logging.error(f"Error retrieving user phone number: {str(e)}", exc_info=True)
            return None


class GoogleCalendarUtils:
    def __init__(self, calendar_service):
        self.service = calendar_service

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
        except RefreshError as e:
            logger.error(f"Authentication error: {str(e)}. Please check your credentials and scopes.")
            return None
        except Exception as e:
            logger.error(f"Error in get_or_create_user_calendar: {str(e)}", exc_info=True)
            return None

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

    # def prepare_event_data(
    #     self,
    #     user_id: str,
    #     title: str,
    #     start: str,
    #     end: str,
    #     description: Optional[str] = None,
    #     location: Optional[str] = None,
    #     reminders: Optional[str] = None,
    #     recurrence: Optional[str] = None,
    #     local_timezone: str = 'America/Los_Angeles'
    # ) -> Dict[str, Any]:
    #     """
    #     Prepare event data with proper handling of reminders and time zones.

    #     Args:
    #         user_id (str): The unique identifier for the user.
    #         title (str): The title of the event.
    #         start (str): The start time in ISO 8601 format.
    #         end (str): The end time in ISO 8601 format.
    #         description (Optional[str]): The description of the event.
    #         location (Optional[str]): The location of the event.
    #         reminders (Optional[str]): JSON string representation of reminders.
    #         recurrence (Optional[str]): Recurrence rule in RRULE format.
    #         local_timezone (str): The timezone for the event.

    #     Returns:
    #         Dict[str, Any]: Prepared event data ready to be used for creating or updating an event.
    #     """
    #     start_time = parse_datetime(start, local_timezone)
    #     end_time = parse_datetime(end, local_timezone)
    #     current_time = datetime.now(pytz.timezone(local_timezone))

    #     event_data = {
    #         'summary': title,
    #         'start': {'dateTime': start_time.isoformat(), 'timeZone': local_timezone},
    #         'end': {'dateTime': end_time.isoformat(), 'timeZone': local_timezone},
    #         'description': description,
    #         'location': location,
    #     }

    #     if recurrence:
    #         event_data['recurrence'] = [recurrence]

    #     # Handle reminders
    #     if reminders:
    #         reminders_list = json.loads(reminders)
    #         standard_reminders = []
    #         custom_reminders = []
    #         for reminder in reminders_list:
    #             if reminder['type'] in ['email', 'popup', 'sms']:
    #                 standard_reminders.append({'method': reminder['type'], 'minutes': reminder['minutes']})
    #             else:
    #                 custom_reminders.append(reminder)
            
    #         event_data['reminders'] = {
    #             'useDefault': False,
    #             'overrides': standard_reminders
    #         }
            
    #         if custom_reminders:
    #             event_data['extendedProperties'] = {
    #                 'private': {
    #                     'customReminders': json.dumps(custom_reminders)
    #                 }
    #             }
    #     else:
    #         # Use default reminders if none specified
    #         event_data['reminders'] = {'useDefault': True}

    #     # Ensure at least one valid reminder
    #     time_until_event = start_time - current_time
    #     if time_until_event > timedelta(0):
    #         if not event_data['reminders'].get('overrides') and event_data['reminders'].get('useDefault', True):
    #             user_prefs = UserDataManager.get_user_reminder_prefs(user_id)
    #             default_reminder_time = user_prefs['default_reminder_time']
    #             default_method = user_prefs['reminder_method'].split(',')[0]
                
    #             if time_until_event < timedelta(minutes=default_reminder_time):
    #                 # If the event is too soon for the default reminder, set an immediate reminder
    #                 immediate_reminder_minutes = max(0, time_until_event.total_seconds() // 60)
    #                 event_data['reminders'] = {
    #                     'useDefault': False,
    #                     'overrides': [{'method': default_method, 'minutes': int(immediate_reminder_minutes)}]
    #                 }

    #     return event_data
    

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
            try:
                reminders_list = json.loads(reminders)
                standard_reminders = []
                custom_reminders = []
                for reminder in reminders_list:
                    if 'method' in reminder and 'minutes' in reminder:
                        if reminder['method'] in ['email', 'popup', 'sms']:
                            standard_reminders.append({'method': reminder['method'], 'minutes': reminder['minutes']})
                        else:
                            custom_reminders.append(reminder)
                    else:
                        logger.warning(f"Invalid reminder format: {reminder}")
                
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
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in reminders: {reminders}")
                event_data['reminders'] = {'useDefault': True}
        else:
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
    


    def find_available_slots(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        conflicting_events: List[Dict[str, Any]],
        local_timezone: str
    ) -> List[Dict[str, str]]:
        tz = pytz.timezone(local_timezone)
        event_duration = end_time - start_time
        buffer = timedelta(minutes=15)  # Add a 15-minute buffer between events

        # Set business hours
        business_start = tz.localize(datetime.combine(start_time.date(), datetime.min.time())).replace(hour=9, minute=0)
        business_end = tz.localize(datetime.combine(start_time.date(), datetime.min.time())).replace(hour=17, minute=0)

        # Extend search to next 7 days
        search_end = business_end + timedelta(days=7)

        available_slots = []
        current_time = max(start_time, business_start)

        sorted_events = sorted(conflicting_events, key=lambda e: parse_datetime(e['start'], local_timezone))
        
        while current_time < search_end:
            if current_time.time() < business_start.time():
                current_time = tz.localize(datetime.combine(current_time.date(), business_start.time()))
            elif current_time.time() >= business_end.time():
                current_time = tz.localize(datetime.combine(current_time.date() + timedelta(days=1), business_start.time()))
                continue

            slot_end = min(current_time + event_duration, tz.localize(datetime.combine(current_time.date(), business_end.time())))

            is_free = True
            for event in sorted_events:
                event_start = parse_datetime(event['start'], local_timezone)
                event_end = parse_datetime(event['end'], local_timezone)

                if (event_start < slot_end) and (event_end > current_time):
                    is_free = False
                    current_time = max(current_time, event_end + buffer)
                    break

            if is_free:
                available_slots.append({
                    "start": current_time.isoformat(),
                    "end": slot_end.isoformat(),
                    "day_of_week": current_time.strftime("%A")
                })
                current_time = slot_end + buffer

            if len(available_slots) >= 10:  # Limit to 10 available slots
                break

        return available_slots
 
    def check_conflicts(
        self,
        user_id: str,
        start: str,
        end: str,
        event_id: Optional[str] = None,
        local_timezone: str = 'America/Los_Angeles'
    ) -> Dict[str, Any]:
        calendar_id = self.get_or_create_user_calendar(user_id)
        if not calendar_id:
            return {"success": False, "message": "Unable to get or create user calendar"}

        start_time = parse_datetime(start, local_timezone)
        end_time = parse_datetime(end, local_timezone)

        # Extend the search range to 7 days
        search_end = end_time + timedelta(days=7)

        events = self.fetch_upcoming_events(
            user_id=user_id,
            max_results=100,  # Increase max results to cover more days
            time_min=start_time.isoformat(),
            time_max=search_end.isoformat(),
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
            available_slots = self.find_available_slots(user_id, start_time, end_time, conflicting_events, local_timezone)
            return {
                "success": False,
                "message": "Conflicting events found.",
                "conflicts": conflicting_events,
                "available_slots": available_slots
            }
        else:
            return {"success": True, "message": "No conflicts found."}


    def suggest_alternative_times(
        self,
        start_time: datetime,
        end_time: datetime,
        conflicting_events: List[Dict[str, Any]],
        local_timezone: str
    ) -> List[Dict[str, str]]:
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
                alternative_times.append({
                    "start": suggested_start.isoformat(),
                    "end": suggested_end.isoformat()
                })

        # Suggest times between conflicts
        sorted_conflicts = sorted(conflicting_events, key=lambda e: parse_datetime(e['start'], local_timezone))
        for i in range(len(sorted_conflicts) - 1):
            current_end = parse_datetime(sorted_conflicts[i]['end'], local_timezone)
            next_start = parse_datetime(sorted_conflicts[i+1]['start'], local_timezone)
            if current_end + buffer + event_duration + buffer <= next_start:
                suggested_start = current_end + buffer
                suggested_end = suggested_start + event_duration
                alternative_times.append({
                    "start": suggested_start.isoformat(),
                    "end": suggested_end.isoformat()
                })

        # Suggest a time after the last conflict
        last_conflict = max(conflicting_events, key=lambda e: parse_datetime(e['end'], local_timezone))
        last_conflict_end = parse_datetime(last_conflict['end'], local_timezone)
        suggested_start = last_conflict_end + buffer
        suggested_end = suggested_start + event_duration
        if suggested_end < end_time + timedelta(days=1):  # Don't suggest times more than a day later
            alternative_times.append({
                "start": suggested_start.isoformat(),
                "end": suggested_end.isoformat()
            })

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

            # Log the event data being sent
            logging.info(f"Sending event data: {json.dumps(event_data, indent=2)}")

            event = self.service.events().insert(calendarId=calendar_id, body=event_data).execute()
            return {"success": True, "event": event}
        except Exception as e:
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

class GoogleEmailUtils:
    """
    A utility class for handling Gmail operations, designed to work with LLM tools.

    This class provides methods for Gmail operations using the MemGPTEmailRouter,
    with a focus on using memgpt_user_id as the primary identifier.
    """

    @staticmethod
    def send_email(memgpt_user_id: str, subject: str, body: str, message_id: Optional[str] = None) -> Dict[str, str]:
        """
        Send an email using the MemGPTEmailRouter, identified by memgpt_user_id.

        Args:
            memgpt_user_id (str): The unique identifier for the user in the MemGPT system.
            subject (str): The email subject.
            body (str): The email body.
            message_id (Optional[str]): The ID of the message being replied to, if applicable.

        Returns:
            Dict[str, str]: A dictionary containing the status and message ID of the sent email.
        """
        try:
            user_data = UserDataManager.get_user_data(memgpt_user_id)
            if not user_data:
                logger.error(f"No user data found for user ID: {memgpt_user_id}")
                return {"status": "failed", "message": "No valid user data available."}

            recipient_email = user_data.get('email')
            if not recipient_email:
                logger.error(f"No email found for user ID: {memgpt_user_id}")
                return {"status": "failed", "message": "No valid recipient email address available."}

            result = email_router.generate_and_send_email_sync(
                to_email=recipient_email,
                subject=subject,
                context={"body": body},
                memgpt_user_api_key=user_data.get('memgpt_user_api_key'),
                agent_key=user_data.get('default_agent_key'),
                message_id=message_id,
                is_reply=bool(message_id)
            )
            
            if result['status'] == 'success':
                logger.info(f"Message sent to user {memgpt_user_id} ({recipient_email}): {result['message_id']}")
            else:
                logger.error(f"Error sending email to user {memgpt_user_id}: {result['message']}")
            
            return result
        except Exception as e:
            logger.error(f"Error sending email for user {memgpt_user_id}: {str(e)}", exc_info=True)
            return {"status": "failed", "message": str(e)}


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



        # def check_conflicts(
    #     self,
    #     user_id: str,
    #     start: str,
    #     end: str,
    #     event_id: Optional[str] = None,
    #     local_timezone: str = 'America/Los_Angeles'
    # ) -> Dict[str, Any]:
    #     """
    #     Check for conflicting events in the user's calendar.

    #     Args:
    #         user_id (str): The unique identifier for the user.
    #         start (str): The start time of the event in ISO 8601 format.
    #         end (str): The end time of the event in ISO 8601 format.
    #         event_id (Optional[str]): The ID of the event being updated (if applicable).
    #         local_timezone (str): The timezone for the event.

    #     Returns:
    #         Dict[str, Any]: A dictionary containing information about conflicts and suggested alternative times.
    #     """
    #     calendar_id = self.get_or_create_user_calendar(user_id)
    #     if not calendar_id:
    #         return {"success": False, "message": "Unable to get or create user calendar"}

    #     start_time = parse_datetime(start, local_timezone)
    #     end_time = parse_datetime(end, local_timezone)

    #     # Fetch existing events
    #     events = self.fetch_upcoming_events(
    #         user_id=user_id,
    #         max_results=50,
    #         time_min=start_time.isoformat(),
    #         time_max=end_time.isoformat(),
    #         local_timezone=local_timezone
    #     )

    #     conflicting_events = []
    #     for event in events.get('items', []):
    #         if event.get('id') == event_id:
    #             continue  # Skip the event being updated (if applicable)
    #         event_start = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), local_timezone)
    #         event_end = parse_datetime(event['end'].get('dateTime', event['end'].get('date')), local_timezone)
    #         if (event_start < end_time and event_end > start_time):
    #             conflicting_events.append({
    #                 "id": event['id'],
    #                 "summary": event['summary'],
    #                 "start": event['start'].get('dateTime', event['start'].get('date')),
    #                 "end": event['end'].get('dateTime', event['end'].get('date'))
    #             })

    #     if conflicting_events:
    #         # Generate alternative times
    #         alternative_times = self.suggest_alternative_times(start_time, end_time, conflicting_events, local_timezone)
    #         return {
    #             "success": False,
    #             "message": "Conflicting events found.",
    #             "conflicts": conflicting_events,
    #             "suggested_times": alternative_times
    #         }
    #     else:
    #         return {"success": True, "message": "No conflicts found."}

    # def suggest_alternative_times(
    #     self,
    #     start_time: datetime,
    #     end_time: datetime,
    #     conflicting_events: List[Dict[str, Any]],
    #     local_timezone: str
    # ) -> List[Tuple[str, str]]:
    #     """
    #     Suggest alternative times for an event based on conflicts.

    #     Args:
    #         start_time (datetime): The original start time of the event.
    #         end_time (datetime): The original end time of the event.
    #         conflicting_events (List[Dict[str, Any]]): List of conflicting events.
    #         local_timezone (str): The timezone for the event.

    #     Returns:
    #         List[Tuple[str, str]]: A list of tuples containing suggested start and end times.
    #     """
    #     event_duration = end_time - start_time
    #     buffer = timedelta(minutes=15)  # Add a 15-minute buffer between events
    #     alternative_times = []

    #     # Suggest a time before the first conflict
    #     first_conflict = min(conflicting_events, key=lambda e: parse_datetime(e['start'], local_timezone))
    #     first_conflict_start = parse_datetime(first_conflict['start'], local_timezone)
    #     if start_time < first_conflict_start:
    #         suggested_end = first_conflict_start - buffer
    #         suggested_start = suggested_end - event_duration
    #         if suggested_start > start_time - timedelta(days=1):  # Don't suggest times more than a day earlier
    #             alternative_times.append((suggested_start.isoformat(), suggested_end.isoformat()))

    #     # Suggest times between conflicts
    #     sorted_conflicts = sorted(conflicting_events, key=lambda e: parse_datetime(e['start'], local_timezone))
    #     for i in range(len(sorted_conflicts) - 1):
    #         current_end = parse_datetime(sorted_conflicts[i]['end'], local_timezone)
    #         next_start = parse_datetime(sorted_conflicts[i+1]['start'], local_timezone)
    #         if current_end + buffer + event_duration + buffer <= next_start:
    #             suggested_start = current_end + buffer
    #             suggested_end = suggested_start + event_duration
    #             alternative_times.append((suggested_start.isoformat(), suggested_end.isoformat()))

    #     # Suggest a time after the last conflict
    #     last_conflict = max(conflicting_events, key=lambda e: parse_datetime(e['end'], local_timezone))
    #     last_conflict_end = parse_datetime(last_conflict['end'], local_timezone)
    #     suggested_start = last_conflict_end + buffer
    #     suggested_end = suggested_start + event_duration
    #     if suggested_end < end_time + timedelta(days=1):  # Don't suggest times more than a day later
    #         alternative_times.append((suggested_start.isoformat(), suggested_end.isoformat()))

    #     return alternative_times

    # def create_calendar_event(self, user_id: str, event_data: dict, local_timezone: str) -> dict:
    #     try:
    #         calendar_id = self.get_or_create_user_calendar(user_id)
    #         if not calendar_id:
    #             return {"success": False, "message": "Unable to get or create user calendar"}

    #         # Convert event times to user's timezone
    #         start_time = self._localize_time(event_data['start']['dateTime'], local_timezone)
    #         end_time = self._localize_time(event_data['end']['dateTime'], local_timezone)

    #         event_data['start'] = {'dateTime': start_time.isoformat(), 'timeZone': local_timezone}
    #         event_data['end'] = {'dateTime': end_time.isoformat(), 'timeZone': local_timezone}

    #         # Handle reminders
    #         if 'reminders' not in event_data:
    #             event_data['reminders'] = {'useDefault': True}

    #         # Handle custom reminders in extendedProperties
    #         if 'extendedProperties' in event_data and 'private' in event_data['extendedProperties']:
    #             custom_reminders = event_data['extendedProperties']['private'].get('customReminders')
    #             if custom_reminders:
    #                 # Ensure the customReminders are properly formatted as a JSON string
    #                 if isinstance(custom_reminders, str):
    #                     try:
    #                         json.loads(custom_reminders)
    #                     except json.JSONDecodeError:
    #                         logger.warning(f"Invalid JSON in customReminders: {custom_reminders}")
    #                         del event_data['extendedProperties']['private']['customReminders']
    #                 elif isinstance(custom_reminders, list):
    #                     event_data['extendedProperties']['private']['customReminders'] = json.dumps(custom_reminders)
    #                 else:
    #                     logger.warning(f"Unexpected type for customReminders: {type(custom_reminders)}")
    #                     del event_data['extendedProperties']['private']['customReminders']

    #         # Log the event data being sent
    #         logging.info(f"Sending event data: {json.dumps(event_data, indent=2)}")

    #         event = self.service.events().insert(calendarId=calendar_id, body=event_data).execute()
    #         return {"success": True, "id": event['id'], "htmlLink": event.get('htmlLink')}
    #     except HttpError as e:
    #         logging.error(f"Error creating calendar event: {str(e)}", exc_info=True)
    #         return {"success": False, "message": f"Error creating event: {str(e)}"}

    # def check_conflicts(
    #     self,
    #     user_id: str,
    #     start: str,
    #     end: str,
    #     event_id: Optional[str] = None,
    #     local_timezone: str = 'America/Los_Angeles'
    # ) -> Dict[str, Any]:
    #     calendar_id = self.get_or_create_user_calendar(user_id)
    #     if not calendar_id:
    #         return {"success": False, "message": "Unable to get or create user calendar"}

    #     start_time = parse_datetime(start, local_timezone)
    #     end_time = parse_datetime(end, local_timezone)

    #     events = self.fetch_upcoming_events(
    #         user_id=user_id,
    #         max_results=50,
    #         time_min=start_time.isoformat(),
    #         time_max=end_time.isoformat(),
    #         local_timezone=local_timezone
    #     )

    #     conflicting_events = []
    #     for event in events.get('items', []):
    #         if event.get('id') == event_id:
    #             continue  # Skip the event being updated (if applicable)
    #         event_start = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), local_timezone)
    #         event_end = parse_datetime(event['end'].get('dateTime', event['end'].get('date')), local_timezone)
    #         if (event_start < end_time and event_end > start_time):
    #             conflicting_events.append({
    #                 "id": event['id'],
    #                 "summary": event['summary'],
    #                 "start": event['start'].get('dateTime', event['start'].get('date')),
    #                 "end": event['end'].get('dateTime', event['end'].get('date'))
    #             })

    #     if conflicting_events:
    #         return {
    #             "success": False,
    #             "message": "Conflicting events found.",
    #             "conflicts": conflicting_events,
    #             "suggested_times": self.suggest_alternative_times(start_time, end_time, conflicting_events, local_timezone)
    #         }
    #     else:
    #         return {"success": True, "message": "No conflicts found."}
