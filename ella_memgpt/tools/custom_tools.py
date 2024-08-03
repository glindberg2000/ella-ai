# custom_tools.py

from memgpt.agent import Agent
from typing import Optional
import logging
import os
import sys
from typing import Optional, List, Dict, Union
from dotenv import load_dotenv
from enum import Enum

# Global imports for testing purposes only. Comment out the internal import versions while testing.
# from google_utils import GoogleCalendarUtils, UserDataManager, GoogleEmailUtils
# from twilio.rest import Client
    
def schedule_event(
    self: Agent,
    user_id: str,
    title: str,
    start: str,
    end: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    reminders: Optional[str] = None,
    recurrence: Optional[str] = None,
    local_timezone: Optional[str] = None
) -> str:
    """
    Schedule a new event in the user's Google Calendar.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        title (str): The title of the event.
        start (str): The start time in ISO 8601 format.
        end (str): The end time in ISO 8601 format.
        description (Optional[str]): The description of the event.
        location (Optional[str]): The location of the event.
        reminders (Optional[str]): JSON string representation of reminders. 
            Format: '[{"method": "email", "minutes": 30}, {"method": "popup", "minutes": 10}]'
            Supported reminder methods: 'email', 'popup', 'sms'
            If not provided, user's default reminder preferences will be used.
        recurrence (Optional[str]): Recurrence rule in RRULE format (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,TU").
        local_timezone (Optional[str]): The timezone for the event. If None, the user's default timezone will be used.

    Returns:
        str: A JSON string indicating success or failure of the event creation.

    Examples:
        1. Schedule a one-time event with custom reminders:
            schedule_event(
                self,
                user_id='user123',
                title='Doctor Appointment',
                start='2024-08-01T10:00:00',
                end='2024-08-01T11:00:00',
                description='Annual check-up',
                location='123 Clinic Street',
                reminders='[{"method": "email", "minutes": 30}, {"method": "popup", "minutes": 10}]'
            )

        2. Schedule a weekly recurring event with default reminders:
            schedule_event(
                self,
                user_id='user123',
                title='Morning Jog',
                start='2024-08-01T07:00:00',
                end='2024-08-01T08:00:00',
                description='Time for a refreshing jog!',
                location='The park',
                recurrence='RRULE:FREQ=WEEKLY;BYDAY=MO,TU',
                local_timezone='America/New_York'
            )
    """
    import logging
    import os
    import sys
    from typing import Optional, List, Dict, Union
    from dotenv import load_dotenv
    import json

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    try:
        load_dotenv()
        MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
        CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
        if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
            return json.dumps({"success": False, "message": "MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"})

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        from google_utils import GoogleCalendarUtils, UserDataManager, is_valid_timezone, parse_datetime

        calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

        if not local_timezone:
            local_timezone = UserDataManager.get_user_timezone(user_id)
        elif not is_valid_timezone(local_timezone):
            return json.dumps({"success": False, "message": f"Invalid timezone: {local_timezone}"})
        
        start_time = parse_datetime(start, local_timezone)
        end_time = parse_datetime(end, local_timezone)

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
        if reminders is None:
            # Fetch user's default reminder preferences
            user_prefs = UserDataManager.get_user_reminder_prefs(user_id)
            default_reminder_time = user_prefs['default_reminder_time']
            default_methods = user_prefs['reminder_method'].split(',')
            
            reminders_list = [{'method': method, 'minutes': default_reminder_time} for method in default_methods]
        else:
            reminders_list = json.loads(reminders)

        event_data['reminders'] = {
            'useDefault': False,
            'overrides': reminders_list
        }

        result = calendar_utils.create_calendar_event(user_id, event_data, local_timezone)

        if result.get("success", False):
            return json.dumps({"success": True, "message": f"Event created: ID: {result.get('id', 'Unknown')}, Link: {result.get('htmlLink', 'No link available')}"})
        else:
            return json.dumps({"success": False, "message": result.get('message', 'Failed to create event')})

    except Exception as e:
        logger.error(f"Error in schedule_event: {str(e)}", exc_info=True)
        return json.dumps({"success": False, "message": f"Error scheduling event: {str(e)}"})


