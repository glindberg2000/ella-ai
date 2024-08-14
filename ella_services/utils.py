# utils.py

import os
import sys
from typing import Optional, Dict, Any
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

from ella_memgpt.tools.google_utils import GoogleCalendarUtils, is_valid_timezone, parse_datetime
from ella_memgpt.tools.google_service_manager import google_service_manager
from ella_memgpt.tools.memgpt_email_router import email_router
from ella_memgpt.tools.voice_call_manager import VoiceCallManager
from ella_dbo.db_manager import get_user_data_by_field

# Initialize utilities
calendar_service = google_service_manager.get_calendar_service()
calendar_utils = GoogleCalendarUtils(calendar_service)
voice_call_manager = VoiceCallManager()

class UserDataManager:
    @staticmethod
    def get_user_data(memgpt_user_id: str) -> dict:
        """Retrieve all data for a given user."""
        try:
            logger.debug(f"Attempting to retrieve user data for ID: {memgpt_user_id}")
            user_data = get_user_data_by_field('memgpt_user_id', memgpt_user_id)
            if user_data:
                logger.debug(f"User data retrieved successfully: {user_data}")
            else:
                logger.warning(f"No user data found for ID: {memgpt_user_id}")
                # Return default user data for testing purposes
                user_data = {
                    "memgpt_user_id": memgpt_user_id,
                    "email": f"{memgpt_user_id}@example.com",
                    "local_timezone": "UTC",
                    "memgpt_user_api_key": "test_api_key",
                    "default_agent_key": "test_agent_key"
                }
                logger.info(f"Using default user data for testing: {user_data}")
            return user_data
        except Exception as e:
            logger.error(f"Error retrieving user data: {str(e)}", exc_info=True)
            return {}

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
            calendar_id = calendar_utils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                logger.error(f"Failed to get or create calendar for user {user_id}")
                return {"success": False, "message": "Failed to get or create user calendar"}

            prepared_event = calendar_utils.prepare_event_data(
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
            conflict_check = calendar_utils.check_conflicts(user_id, event_data['start'], event_data['end'], local_timezone=user_timezone)
            if not conflict_check["success"]:
                logger.warning(f"Conflict detected for event: {event_data['summary']}")
                return conflict_check  # Return conflict information

            result = calendar_utils.create_calendar_event(user_id, prepared_event, user_timezone)
            if result["success"]:
                logger.info(f"Event created successfully: {result['event']['id']}")
                return {"success": True, "event": result['event']}
            else:
                logger.error(f"Failed to create event: {result['message']}")
                return result
        except Exception as e:
            logger.error(f"Error scheduling event: {str(e)}", exc_info=True)
            return {"success": False, "message": str(e)}

# Add this method to the EventManagementUtils class
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
    async def update_event(
        user_id: str,
        event_id: str,
        title: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        reminders: Optional[str] = None,
        recurrence: Optional[str] = None,
        update_series: bool = False,
        local_timezone: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            calendar_utils = GoogleCalendarUtils(google_service_manager.get_calendar_service())
            
            if not local_timezone:
                local_timezone = UserDataManager.get_user_timezone(user_id)

            # Fetch the existing event
            existing_event = calendar_utils.get_calendar_event(user_id, event_id)
            if not existing_event:
                return {"success": False, "message": f"Event with ID {event_id} not found"}

            # Check for conflicts if start or end time is being updated
            if start is not None or end is not None:
                new_start = start or existing_event['start'].get('dateTime', existing_event['start'].get('date'))
                new_end = end or existing_event['end'].get('dateTime', existing_event['end'].get('date'))
                conflict_check = calendar_utils.check_conflicts(user_id, new_start, new_end, event_id, local_timezone)
                if not conflict_check["success"]:
                    return conflict_check  # Return conflict information

            # Prepare the update data
            update_data = calendar_utils.prepare_event_data(
                user_id,
                title or existing_event['summary'],
                start or existing_event['start'].get('dateTime', existing_event['start'].get('date')),
                end or existing_event['end'].get('dateTime', existing_event['end'].get('date')),
                description if description is not None else existing_event.get('description'),
                location if location is not None else existing_event.get('location'),
                reminders,
                recurrence if recurrence is not None else existing_event.get('recurrence'),
                local_timezone
            )

            # Remove any fields that weren't specified in the update
            if title is None:
                update_data.pop('summary', None)
            if start is None and end is None:
                update_data.pop('start', None)
                update_data.pop('end', None)
            if description is None:
                update_data.pop('description', None)
            if location is None:
                update_data.pop('location', None)
            if reminders is None:
                update_data.pop('reminders', None)
                update_data.pop('extendedProperties', None)
            if recurrence is None:
                update_data.pop('recurrence', None)

            result = calendar_utils.update_calendar_event(user_id, event_id, update_data, update_series, local_timezone)

            if result["success"]:
                return {"success": True, "event": result["event"], "message": "Event updated successfully"}
            else:
                return {"success": False, "message": result.get('message', 'Unknown error')}

        except Exception as e:
            logger.error(f"Error in update_event: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error updating event: {str(e)}"}

    @staticmethod
    async def fetch_events(
        user_id: str,
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        local_timezone: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            calendar_utils = GoogleCalendarUtils(google_service_manager.get_calendar_service())
            
            if not local_timezone:
                local_timezone = UserDataManager.get_user_timezone(user_id)

            tz = pytz.timezone(local_timezone)
            now = datetime.now(tz)

            if not time_min:
                time_min = now.isoformat()
            if not time_max:
                time_max = (now + timedelta(days=1)).isoformat()

            events_data = calendar_utils.fetch_upcoming_events(user_id, max_results, time_min, time_max, local_timezone)

            if not events_data.get('items', []):
                return {"success": True, "message": "No upcoming events found.", "events": []}

            event_list = []
            for event in events_data['items']:
                event_summary = {
                    'id': event['id'],
                    'title': event['summary'],
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'reminders': []
                }

                # Handle standard reminders
                if 'reminders' in event and 'overrides' in event['reminders']:
                    for reminder in event['reminders']['overrides']:
                        event_summary['reminders'].append({
                            'type': reminder['method'],
                            'minutes': reminder['minutes']
                        })

                # Handle custom reminders from extended properties
                if 'extendedProperties' in event and 'private' in event['extendedProperties']:
                    custom_reminders = event['extendedProperties']['private'].get('customReminders')
                    if custom_reminders:
                        try:
                            custom_reminders_list = json.loads(custom_reminders)
                            event_summary['reminders'].extend(custom_reminders_list)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in customReminders for event {event['id']}")

                # Handle recurrence
                if 'recurrence' in event:
                    event_summary['recurrence'] = event['recurrence']

                event_list.append(event_summary)

            return {"success": True, "events": event_list}

        except Exception as e:
            logger.error(f"Error in fetch_events: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error fetching events: {str(e)}"}
        
    @staticmethod
    async def delete_event(
        user_id: str,
        event_id: str,
        delete_series: bool = False
    ) -> Dict[str, Any]:
        try:
            calendar_utils = GoogleCalendarUtils(google_service_manager.get_calendar_service())

            calendar_id = calendar_utils.get_or_create_user_calendar(user_id)
            if not calendar_id:
                return {"success": False, "message": "Unable to get or create user calendar"}

            try:
                event = calendar_utils.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
                
                if delete_series and 'recurringEventId' in event:
                    # This is part of a recurring series, so we'll delete the series
                    series_id = event['recurringEventId']
                    result = calendar_utils.delete_calendar_event(user_id, series_id)
                    message = f"Event series deleted successfully. ID: {series_id}"
                else:
                    # Delete the specific instance or non-recurring event
                    result = calendar_utils.delete_calendar_event(user_id, event_id)
                    message = f"Event deleted successfully. ID: {event_id}"

                if result["success"]:
                    return {"success": True, "message": message}
                else:
                    return {"success": False, "message": f"Failed to delete event: {result.get('message', 'Unknown error')}"}

            except HttpError as e:
                if e.resp.status == 410:
                    return {"success": True, "message": f"Event (ID: {event_id}) has already been deleted."}
                else:
                    logger.error(f"HttpError in delete_event: {str(e)}", exc_info=True)
                    return {"success": False, "message": f"Error deleting event: {str(e)}"}

        except Exception as e:
            logger.error(f"Error in delete_event: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error deleting event: {str(e)}"}
