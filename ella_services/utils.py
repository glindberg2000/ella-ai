# utils.py

import os
import sys
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import pytz
import json
import logging
from ella_dbo.models import Event
from dotenv import load_dotenv

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

#from google_utils import GoogleCalendarUtils, is_valid_timezone, parse_datetime
from google_service_manager import google_service_manager
from memgpt_email_router import email_router
from voice_call_manager import VoiceCallManager
from ella_dbo.db_manager import get_user_data_by_field

# Initialize utilities
calendar_service = google_service_manager.get_calendar_service()
#calendar_utils = GoogleCalendarUtils(calendar_service)
voice_call_manager = VoiceCallManager()

class UserDataManager:
    @staticmethod
    def get_user_data(memgpt_user_id: str) -> Optional[Dict[str, Any]]:
        try:
            logger.debug(f"Attempting to retrieve user data for ID: {memgpt_user_id}")
            user_data = get_user_data_by_field('memgpt_user_id', memgpt_user_id)
            if user_data:
                logger.debug(f"Raw user data retrieved: {user_data}")
                
                # Map database fields to expected fields
                mapped_data = {
                    'email': user_data.get('email'),
                    'memgpt_api_key': user_data.get('memgpt_user_api_key'),
                    'agent_key': user_data.get('default_agent_key'),
                    'local_timezone': user_data.get('local_timezone', 'UTC')
                }
                
                # Check for missing or empty required fields
                required_fields = ['email', 'memgpt_api_key', 'agent_key']
                for field in required_fields:
                    if not mapped_data.get(field):
                        logger.warning(f"Missing or empty required field '{field}' for user {memgpt_user_id}")
                        logger.debug(f"Database value for {field}: {user_data.get(field)}")
                
                return mapped_data
            else:
                logger.warning(f"No user data found for ID: {memgpt_user_id}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving user data: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def get_user_timezone(memgpt_user_id: str) -> str:
        """Retrieve the timezone for a given user."""
        user_data = UserDataManager.get_user_data(memgpt_user_id)
        timezone = user_data.get('local_timezone', 'UTC')
        logger.debug(f"Retrieved timezone for user {memgpt_user_id}: {timezone}")
        return timezone

class EventManagementUtils:
    @staticmethod
    async def schedule_event(user_id: str, event_data: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            user_timezone = str(user_data.get('local_timezone', 'UTC'))
            logger.debug(f"User timezone: {user_timezone}")
            
            if not is_valid_timezone(user_timezone):
                logger.warning(f"Invalid timezone for user {user_id}: {user_timezone}. Using default.")
                user_timezone = 'UTC'

            # Ensure event_data timezones are strings
            for time_field in ['start', 'end']:
                if 'timeZone' in event_data[time_field]:
                    logger.debug(f"Original {time_field} timeZone: {event_data[time_field]['timeZone']}")
                    event_data[time_field]['timeZone'] = str(event_data[time_field]['timeZone'])
                    logger.debug(f"Converted {time_field} timeZone: {event_data[time_field]['timeZone']}")

            # Get or create user's calendar
            calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                logger.error(f"Failed to get or create calendar for user {user_id}")
                return {"success": False, "message": "Failed to get or create user calendar"}

            prepared_event = EventManagementUtils.prepare_event_data(
                user_id,
                event_data['summary'],
                event_data['start'],
                event_data['end'],
                event_data.get('description'),
                event_data.get('location'),
                event_data.get('reminders'),
                event_data.get('recurrence'),
                user_timezone
            )
            logger.debug(f"Prepared event: {prepared_event}")

            # Check for conflicts
            conflict_check = EventManagementUtils.check_conflicts(user_id, event_data['start'], event_data['end'], local_timezone=user_timezone)
            if not conflict_check["success"]:
                logger.warning(f"Conflict detected for event: {event_data['summary']}")
                return conflict_check  # Return conflict information

            result = EventManagementUtils.create_calendar_event(user_id, prepared_event, user_timezone)
            if result["success"]:
                logger.info(f"Event created successfully: {result['event']['id']}")
                result['event']['local_timezone'] = user_timezone  # Add local_timezone to the event data
                return {"success": True, "event": result['event']}
            else:
                logger.error(f"Failed to create event: {result['message']}")
                return result
        except Exception as e:
            logger.error(f"Error scheduling event: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}

    # @staticmethod
    # def get_or_create_user_calendar(user_id: str) -> Optional[str]:
    #     try:
    #         logger.info(f"Attempting to get or create calendar for user: {user_id}")
    #         user_email = UserDataManager.get_user_data(user_id).get('email')
    #         if not user_email:
    #             logger.error(f"Unable to retrieve email for user_id: {user_id}")
    #             return None

    #         calendar_summary = f"User-{user_id}-Calendar"
    #         calendars = calendar_service.calendarList().list().execute()
    #         for calendar in calendars.get("items", []):
    #             if calendar["summary"] == calendar_summary:
    #                 logger.info(f"Calendar {calendar_summary} already exists.")
    #                 return calendar["id"]

    #         # Create new calendar
    #         new_calendar = {"summary": calendar_summary, "timeZone": "UTC"}
    #         created_calendar = calendar_service.calendars().insert(body=new_calendar).execute()
    #         logger.info(f"Created new calendar: {created_calendar['id']}")
            
    #         # Set permissions
    #         rule = {
    #             'scope': {
    #                 'type': 'user',
    #                 'value': user_email
    #             },
    #             'role': 'owner'
    #         }
    #         calendar_service.acl().insert(calendarId=created_calendar['id'], body=rule).execute()
    #         logger.info(f"Set calendar permissions for {user_email} on calendar {created_calendar['id']}")
            
    #         return created_calendar['id']
    #     except Exception as e:
    #         logger.error(f"Error in get_or_create_user_calendar: {str(e)}", exc_info=True)
    #         return None

    @staticmethod
    def get_or_create_user_calendar(user_id: str) -> Optional[str]:
        try:
            logger.info(f"Attempting to get or create calendar for user: {user_id}")
            user_email = UserDataManager.get_user_data(user_id).get('email')
            if not user_email:
                logger.error(f"Unable to retrieve email for user_id: {user_id}")
                return None

            auth_email = google_service_manager.get_auth_email()
            if not auth_email:
                logger.error(f"Unable to retrieve authenticated email")
                return None
            # Fetch the latest calendar service
            calendar_service = google_service_manager.get_calendar_service()

            calendar_summary = f"User-{user_id}-Calendar"
            calendars = calendar_service.calendarList().list().execute()
            for calendar in calendars.get("items", []):
                if calendar["summary"] == calendar_summary:
                    logger.info(f"Calendar {calendar_summary} already exists.")
                    return calendar["id"]

            # Create new calendar
            new_calendar = {"summary": calendar_summary, "timeZone": "UTC"}
            created_calendar = calendar_service.calendars().insert(body=new_calendar).execute()
            logger.info(f"Created new calendar: {created_calendar['id']}")
            
            # Set permissions
            rule = {
                'scope': {
                    'type': 'user',
                    'value': user_email
                },
                'role': 'owner'
            }
            calendar_service.acl().insert(calendarId=created_calendar['id'], body=rule).execute()
            logger.info(f"Set calendar permissions for {user_email} on calendar {created_calendar['id']}")
            
            return created_calendar['id']
        except Exception as e:
            logger.error(f"Error in get_or_create_user_calendar: {str(e)}", exc_info=True)
            return None
        
    @staticmethod
    def prepare_event_data(
        user_id: str,
        summary: str,
        start: Dict[str, Any],
        end: Dict[str, Any],
        description: Optional[str] = None,
        location: Optional[str] = None,
        reminders: Optional[Union[str, Dict[str, Any]]] = None,
        recurrence: Optional[str] = None,
        local_timezone: str = 'UTC'
    ) -> Dict[str, Any]:
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': start.copy(),  # Create a copy to avoid modifying the original dict
            'end': end.copy(),  # Create a copy to avoid modifying the original dict
        }

        # Ensure start and end have the same format (dateTime) and string timezone
        for time_field in ['start', 'end']:
            if 'dateTime' not in event[time_field]:
                event[time_field]['dateTime'] = event[time_field].get('date')
            if 'timeZone' not in event[time_field] or not isinstance(event[time_field]['timeZone'], str):
                event[time_field]['timeZone'] = str(local_timezone)

        if recurrence:
            event['recurrence'] = [recurrence]

        if reminders:
            if isinstance(reminders, str):
                try:
                    reminder_data = json.loads(reminders)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid reminders format for user {user_id}: {reminders}")
                    reminder_data = None
            elif isinstance(reminders, dict):
                reminder_data = reminders
            else:
                logger.warning(f"Unsupported reminders format for user {user_id}: {type(reminders)}")
                reminder_data = None

            if reminder_data:
                event['reminders'] = {
                    'useDefault': False,
                    'overrides': reminder_data.get('overrides', [])
                }

        return event


    # @staticmethod
    # def check_conflicts(user_id: str, start: Dict[str, Any], end: Dict[str, Any], event_id: Optional[str] = None, local_timezone: str = 'UTC') -> Dict[str, Any]:
    #     try:
    #         calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
    #         if not calendar_id:
    #             return {"success": False, "message": "Failed to get user calendar"}

    #         tz = pytz.timezone(local_timezone)
    #         start_dt = parse_datetime(start['dateTime'], tz)
    #         end_dt = parse_datetime(end['dateTime'], tz)

    #         # Fetch events within the time range
    #         events_result = calendar_service.events().list(
    #             calendarId=calendar_id,
    #             timeMin=start_dt.isoformat(),
    #             timeMax=end_dt.isoformat(),
    #             singleEvents=True,
    #             orderBy='startTime'
    #         ).execute()

    #         conflicts = []
    #         for event in events_result.get('items', []):
    #             if event['id'] == event_id:
    #                 continue  # Skip the event being updated

    #             event_start = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), tz)
    #             event_end = parse_datetime(event['end'].get('dateTime', event['end'].get('date')), tz)

    #             if (start_dt < event_end and end_dt > event_start):
    #                 conflicts.append({
    #                     'id': event['id'],
    #                     'summary': event['summary'],
    #                     'start': event['start'],
    #                     'end': event['end']
    #                 })

    #         if conflicts:
    #             return {
    #                 "success": False,
    #                 "message": "Conflicting events found",
    #                 "conflicts": conflicts,
    #                 "available_slots": EventManagementUtils.find_available_slots(user_id, start_dt, end_dt, local_timezone)
    #             }

    #         return {"success": True}
    #     except Exception as e:
    #         logger.error(f"Error checking conflicts: {str(e)}", exc_info=True)
    #         return {"success": False, "message": str(e)}

    @staticmethod
    def check_conflicts(user_id: str, start: Dict[str, Any], end: Dict[str, Any], event_id: Optional[str] = None, local_timezone: str = 'UTC') -> Dict[str, Any]:
        try:
            # Fetch the latest calendar service
            calendar_service = google_service_manager.get_calendar_service()
            
            calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return {"success": False, "message": "Failed to get user calendar"}

            tz = pytz.timezone(local_timezone)
            start_dt = parse_datetime(start['dateTime'], tz)
            end_dt = parse_datetime(end['dateTime'], tz)

            # Fetch events within the time range
            events_result = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            conflicts = []
            for event in events_result.get('items', []):
                if event['id'] == event_id:
                    continue  # Skip the event being updated

                event_start = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), tz)
                event_end = parse_datetime(event['end'].get('dateTime', event['end'].get('date')), tz)

                if (start_dt < event_end and end_dt > event_start):
                    conflicts.append({
                        'id': event['id'],
                        'summary': event['summary'],
                        'start': event['start'],
                        'end': event['end']
                    })

            if conflicts:
                return {
                    "success": False,
                    "message": "Conflicting events found",
                    "conflicts": conflicts,
                    "available_slots": EventManagementUtils.find_available_slots(user_id, start_dt, end_dt, local_timezone)
                }

            return {"success": True}
        except Exception as e:
            logger.error(f"Error checking conflicts: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}


    # @staticmethod
    # def find_available_slots(user_id: str, start_dt: datetime, end_dt: datetime, local_timezone: str) -> List[Dict[str, str]]:
    #     calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
    #     if not calendar_id:
    #         return []

    #     tz = pytz.timezone(local_timezone)
    #     events_result = calendar_service.events().list(
    #         calendarId=calendar_id,
    #         timeMin=start_dt.isoformat(),
    #         timeMax=(end_dt + timedelta(days=7)).isoformat(),  # Look for slots up to a week after the requested end time
    #         singleEvents=True,
    #         orderBy='startTime'
    #     ).execute()

    #     events = events_result.get('items', [])
    #     available_slots = []
    #     current_slot_start = start_dt

    #     for event in events:
    #         event_start = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), tz)
    #         if current_slot_start < event_start:
    #             available_slots.append({
    #                 'start': current_slot_start.isoformat(),
    #                 'end': event_start.isoformat()
    #             })
    #         current_slot_start = parse_datetime(event['end'].get('dateTime', event['end'].get('date')), tz)

    #     if current_slot_start < end_dt:
    #         available_slots.append({
    #             'start': current_slot_start.isoformat(),
    #             'end': end_dt.isoformat()
    #         })

    #     return available_slots

    @staticmethod
    def find_available_slots(user_id: str, start_dt: datetime, end_dt: datetime, local_timezone: str) -> List[Dict[str, str]]:
        # Fetch the latest calendar service
        calendar_service = google_service_manager.get_calendar_service()

        calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
        if not calendar_id:
            return []

        tz = pytz.timezone(local_timezone)
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=start_dt.isoformat(),
            timeMax=(end_dt + timedelta(days=7)).isoformat(),  # Look for slots up to a week after the requested end time
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        available_slots = []
        current_slot_start = start_dt

        for event in events:
            event_start = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), tz)
            if current_slot_start < event_start:
                available_slots.append({
                    'start': current_slot_start.isoformat(),
                    'end': event_start.isoformat()
                })
            current_slot_start = parse_datetime(event['end'].get('dateTime', event['end'].get('date')), tz)

        if current_slot_start < end_dt:
            available_slots.append({
                'start': current_slot_start.isoformat(),
                'end': end_dt.isoformat()
            })

        return available_slots

    # @staticmethod
    # def create_calendar_event(user_id: str, event_data: Dict[str, Any], local_timezone: str) -> Dict[str, Any]:
    #     try:
    #         calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
    #         if not calendar_id:
    #             return {"success": False, "message": "Failed to get or create user calendar"}

    #         # Ensure the time zone is in the correct format
    #         valid_timezones = pytz.all_timezones
    #         if local_timezone not in valid_timezones:
    #             logger.warning(f"Invalid timezone: {local_timezone}. Defaulting to UTC.")
    #             local_timezone = 'UTC'

    #         # Update the event data with the correct time zone
    #         for time_field in ['start', 'end']:
    #             if 'dateTime' in event_data[time_field]:
    #                 dt = parse_datetime(event_data[time_field]['dateTime'], local_timezone)
    #                 event_data[time_field]['dateTime'] = dt.isoformat()
    #                 event_data[time_field]['timeZone'] = local_timezone

    #         logger.debug(f"Sending event data to Google Calendar API: {event_data}")

    #         event = calendar_service.events().insert(calendarId=calendar_id, body=event_data).execute()
    #         logger.info(f"Event created: {event.get('htmlLink')}")
    #         return {"success": True, "event": event}
    #     except HttpError as e:
    #         logger.error(f"HTTP error creating calendar event: {str(e)}", exc_info=True)
    #         return {"success": False, "message": str(e)}
    #     except Exception as e:
    #         logger.error(f"Error creating calendar event: {str(e)}", exc_info=True)
    #         return {"success": False, "message": str(e)}

    @staticmethod
    def create_calendar_event(user_id: str, event_data: Dict[str, Any], local_timezone: str) -> Dict[str, Any]:
        try:
            # Always fetch the latest calendar service
            calendar_service = google_service_manager.get_calendar_service()
            
            calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return {"success": False, "message": "Failed to get or create user calendar"}

            # Ensure the time zone is in the correct format
            valid_timezones = pytz.all_timezones
            if local_timezone not in valid_timezones:
                logger.warning(f"Invalid timezone: {local_timezone}. Defaulting to UTC.")
                local_timezone = 'UTC'

            # Update the event data with the correct time zone
            for time_field in ['start', 'end']:
                if 'dateTime' in event_data[time_field]:
                    dt = parse_datetime(event_data[time_field]['dateTime'], local_timezone)
                    event_data[time_field]['dateTime'] = dt.isoformat()
                    event_data[time_field]['timeZone'] = local_timezone

            logger.debug(f"Sending event data to Google Calendar API: {event_data}")

            event = calendar_service.events().insert(calendarId=calendar_id, body=event_data).execute()
            logger.info(f"Event created: {event.get('htmlLink')}")
            return {"success": True, "event": event}
        except HttpError as e:
            logger.error(f"HTTP error creating calendar event: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}
        except Exception as e:
            logger.error(f"Error creating calendar event: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}
            
    # @staticmethod
    # async def fetch_events(
    #     user_id: str,
    #     max_results: int = 10,
    #     time_min: Optional[str] = None,
    #     time_max: Optional[str] = None,
    #     local_timezone: str = 'UTC'
    # ) -> Dict[str, Any]:
    #     try:
    #         calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
    #         if not calendar_id:
    #             return {"success": False, "message": "Failed to get user calendar"}

    #         tz = pytz.timezone(local_timezone)
    #         now = datetime.now(tz)

    #         if time_min:
    #             time_min = parse_datetime(time_min, tz)
    #         else:
    #             time_min = now

    #         if time_max:
    #             time_max = parse_datetime(time_max, tz)
    #         else:
    #             time_max = now + timedelta(days=30)  # Default to 30 days from now

    #         events_result = calendar_service.events().list(
    #             calendarId=calendar_id,
    #             timeMin=time_min.isoformat(),
    #             timeMax=time_max.isoformat(),
    #             maxResults=max_results,
    #             singleEvents=True,
    #             orderBy='startTime'
    #         ).execute()

    #         events = events_result.get('items', [])
    #         formatted_events: List[Dict[str, Any]] = []

    #         for event in events:
    #             formatted_event = Event(
    #                 id=event['id'],
    #                 summary=event['summary'],
    #                 start=event['start'],
    #                 end=event['end'],
    #                 description=event.get('description', ''),
    #                 location=event.get('location', ''),
    #                 reminders=event.get('reminders', {}),
    #                 recurrence=event.get('recurrence', []),
    #                 local_timezone=local_timezone
    #             )
    #             formatted_events.append(formatted_event.dict())

    #         return {
    #             "success": True,
    #             "events": formatted_events,
    #             "nextPageToken": events_result.get('nextPageToken')
    #         }
    #     except Exception as e:
    #         logger.error(f"Error fetching events: {str(e)}", exc_info=True)
    #         return {"success": False, "message": str(e)}

    @staticmethod
    async def fetch_events(
        user_id: str,
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        local_timezone: str = 'UTC'
    ) -> Dict[str, Any]:
        try:
            # Always fetch the latest calendar service
            calendar_service = google_service_manager.get_calendar_service()
            
            calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return {"success": False, "message": "Failed to get user calendar"}

            tz = pytz.timezone(local_timezone)
            now = datetime.now(tz)

            if time_min:
                time_min = parse_datetime(time_min, tz)
            else:
                time_min = now

            if time_max:
                time_max = parse_datetime(time_max, tz)
            else:
                time_max = now + timedelta(days=30)  # Default to 30 days from now

            events_result = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            formatted_events: List[Dict[str, Any]] = []

            for event in events:
                formatted_event = Event(
                    id=event['id'],
                    summary=event['summary'],
                    start=event['start'],
                    end=event['end'],
                    description=event.get('description', ''),
                    location=event.get('location', ''),
                    reminders=event.get('reminders', {}),
                    recurrence=event.get('recurrence', []),
                    local_timezone=local_timezone
                )
                formatted_events.append(formatted_event.dict())

            return {
                "success": True,
                "events": formatted_events,
                "nextPageToken": events_result.get('nextPageToken')
            }
        except Exception as e:
            logger.error(f"Error fetching events: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}
    
    # @staticmethod
    # async def delete_event(
    #     user_id: str,
    #     event_id: str,
    #     delete_series: bool = False
    # ) -> str:
    #     try:
    #         calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
    #         if not calendar_id:
    #             return "Failed to get user calendar"

    #         if delete_series:
    #             # To delete a recurring event series, we need to fetch the event first
    #             event = calendar_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    #             if 'recurringEventId' in event:
    #                 event_id = event['recurringEventId']

    #         calendar_service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    #         return f"Event {event_id} deleted successfully"
    #     except Exception as e:
    #         logger.error(f"Error deleting event: {str(e)}", exc_info=True)
    #         return f"Error deleting event: {str(e)}"

    @staticmethod
    async def delete_event(
        user_id: str,
        event_id: str,
        delete_series: bool = False
    ) -> str:
        try:
            # Fetch the latest calendar service
            calendar_service = google_service_manager.get_calendar_service()
            
            calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return "Failed to get user calendar"

            if delete_series:
                # To delete a recurring event series, we need to fetch the event first
                event = calendar_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
                if 'recurringEventId' in event:
                    event_id = event['recurringEventId']

            calendar_service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return f"Event {event_id} deleted successfully"
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}", exc_info=True)
            return f"Error deleting event: {str(e)}"
        
    # @staticmethod
    # async def update_event(
    #     user_id: str,
    #     event_id: str,
    #     title: Optional[str] = None,
    #     start: Optional[Dict[str, Any]] = None,
    #     end: Optional[Dict[str, Any]] = None,
    #     description: Optional[str] = None,
    #     location: Optional[str] = None,
    #     reminders: Optional[Dict[str, Any]] = None,
    #     recurrence: Optional[List[str]] = None,
    #     update_series: bool = False,
    #     local_timezone: str = 'America/Los_Angeles'
    # ) -> str:
    #     try:
    #         calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
    #         if not calendar_id:
    #             return json.dumps({"success": False, "message": "Failed to get user calendar"})

    #         # Fetch the existing event
    #         event = calendar_service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    #         # Prepare the update data
    #         update_data = {}
    #         if title is not None:
    #             update_data['summary'] = title
    #         else:
    #             # If title is not provided, use the existing summary
    #             update_data['summary'] = event.get('summary', '')
            
    #         if start is not None:
    #             update_data['start'] = start
    #         if end is not None:
    #             update_data['end'] = end
    #         if description is not None:
    #             update_data['description'] = description
    #         if location is not None:
    #             update_data['location'] = location
    #         if reminders is not None:
    #             update_data['reminders'] = reminders
    #         if recurrence is not None:
    #             update_data['recurrence'] = recurrence

    #         # Update the event
    #         updated_event = calendar_service.events().update(
    #             calendarId=calendar_id,
    #             eventId=event_id,
    #             body=update_data
    #         ).execute()

    #         return json.dumps({"success": True, "event": updated_event})
    #     except Exception as e:
    #         logger.error(f"Error updating event: {str(e)}", exc_info=True)
    #         return json.dumps({"success": False, "message": str(e)})
    #     # @staticmethod
    #     # async def update_event(
    #     #     user_id: str,
    #     #     event_id: str,
    #     #     title: Optional[str] = None,
    #     #     start: Optional[Dict[str, Any]] = None,
    #     #     end: Optional[Dict[str, Any]] = None,
    #     #     description: Optional[str] = None,
    #     #     location: Optional[str] = None,
    #     #     reminders: Optional[Dict[str, Any]] = None,
    #     #     recurrence: Optional[List[str]] = None,
    #     #     update_series: bool = False,
    #     #     local_timezone: str = 'UTC'
    #     # ) -> str:
    #     #     try:
    #     #         calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
    #     #         if not calendar_id:
    #     #             return json.dumps({"success": False, "message": "Failed to get user calendar"})

    #     #         # Fetch the existing event
    #     #         event = calendar_service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    #     #         # Prepare the update data
    #     #         update_data = {}
    #     #         if title is not None:
    #     #             update_data['summary'] = title
    #     #         if start is not None:
    #     #             update_data['start'] = start
    #     #         if end is not None:
    #     #             update_data['end'] = end
    #     #         if description is not None:
    #     #             update_data['description'] = description
    #     #         if location is not None:
    #     #             update_data['location'] = location
    #     #         if reminders is not None:
    #     #             update_data['reminders'] = reminders
    #     #         if recurrence is not None:
    #     #             update_data['recurrence'] = recurrence


    #     #         # Check for conflicts if start or end time is being updated
    #     #         if start is not None or end is not None:
    #     #             conflict_check = EventManagementUtils.check_conflicts(
    #     #                 user_id,
    #     #                 update_data.get('start', event['start']),
    #     #                 update_data.get('end', event['end']),
    #     #                 event_id,
    #     #                 local_timezone
    #     #             )
    #     #             if not conflict_check["success"]:
    #     #                 return json.dumps(conflict_check)

    #     #         # Update the event
    #     #         updated_event = calendar_service.events().update(
    #     #             calendarId=calendar_id,
    #     #             eventId=event_id,
    #     #             body=update_data
    #     #         ).execute()

    #     #         return json.dumps({"success": True, "event": updated_event})
    #     #     except Exception as e:
    #     #         logger.error(f"Error updating event: {str(e)}", exc_info=True)
    #     #         return json.dumps({"success": False, "message": str(e)})
    @staticmethod
    async def update_event(
        user_id: str,
        event_id: str,
        title: Optional[str] = None,
        start: Optional[Dict[str, Any]] = None,
        end: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        reminders: Optional[Dict[str, Any]] = None,
        recurrence: Optional[List[str]] = None,
        update_series: bool = False,
        local_timezone: str = 'America/Los_Angeles'
    ) -> str:
        try:
            # Fetch the latest calendar service
            calendar_service = google_service_manager.get_calendar_service()
            
            calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return json.dumps({"success": False, "message": "Failed to get user calendar"})

            # Fetch the existing event
            event = calendar_service.events().get(calendarId=calendar_id, eventId=event_id).execute()

            # Prepare the update data
            update_data = {}
            if title is not None:
                update_data['summary'] = title
            else:
                # If title is not provided, use the existing summary
                update_data['summary'] = event.get('summary', '')
            
            if start is not None:
                update_data['start'] = start
            if end is not None:
                update_data['end'] = end
            if description is not None:
                update_data['description'] = description
            if location is not None:
                update_data['location'] = location
            if reminders is not None:
                update_data['reminders'] = reminders
            if recurrence is not None:
                update_data['recurrence'] = recurrence

            # Update the event
            # Update the event
            updated_event = calendar_service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=update_data
            ).execute()

            return json.dumps({"success": True, "event": updated_event})
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}", exc_info=True)
            return json.dumps({"success": False, "message": str(e)})
        
    # @staticmethod
    # def check_reminder_status(user_id: str, event_id: str, reminder_key: str) -> bool:
    #     try:
    #         calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
    #         if not calendar_id:
    #             logger.error(f"Failed to get calendar for user {user_id}")
    #             return False

    #         event = google_service_manager.get_calendar_service().events().get(
    #             calendarId=calendar_id,
    #             eventId=event_id
    #         ).execute()

    #         sent_reminders = json.loads(event.get('extendedProperties', {}).get('private', {}).get('sentReminders', '[]'))
    #         return reminder_key in sent_reminders
    #     except Exception as e:
    #         logger.error(f"Error checking reminder status: {str(e)}", exc_info=True)
    #         return False

    @staticmethod
    def check_reminder_status(user_id: str, event_id: str, reminder_key: str) -> bool:
        try:
            # Fetch the latest calendar service
            calendar_service = google_service_manager.get_calendar_service()
            
            calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                logger.error(f"Failed to get calendar for user {user_id}")
                return False

            event = calendar_service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            sent_reminders = json.loads(event.get('extendedProperties', {}).get('private', {}).get('sentReminders', '[]'))
            return reminder_key in sent_reminders
        except Exception as e:
            logger.error(f"Error checking reminder status: {str(e)}", exc_info=True)
            return False
        
    # @staticmethod
    # def update_reminder_status(user_id: str, event_id: str, reminder_key: str) -> bool:
    #     try:
    #         calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
    #         if not calendar_id:
    #             logger.error(f"Failed to get calendar for user {user_id}")
    #             return False

    #         event = google_service_manager.get_calendar_service().events().get(
    #             calendarId=calendar_id,
    #             eventId=event_id
    #         ).execute()

    #         if 'extendedProperties' not in event:
    #             event['extendedProperties'] = {'private': {}}
    #         elif 'private' not in event['extendedProperties']:
    #             event['extendedProperties']['private'] = {}

    #         sent_reminders = json.loads(event['extendedProperties']['private'].get('sentReminders', '[]'))
    #         if reminder_key not in sent_reminders:
    #             sent_reminders.append(reminder_key)

    #         event['extendedProperties']['private']['sentReminders'] = json.dumps(sent_reminders)

    #         updated_event = google_service_manager.get_calendar_service().events().update(
    #             calendarId=calendar_id,
    #             eventId=event_id,
    #             body=event
    #         ).execute()

    #         return 'sentReminders' in updated_event.get('extendedProperties', {}).get('private', {})
    #     except Exception as e:
    #         logger.error(f"Error updating reminder status: {str(e)}", exc_info=True)
    #         return False

    @staticmethod
    def update_reminder_status(user_id: str, event_id: str, reminder_key: str) -> bool:
        try:
            # Fetch the latest calendar service
            calendar_service = google_service_manager.get_calendar_service()
            
            calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                logger.error(f"Failed to get calendar for user {user_id}")
                return False

            event = calendar_service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            if 'extendedProperties' not in event:
                event['extendedProperties'] = {'private': {}}
            elif 'private' not in event['extendedProperties']:
                event['extendedProperties']['private'] = {}

            sent_reminders = json.loads(event['extendedProperties']['private'].get('sentReminders', '[]'))
            if reminder_key not in sent_reminders:
                sent_reminders.append(reminder_key)

            event['extendedProperties']['private']['sentReminders'] = json.dumps(sent_reminders)

            updated_event = calendar_service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            return 'sentReminders' in updated_event.get('extendedProperties', {}).get('private', {})
        except Exception as e:
            logger.error(f"Error updating reminder status: {str(e)}", exc_info=True)
            return False
    