def update_event(
    self: Agent,
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
) -> str:
    """
    Update an existing event in the user's Google Calendar.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        event_id (str): The unique identifier for the event to be updated.
        title (Optional[str]): The new title for the event. If None, the title remains unchanged.
        start (Optional[str]): The new start time in ISO 8601 format. If None, the start time remains unchanged.
        end (Optional[str]): The new end time in ISO 8601 format. If None, the end time remains unchanged.
        description (Optional[str]): The new description for the event. If None, the description remains unchanged.
        location (Optional[str]): The new location for the event. If None, the location remains unchanged.
        reminders (Optional[str]): JSON string representation of new reminders. 
            Format: '[{"method": "email", "minutes": 30}, {"method": "popup", "minutes": 10}]'
            Supported reminder methods: 'email', 'popup', 'sms'
            If None, reminders remain unchanged. If an empty list '[]' is provided, all reminders will be removed.
        recurrence (Optional[str]): New recurrence rule in RRULE format (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,TU"). 
            If None, recurrence remains unchanged. If an empty string is provided, recurrence will be removed.
        update_series (bool): If True, update the entire event series if the event is part of a recurring series.
        local_timezone (Optional[str]): The new timezone for the event. If None, the timezone remains unchanged.

    Returns:
        str: A JSON string containing information about the success or failure of the event update.

    Examples:
        1. Update the title and add a reminder to an existing event:
            update_event(
                self,
                user_id='user123',
                event_id='event123',
                title='Updated Doctor Appointment',
                reminders='[{"method": "email", "minutes": 45}, {"method": "popup", "minutes": 15}]'
            )

        2. Change the time and recurrence of a recurring event:
            update_event(
                self,
                user_id='user123',
                event_id='event123',
                start='2024-08-01T08:00:00',
                end='2024-08-01T09:00:00',
                recurrence='RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR',
                update_series=True
            )

        3. Remove all reminders from an event:
            update_event(
                self,
                user_id='user123',
                event_id='event123',
                reminders='[]'
            )
    """
    import logging
    import os
    import sys
    from typing import Optional, List, Dict, Union
    from dotenv import load_dotenv
    import json

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    try:
        load_dotenv()
        MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
        CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
        if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
            return json.dumps({"success": False, "message": "MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"})

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        from google_utils import GoogleCalendarUtils, UserDataManager, is_valid_timezone, parse_datetime

        calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

        if local_timezone is None:
            local_timezone = UserDataManager.get_user_timezone(user_id)
        
        if local_timezone and not is_valid_timezone(local_timezone):
            return json.dumps({"success": False, "message": f"Invalid timezone: {local_timezone}"})

        event_data = {}
        if title is not None:
            event_data['summary'] = title
        if start is not None:
            start_time = parse_datetime(start, local_timezone)
            event_data['start'] = {'dateTime': start_time.isoformat(), 'timeZone': local_timezone}
        if end is not None:
            end_time = parse_datetime(end, local_timezone)
            event_data['end'] = {'dateTime': end_time.isoformat(), 'timeZone': local_timezone}
        if description is not None:
            event_data['description'] = description
        if location is not None:
            event_data['location'] = location
        if reminders is not None:
            reminders_list = json.loads(reminders)
            event_data['reminders'] = {
                'useDefault': False,
                'overrides': reminders_list
            }
        if recurrence is not None:
            event_data['recurrence'] = [recurrence] if recurrence else None

        result = calendar_utils.update_calendar_event(user_id, event_id, event_data, update_series, local_timezone)

        if result.get("success", False):
            return json.dumps({"success": True, "event_id": result['event']['id'], "message": "Event updated successfully"})
        else:
            return json.dumps({"success": False, "message": result.get('message', 'Unknown error')})

    except Exception as e:
        logger.error(f"Error in update_event: {str(e)}", exc_info=True)
        return json.dumps({"success": False, "message": f"Error updating event: {str(e)}"})
    

