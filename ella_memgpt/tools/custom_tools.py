# memgpt_tools/custom_tools.py

from memgpt.agent import Agent
from typing import Optional

def schedule_event(
    self: Agent,
    user_id: str,
    title: str,
    start: str,
    end: str,
    description: Optional[str] = None
) -> str:
    """
    Schedule an event and grant calendar access to a user.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The user ID used to retrieve the email for sharing.
        title (str): Event name.
        start (str): Event start time in ISO 8601 format.
        end (str): Event end time in ISO 8601 format.
        description (Optional[str]): Description of the event.

    Returns:
        str: Status of the event scheduling request.
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
            return "Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"

        logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
        logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        from google_utils import GoogleUtils

        SCOPES = ["https://www.googleapis.com/auth/calendar"]
        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        if not os.path.exists(GCAL_TOKEN_PATH) or not os.path.exists(GOOGLE_CREDENTIALS_PATH):
            return f"Error: Token or credentials file not found. GCAL_TOKEN_PATH: {GCAL_TOKEN_PATH}, GOOGLE_CREDENTIALS_PATH: {GOOGLE_CREDENTIALS_PATH}"

        utils = GoogleUtils(user_id, GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH, SCOPES)
        
        if not utils.service:
            return "Error: Failed to authenticate Google service"

        if not utils.user_email:
            return "Error: Unable to retrieve user email"

        if not utils.calendar_id:
            return "Error: Unable to get or create user calendar"

        utils.set_calendar_permissions()
        event_link = utils.create_calendar_event(title, start, end, description)

        if not event_link:
            return "Error: Failed to create event"

        return f"Event created: {event_link}"

    except Exception as e:
        logger.error(f"Error in schedule_event: {str(e)}", exc_info=True)
        return f"Error scheduling event: {str(e)}"
    
def fetch_events(
    self: Agent,
    user_id: str,
    max_results: int = 100,
    time_min: Optional[str] = None
) -> str:
    """
    Fetch upcoming events from a user's Google Calendar.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The user ID used to retrieve the calendar.
        max_results (int): Maximum number of events to retrieve. Default is 100.
        time_min (Optional[str]): Minimum time filter for events in ISO 8601 format.

    Returns:
        str: A formatted string containing event details or an error message.
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
            return "Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"

        logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
        logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        from google_utils import GoogleUtils

        SCOPES = ["https://www.googleapis.com/auth/calendar"]
        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        if not os.path.exists(GCAL_TOKEN_PATH) or not os.path.exists(GOOGLE_CREDENTIALS_PATH):
            return f"Error: Token or credentials file not found. GCAL_TOKEN_PATH: {GCAL_TOKEN_PATH}, GOOGLE_CREDENTIALS_PATH: {GOOGLE_CREDENTIALS_PATH}"

        utils = GoogleUtils(user_id, GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH, SCOPES)
        
        if not utils.service:
            return "Error: Failed to authenticate Google service"

        if not utils.user_email:
            return "Error: Unable to retrieve user email"

        if not utils.calendar_id:
            return "Error: Unable to get or create user calendar"

        events = utils.fetch_upcoming_events(max_results, time_min)

        if not events:
            return "No upcoming events found."

        formatted_output = "Upcoming events:\n\n"
        for event in events:
            formatted_output += f"Title: {event['summary']}\n"
            formatted_output += f"Start: {event['start']}\n"
            formatted_output += f"End: {event['end']}\n"
            formatted_output += f"Description: {event['description']}\n"
            formatted_output += f"Location: {event['location']}\n"
            if event['attendees']:
                formatted_output += f"Attendees: {', '.join(event['attendees'])}\n"
            formatted_output += "\n"

        return formatted_output

    except Exception as e:
        logger.error(f"Error in fetch_events: {str(e)}", exc_info=True)
        return f"Error fetching events: {str(e)}"

# Update the CUSTOM_TOOLS list
CUSTOM_TOOLS = [schedule_event, fetch_events]

