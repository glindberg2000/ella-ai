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
#from google_utils import GoogleCalendarUtils, UserDataManager, GoogleEmailUtils

def schedule_event(
    self: Agent,
    user_id: str,
    title: str,
    start: str,
    end: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    reminders: Optional[str] = None,
    recurrence: Optional[str] = None
) -> str:
    """
    Schedule an event in the user's Google Calendar with location, reminders, and recurrence.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        title (str): The title of the event.
        start (str): The start time of the event in ISO 8601 format.
        end (str): The end time of the event in ISO 8601 format.
        description (Optional[str]): An optional description for the event.
        location (Optional[str]): An optional location for the event.
        reminders (Optional[str]): Optional reminders as a comma-separated string of minutes (e.g., "10,30,60").
        recurrence (Optional[str]): Optional recurrence rule (e.g., "daily", "weekly", "monthly", "yearly", or a custom RRULE string).

    Returns:
        str: A message indicating success or failure of the event creation, including the event ID and link if successful.
    """
    import logging
    import os
    import sys
    from typing import Optional
    from dotenv import load_dotenv
    import re

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

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        # comment out for unittesting only
        from google_utils import GoogleCalendarUtils

        calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

        calendar_id = calendar_utils.get_or_create_user_calendar(user_id)
        if not calendar_id:
            return "Error: Unable to get or create user calendar"

        event_data = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {'dateTime': start, 'timeZone': 'America/Los_Angeles'},
            'end': {'dateTime': end, 'timeZone': 'America/Los_Angeles'},
        }

        if reminders:
            reminder_minutes = [int(m.strip()) for m in reminders.split(',')]
            event_data['reminders'] = {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': minutes} for minutes in reminder_minutes]
            }

        if recurrence:
            if recurrence.lower() in ['daily', 'weekly', 'monthly', 'yearly']:
                recurrence = f"RRULE:FREQ={recurrence.upper()}"
            elif not recurrence.startswith("RRULE:"):
                recurrence = "RRULE:" + recurrence
            event_data['recurrence'] = [recurrence]

        result = calendar_utils.create_calendar_event(calendar_id, event_data)

        if isinstance(result, dict):
            return f"Event created: ID: {result['id']}, Link: {result.get('htmlLink')}"
        elif isinstance(result, str):
            # Attempt to extract event ID from the link
            match = re.search(r"eid=([^&]+)", result)
            event_id = match.group(1) if match else "Unknown"
            return f"Event created: ID: {event_id}, Link: {result}"
        else:
            return "Error: Failed to create event"

    except Exception as e:
        logger.error(f"Error in schedule_event: {str(e)}", exc_info=True)
        return f"Error scheduling event: {str(e)}"
    

def fetch_events(
    self: Agent,
    user_id: str,
    max_results: int = 10,
    time_min: Optional[str] = None
) -> str:
    """
    Fetch upcoming events from the user's Google Calendar.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        max_results (int): The maximum number of events to return. Default is 10.
        time_min (Optional[str]): The start time (in ISO 8601 format) from which to fetch events.
                                  If not provided, it defaults to the current time.

    Returns:
        str: A formatted string containing the list of upcoming events or an error message.
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

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        # Comment out for unit testing only
        from google_utils import GoogleCalendarUtils

        calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

        events = calendar_utils.fetch_upcoming_events(user_id, max_results, time_min)

        if not events:
            return "No upcoming events found."

        formatted_output = "Upcoming events:\n\n"
        for event in events:
            formatted_output += f"Title: {event['summary']}\n"
            formatted_output += f"Start: {event['start']}\n"
            formatted_output += f"End: {event['end']}\n"
            formatted_output += f"Description: {event.get('description', 'No description')}\n"
            formatted_output += f"Location: {event.get('location', 'No location')}\n"
            formatted_output += f"Event ID: {event['id']}\n"
            if 'recurrence' in event:
                formatted_output += f"Recurrence: {event['recurrence'][0]}\n"
                formatted_output += "This is a recurring event. Use the series ID to modify or delete the entire series.\n"
            formatted_output += f"Event Link: {event.get('htmlLink')}\n\n"

        return formatted_output

    except Exception as e:
        logger.error(f"Error in fetch_events: {str(e)}", exc_info=True)
        return f"Error fetching events: {str(e)}"

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
    update_series: bool = False
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
        reminders (Optional[str]): New reminders as a comma-separated string of minutes (e.g., "10,30,60"). If None, reminders remain unchanged.
        recurrence (Optional[str]): New recurrence rule (e.g., "daily", "weekly", "monthly", "yearly", or a custom RRULE string). If None, recurrence remains unchanged.
        update_series (bool): If True, update the entire event series if the event is part of a recurring series.

    Returns:
        str: A message indicating success or failure of the event update.
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

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        from google_utils import GoogleCalendarUtils

        calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

        event_data = {}
        if title:
            event_data['summary'] = title
        if start:
            event_data['start'] = {'dateTime': start, 'timeZone': 'America/Los_Angeles'}
        if end:
            event_data['end'] = {'dateTime': end, 'timeZone': 'America/Los_Angeles'}
        if description:
            event_data['description'] = description
        if location:
            event_data['location'] = location
        if reminders:
            reminder_minutes = [int(m.strip()) for m in reminders.split(',')]
            event_data['reminders'] = {
                'useDefault': False,
                'overrides': [{'method': 'popup', 'minutes': minutes} for minutes in reminder_minutes]
            }
        if recurrence:
            if recurrence.lower() in ['daily', 'weekly', 'monthly', 'yearly']:
                recurrence = f"RRULE:FREQ={recurrence.upper()}"
            elif not recurrence.startswith("RRULE:"):
                recurrence = "RRULE:" + recurrence
            elif not recurrence.startswith("RRULE:FREQ="):
                return "Error: Invalid recurrence rule format"
            event_data['recurrence'] = [recurrence]

        logger.debug(f"Event data to update: {event_data}")

        result = calendar_utils.update_calendar_event(user_id, event_id, event_data, update_series)

        if result.get("success", False):
            return f"Event updated successfully. ID: {result['event']['id']}, Link: {result['event'].get('htmlLink')}"
        else:
            return f"Error updating event: {result.get('message', 'Unknown error')}"

    except Exception as e:
        logger.error(f"Error in update_event: {str(e)}", exc_info=True)
        return f"Error updating event: {str(e)}"
    

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

# List of all custom tools
CUSTOM_TOOLS = [schedule_event, update_event, send_email, fetch_events, delete_event]


