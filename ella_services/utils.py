# utils.py

import os
import sys
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import pytz
import json
import logging
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

from google_utils import GoogleCalendarUtils, is_valid_timezone, parse_datetime
from google_service_manager import google_service_manager
from memgpt_email_router import email_router
from voice_call_manager import VoiceCallManager
from ella_dbo.db_manager import get_user_data_by_field

# Initialize utilities
calendar_service = google_service_manager.get_calendar_service()
calendar_utils = GoogleCalendarUtils(calendar_service)
voice_call_manager = VoiceCallManager()

class UserDataManager:
    @staticmethod
    def get_user_data(memgpt_user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve all data for a given user."""
        try:
            logger.debug(f"Attempting to retrieve user data for ID: {memgpt_user_id}")
            user_data = get_user_data_by_field('memgpt_user_id', memgpt_user_id)
            if user_data:
                logger.debug(f"User data retrieved successfully: {user_data}")
                return user_data
            else:
                logger.warning(f"No user data found for ID: {memgpt_user_id}")
                # Debug: Print all users in the database
                all_users = get_user_data_by_field('memgpt_user_id', None)  # Assuming this returns all users if field is None
                logger.debug(f"All users in database: {all_users}")
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
            user_timezone = user_data.get('local_timezone', 'UTC')
            if not is_valid_timezone(user_timezone):
                logger.warning(f"Invalid timezone for user {user_id}: {user_timezone}. Using default.")
                user_timezone = 'UTC'

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
        
    @staticmethod
    def get_or_create_user_calendar(user_id: str) -> Optional[str]:
        try:
            logger.info(f"Attempting to get or create calendar for user: {user_id}")
            user_email = UserDataManager.get_user_data(user_id).get('email')
            if not user_email:
                logger.error(f"Unable to retrieve email for user_id: {user_id}")
                return None

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
            'start': start,
            'end': end,
        }

        # Ensure start and end have the same format (dateTime)
        for time_field in ['start', 'end']:
            if 'dateTime' not in event[time_field]:
                event[time_field]['dateTime'] = event[time_field].get('date')
            if 'timeZone' not in event[time_field]:
                event[time_field]['timeZone'] = local_timezone

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


    @staticmethod
    def check_conflicts(user_id: str, start: Dict[str, Any], end: Dict[str, Any], event_id: Optional[str] = None, local_timezone: str = 'UTC') -> Dict[str, Any]:
        try:
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
    
    @staticmethod
    def find_available_slots(user_id: str, start_dt: datetime, end_dt: datetime, local_timezone: str) -> List[Dict[str, str]]:
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

    @staticmethod
    def create_calendar_event(user_id: str, event_data: Dict[str, Any], local_timezone: str) -> Dict[str, Any]:
        try:
            calendar_id = EventManagementUtils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return {"success": False, "message": "Failed to get or create user calendar"}

            event = calendar_service.events().insert(calendarId=calendar_id, body=event_data).execute()
            logger.info(f"Event created: {event.get('htmlLink')}")
            return {"success": True, "event": event}
        except Exception as e:
            logger.error(f"Error creating calendar event: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}
        
# Ensure that parse_datetime is updated to handle timezone
def parse_datetime(dt_str: str, timezone: pytz.timezone) -> datetime:
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    return timezone.localize(dt.replace(tzinfo=None))