class GoogleEmailUtils:
    @staticmethod
    def send_email(memgpt_user_id: str, subject: str, body: str, message_id: Optional[str] = None) -> Dict[str, str]:
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

# Ensure that parse_datetime is updated to handle timezone
# def parse_datetime(dt_str: str, timezone: pytz.timezone) -> datetime:
#     dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
#     return timezone.localize(dt.replace(tzinfo=None))

import pytz
from datetime import datetime

def parse_datetime(dt_str: str, timezone_str: Union[str, pytz.tzinfo.BaseTzInfo]) -> datetime:
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    if isinstance(timezone_str, str):
        timezone = pytz.timezone(timezone_str)
    elif isinstance(timezone_str, pytz.tzinfo.BaseTzInfo):
        timezone = timezone_str
    else:
        raise ValueError(f"Invalid timezone type: {type(timezone_str)}")
    
    if dt.tzinfo is None:
        return timezone.localize(dt)
    return dt.astimezone(timezone)

import pytz

def is_valid_timezone(timezone_str):
    logger.debug(f"Checking timezone validity: {timezone_str}")
    if isinstance(timezone_str, pytz.tzinfo.BaseTzInfo):
        logger.debug(f"Timezone is a pytz.tzinfo.BaseTzInfo object")
        return True
    try:
        pytz.timezone(str(timezone_str))
        logger.debug(f"Timezone {timezone_str} is valid")
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone: {timezone_str}")
        return False