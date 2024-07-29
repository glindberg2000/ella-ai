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

# def schedule_event(
#     self: Agent,
#     user_id: str,
#     title: str,
#     start: str,
#     end: str,
#     description: Optional[str] = None,
#     location: Optional[str] = None,
#     reminders: Optional[str] = None,
#     recurrence: Optional[str] = None
# ) -> str:
#     """
#     Schedule an event in the user's Google Calendar with location, reminders, and recurrence.

#     Args:
#         self (Agent): The agent instance calling the tool.
#         user_id (str): The unique identifier for the user.
#         title (str): The title of the event.
#         start (str): The start time of the event in ISO 8601 format.
#         end (str): The end time of the event in ISO 8601 format.
#         description (Optional[str]): An optional description for the event.
#         location (Optional[str]): An optional location for the event.
#         reminders (Optional[str]): Optional reminders as a comma-separated string of minutes (e.g., "10,30,60").
#         recurrence (Optional[str]): Optional recurrence rule (e.g., "daily", "weekly", "monthly", "yearly", or a custom RRULE string).

#     Returns:
#         str: A message indicating success or failure of the event creation, including the event ID and link if successful.
#     """
#     import logging
#     import os
#     import sys
#     from typing import Optional
#     from dotenv import load_dotenv
#     import re

#     logger = logging.getLogger(__name__)
#     logger.setLevel(logging.DEBUG)

#     try:
#         load_dotenv()
#         MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
#         CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
#         if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
#             return "Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"

#         logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
#         logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

#         if MEMGPT_TOOLS_PATH not in sys.path:
#             sys.path.append(MEMGPT_TOOLS_PATH)

#         GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
#         GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

#         # comment out for unittesting only
#         from google_utils import GoogleCalendarUtils

#         calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

#         calendar_id = calendar_utils.get_or_create_user_calendar(user_id)
#         if not calendar_id:
#             return "Error: Unable to get or create user calendar"

#         event_data = {
#             'summary': title,
#             'location': location,
#             'description': description,
#             'start': {'dateTime': start, 'timeZone': 'America/Los_Angeles'},
#             'end': {'dateTime': end, 'timeZone': 'America/Los_Angeles'},
#         }

#         if reminders:
#             reminder_minutes = [int(m.strip()) for m in reminders.split(',')]
#             event_data['reminders'] = {
#                 'useDefault': False,
#                 'overrides': [{'method': 'popup', 'minutes': minutes} for minutes in reminder_minutes]
#             }

#         if recurrence:
#             if recurrence.lower() in ['daily', 'weekly', 'monthly', 'yearly']:
#                 recurrence = f"RRULE:FREQ={recurrence.upper()}"
#             elif not recurrence.startswith("RRULE:"):
#                 recurrence = "RRULE:" + recurrence
#             event_data['recurrence'] = [recurrence]

#         result = calendar_utils.create_calendar_event(calendar_id, event_data)

#         if isinstance(result, dict):
#             return f"Event created: ID: {result['id']}, Link: {result.get('htmlLink')}"
#         elif isinstance(result, str):
#             # Attempt to extract event ID from the link
#             match = re.search(r"eid=([^&]+)", result)
#             event_id = match.group(1) if match else "Unknown"
#             return f"Event created: ID: {event_id}, Link: {result}"
#         else:
#             return "Error: Failed to create event"