def fetch_events(
    self: Agent,
    user_id: str,
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    local_timezone: Optional[str] = None
) -> str:
    """
    Fetch upcoming events from the user's Google Calendar within the specified time range.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        max_results (int): The maximum number of events to return. Default is 10.
        time_min (Optional[str]): The minimum time to filter events in ISO 8601 format. Default is None.
                                  Example: "2024-01-01T00:00:00Z" to fetch events starting from January 1, 2024.
        time_max (Optional[str]): The maximum time to filter events in ISO 8601 format. Default is None.
                                  Example: "2024-01-14T23:59:59Z" to fetch events up to January 14, 2024.
        local_timezone (Optional[str]): The timezone for the events. If None, the user's default timezone will be used.

    Returns:
        str: A JSON string describing the fetched events.
    """
    import os
    import sys
    import logging
    from dotenv import load_dotenv
    import json
    from datetime import datetime
    import pytz
    from typing import Optional

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    try:
        load_dotenv()
        MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
        CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
        if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
            return json.dumps({"success": False, "message": "MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"})

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        from google_utils import GoogleCalendarUtils, UserDataManager, is_valid_timezone, parse_datetime

        calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

        if not local_timezone:
            local_timezone = UserDataManager.get_user_timezone(user_id)
        elif not is_valid_timezone(local_timezone):
            return json.dumps({"success": False, "message": f"Invalid timezone: {local_timezone}"})

        logger.debug(f"Fetching events for user_id: {user_id}, timezone: {local_timezone}")

        tz = pytz.timezone(local_timezone)
        now = datetime.now(tz)

        if not time_min:
            time_min = now.isoformat()
        if not time_max:
            time_max = (now + timedelta(days=1)).isoformat()

        logger.debug(f"Time range: {time_min} to {time_max}")

        events_data = calendar_utils.fetch_upcoming_events(user_id, max_results, time_min, time_max, local_timezone)

        logger.debug(f"Fetched events data: {events_data}")

        if not events_data.get('items', []):
            return json.dumps({"success": True, "message": "No upcoming events found.", "events": []})

        event_list = []
        for event in events_data['items']:
            event_summary = {
                'title': event['summary'],
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'id': event['id']
            }
            event_list.append(event_summary)

        result = {
            "success": True,
            "events": event_list
        }

        return json.dumps(result)

    except Exception as e:
        logger.error(f"Error in fetch_events: {str(e)}", exc_info=True)
        return json.dumps({"success": False, "message": f"Error fetching events: {str(e)}"})

def delete_event(
    self: Agent,
    user_id: str,
    event_id: str,
    delete_series: bool = False
) -> str:
    """
    Delete an event from the user's Google Calendar.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        event_id (str): The unique identifier for the event to be deleted.
        delete_series (bool): If True, attempts to delete all instances of a recurring event series.
                              If False, deletes only the specified instance of a recurring event.
                              Defaults to False.

    Returns:
        str: A message indicating success or failure of the event deletion.
    """
    import logging
    import os
    from googleapiclient.errors import HttpError

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    try:
        CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
        if not CREDENTIALS_PATH:
            return "Error: CREDENTIALS_PATH not set in environment variables"

        logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        # Comment out internal imports for testing purposes
        from google_utils import GoogleCalendarUtils

        calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

        calendar_id = calendar_utils.get_or_create_user_calendar(user_id)
        if not calendar_id:
            return "Error: Unable to get or create user calendar"

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

            logger.debug(f"Result message: {message}")

            if isinstance(result, dict):
                if result.get('success', False):
                    return message
                else:
                    return f"Failed to delete event: {result.get('message', 'Unknown error')}"
            elif isinstance(result, bool):
                if result:
                    return message
                else:
                    return "Failed to delete event. It may not exist or you may not have permission to delete it."
            else:
                return f"Unexpected result type from delete_calendar_event: {type(result)}"

        except HttpError as e:
            if e.resp.status == 410:
                return f"Event (ID: {event_id}) has already been deleted."
            else:
                logger.error(f"HttpError in delete_event: {str(e)}", exc_info=True)
                return f"Error deleting event: {str(e)}"
        except Exception as e:
            logger.error(f"Error getting or deleting event: {str(e)}", exc_info=True)
            return f"Error deleting event: {str(e)}"

    except Exception as e:
        logger.error(f"Error in delete_event: {str(e)}", exc_info=True)
        return f"Error in delete_event function: {str(e)}"