#     except Exception as e:
#         logger.error(f"Error in schedule_event: {str(e)}", exc_info=True)
#         return f"Error scheduling event: {str(e)}"
    
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
    Schedule a new event in the user's Google Calendar.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        title (str): The title of the event.
        start (str): The start time in ISO 8601 format.
        end (str): The end time in ISO 8601 format.
        description (Optional[str]): The description of the event.
        location (Optional[str]): The location of the event.
        reminders (Optional[str]): Reminders as a comma-separated string of minutes.
        recurrence (Optional[str]): Recurrence rule in RRULE format (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,TU").

    Returns:
        str: A message indicating success or failure of the event creation.

    Examples:
        1. Schedule a one-time event:
            schedule_event(
                self,
                user_id='user123',
                title='Doctor Appointment',
                start='2024-08-01T10:00:00',
                end='2024-08-01T11:00:00',
                description='Annual check-up',
                location='123 Clinic Street',
                reminders='30,10'
            )

        2. Schedule a weekly recurring event on Mondays and Tuesdays:
            schedule_event(
                self,
                user_id='user123',
                title='Morning Jog',
                start='2024-08-01T07:00:00',
                end='2024-08-01T08:00:00',
                description='Time for a refreshing jog!',
                location='The park',
                reminders='30,10',
                recurrence='RRULE:FREQ=WEEKLY;BYDAY=MO,TU'
            )
    """
    import logging
    import os
    import sys
    from typing import Optional
    from dotenv import load_dotenv
    import re

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    def is_valid_rrule(rrule: str) -> bool:
        valid_frequencies = {'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'}
        return rrule.startswith('RRULE:') and any(freq in rrule for freq in valid_frequencies)

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
            if not is_valid_rrule(recurrence):
                return "Error: Recurrence rule must be in RRULE format (e.g., 'RRULE:FREQ=WEEKLY;BYDAY=MO,TU')."
            event_data['recurrence'] = [recurrence]

        calendar_id = calendar_utils.get_or_create_user_calendar(user_id)
        if not calendar_id:
            return "Error: Unable to get or create user calendar"

        result = calendar_utils.create_calendar_event(calendar_id, event_data)

        if isinstance(result, dict):
            return f"Event created: ID: {result['id']}, Link: {result.get('htmlLink')}"
        elif isinstance(result, str):
            return f"Event created: ID: {result}"
        else:
            return "Error: Failed to create event"

    except Exception as e:
        logger.error(f"Error in schedule_event: {str(e)}", exc_info=True)
        return f"Error scheduling event: {str(e)}"


# def fetch_events(
#     self: Agent,
#     user_id: str,
#     max_results: int = 10,
#     time_min: Optional[str] = None
# ) -> str:
#     """
#     Fetch upcoming events from the user's Google Calendar.

#     Args:
#         self (Agent): The agent instance calling the tool.
#         user_id (str): The unique identifier for the user.
#         max_results (int): The maximum number of events to return. Default is 10.
#         time_min (Optional[str]): The start time (in ISO 8601 format) from which to fetch events.
#                                   If not provided, it defaults to the current time.

#     Returns:
#         str: A formatted string containing the list of upcoming events or an error message.
#     """
#     import logging
#     import os
#     import sys
#     from dotenv import load_dotenv

#     logger = logging.getLogger(__name__)
#     logger.setLevel(logging.DEBUG)

#     try:
#         load_dotenv()
#         MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
#         CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
#         if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
#             return "Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"

#         logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
#         logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

#         if MEMGPT_TOOLS_PATH not in sys.path:
#             sys.path.append(MEMGPT_TOOLS_PATH)

#         GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
#         GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

#         # Comment out for unit testing only
#         from google_utils import GoogleCalendarUtils

#         calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

#         events = calendar_utils.fetch_upcoming_events(user_id, max_results, time_min)

#         if not events:
#             return "No upcoming events found."

#         formatted_output = "Upcoming events:\n\n"
#         for event in events:
#             formatted_output += f"Title: {event['summary']}\n"
#             formatted_output += f"Start: {event['start']}\n"
#             formatted_output += f"End: {event['end']}\n"
#             formatted_output += f"Description: {event.get('description', 'No description')}\n"
#             formatted_output += f"Location: {event.get('location', 'No location')}\n"
#             formatted_output += f"Event ID: {event['id']}\n"
#             if 'recurrence' in event:
#                 formatted_output += f"Recurrence: {event['recurrence'][0]}\n"
#                 formatted_output += "This is a recurring event. Use the series ID to modify or delete the entire series.\n"
#             formatted_output += f"Event Link: {event.get('htmlLink')}\n\n"

#         return formatted_output

#     except Exception as e:
#         logger.error(f"Error in fetch_events: {str(e)}", exc_info=True)
#         return f"Error fetching events: {str(e)}"

def fetch_events(
    self: Agent,
    user_id: str,
    max_results: int = 10,
    page_token: Optional[str] = None,
    time_min: Optional[str] = None
) -> dict:
    """
    Fetch upcoming events from the user's Google Calendar with optional pagination.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        max_results (int): The maximum number of events to return.
        page_token (Optional[str]): Token for pagination.
        time_min (Optional[str]): The minimum time to filter events.

    Returns:
        dict: A dictionary containing the events and pagination tokens.
    """
    import os
    import sys
    import logging
    from dotenv import load_dotenv

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    try:
        load_dotenv()
        MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
        CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
        if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
            return {"success": False, "message": "MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"}

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        from google_utils import GoogleCalendarUtils

        calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

        events_data = calendar_utils.fetch_upcoming_events(user_id, max_results, time_min, page_token)

        if not events_data.get('items', []):
            return {"success": False, "message": "No upcoming events found."}

        event_list = []
        for event in events_data['items']:
            event_summary = {
                'title': event['summary'],
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'id': event['id']
            }
            event_list.append(event_summary)

        return {
            "success": True,
            "events": event_list,
            "nextPageToken": events_data.get('nextPageToken'),
            "prevPageToken": events_data.get('prevPageToken')
        }

    except Exception as e:
        logger.error(f"Error in fetch_events: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error fetching events: {str(e)}"}
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
) -> dict:
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
        recurrence (Optional[str]): New recurrence rule in RRULE format (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,TU"). If None, recurrence remains unchanged.
        update_series (bool): If True, update the entire event series if the event is part of a recurring series.

    Returns:
        str: A message indicating success or failure of the event update.

    Examples:
        1. Update the title and description of a one-time event:
            update_event(
                self,
                user_id='user123',
                event_id='event123',
                title='Doctor Appointment - Updated',
                description='Annual check-up with Dr. Smith.'
            )

        2. Update the time of a recurring event:
            update_event(
                self,
                user_id='user123',
                event_id='event123',
                start='2024-08-01T07:30:00',
                end='2024-08-01T08:30:00',
                update_series=True
            )

        3. Add a recurrence rule to an existing event:
            update_event(
                self,
                user_id='user123',
                event_id='event123',
                recurrence='RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR'
            )

        4. Add a day to an existing recurrence rule:
            update_event(
                self,
                user_id='user123',
                event_id='event123',
                recurrence='RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR,SU'
            )

        5. Change a recurrence rule to a specific day and time:
            update_event(
                self,
                user_id='user123',
                event_id='event123',
                start='2024-08-02T07:00:00',
                end='2024-08-02T08:00:00',
                recurrence='RRULE:FREQ=WEEKLY;BYDAY=FR'
            )
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
            return {"success": False, "message": "MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"}

        logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
        logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        # Temporarily disable for unit tests
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
            event_data['recurrence'] = [recurrence]

        result = calendar_utils.update_calendar_event(user_id, event_id, event_data, update_series)

        if result.get("success", False):
            return {"success": True, "event_id": result['event']['id'], "message": "Event updated successfully"}
        else:
            return {"success": False, "message": result.get('message', 'Unknown error')}

    except Exception as e:
        logger.error(f"Error in update_event: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error updating event: {str(e)}"}

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