def send_email(
    self: Agent,
    user_id: str,
    subject: str,
    body: str,
    message_id: Optional[str] = None
) -> str:
    """
    Send an email using the Google Gmail API.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user (recipient).
        subject (str): The subject of the email.
        body (str): The body content of the email.
        message_id (Optional[str]): An optional message ID for threading replies.

    Returns:
        str: A message indicating success or failure of the email sending process.
    """
    import logging
    import os
    import sys
    from dotenv import load_dotenv

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    try:
        load_dotenv()
        MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
        CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
        if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
            return "Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"

        logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
        logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        GMAIL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gmail_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        from google_utils import UserDataManager, GoogleEmailUtils

        email_utils = GoogleEmailUtils(GMAIL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)
        recipient_email = UserDataManager.get_user_email(user_id)

        if not recipient_email:
            return "Error: No valid recipient email address available."

        result = email_utils.send_email(recipient_email, subject, body, message_id)

        if result['status'] == 'success':
            return f"Message was successfully sent. Message ID: {result['message_id']}"
        else:
            return f"Message failed to send with error: {result['message']}"

    except Exception as e:
        logger.error(f"Error in send_email: {str(e)}", exc_info=True)
        return f"Error sending email: {str(e)}"


def send_sms(
    self: Agent,
    user_id: str,
    body: str,
    message_id: Optional[str] = None
) -> str:
    """
    Send an SMS message via Twilio using a MemGPT user ID.
    
    This function retrieves the user's phone number from the database using the provided MemGPT user ID.
    If successful, an SMS message is sent using the Twilio API.
    
    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user (recipient).
        body (str): The content of the SMS message.
        message_id (Optional[str]): An optional message ID for reference (not used in SMS, but included for consistency).
        
    Returns:
        str: A status message indicating success or failure.
    """
    import logging
    import os
    import sys
    from dotenv import load_dotenv
    from typing import Optional
 

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    try:
        load_dotenv()
        MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
        CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
            return "Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"
        
        logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
        logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")
        
        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)
        
        # Now that the path is set up, we can import UserDataManager
        from google_utils import UserDataManager
        # Initialize Twilio client
        from twilio.rest import Client
        
        if not account_sid or not auth_token or not from_number:
            return "Error: Twilio credentials not set in environment variables"
        
        client = Client(account_sid, auth_token)
        
        # Retrieve recipient's phone number
        recipient_phone = UserDataManager.get_user_phone(user_id)
        if not recipient_phone:
            return "Error: No valid recipient phone number available."
        
        message_status = client.messages.create(
            body=body,
            from_=from_number,
            to=recipient_phone
        )
        logger.info(f"Message sent to {recipient_phone}: {message_status.sid}")
        return "Message was successfully sent."
    except Exception as e:
        logger.error(f"Message failed to send with error: {str(e)}", exc_info=True)
        return f"Error: Message failed to send. {str(e)}"


# List of all custom tools
CUSTOM_TOOLS = [schedule_event, update_event, fetch_events, delete_event, send_email, send_sms]


