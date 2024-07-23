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

        event_data = utils.create_calendar_event(title, start, end, description)

        if not event_data:
            return "Error: Failed to create event"

        return f"Event created: Event ID: {event_data['event_id']}, Link: {event_data['htmlLink']}"

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
            formatted_output += f"Event ID: {event['event_id']}\n"
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

def update_event(
    self: Agent,
    user_id: str,
    event_id: str,
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Update an existing event on a user's Google Calendar.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The user ID associated with the calendar.
        event_id (str): The unique event identifier.
        title (Optional[str]): New event name (if provided).
        start (Optional[str]): New start time in ISO 8601 format.
        end (Optional[str]): New end time in ISO 8601 format.
        description (Optional[str]): New expanded description of the event.

    Returns:
        str: Status of the event update request.
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

        if not utils.calendar_id:
            return "Error: Unable to get or create user calendar"

        updated_event = utils.update_calendar_event(event_id, title, start, end, description)

        if not updated_event:
            return "Error: Failed to update event"

        return f"Event updated: {updated_event}"

    except Exception as e:
        logger.error(f"Error in update_event: {str(e)}", exc_info=True)
        return f"Error updating event: {str(e)}"

def delete_event(
    self: Agent,
    user_id: str,
    event_id: str
) -> str:
    """
    Delete an event from a user's Google Calendar.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The user ID associated with the calendar.
        event_id (str): The unique event identifier.

    Returns:
        str: Status of the event deletion request.
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

        if not utils.calendar_id:
            return "Error: Unable to get or create user calendar"

        result = utils.delete_calendar_event(event_id)

        if not result:
            return "Error: Failed to delete event"

        return "Event successfully deleted."

    except Exception as e:
        logger.error(f"Error in delete_event: {str(e)}", exc_info=True)
        return f"Error deleting event: {str(e)}"

def send_email(
    self: Agent,
    user_id: str,
    subject: str,
    body: str,
    message_id: Optional[str] = None
) -> str:
    """
    Send an email message via the Gmail API using a MemGPT user ID.

    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The MemGPT user ID stored in the database.
        subject (str): The subject of the email.
        body (str): The email message content to send.
        message_id (Optional[str]): The original message ID for referencing the original email thread.

    Returns:
        str: The status message indicating success or failure.
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

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        from google_utils import GoogleUtils
        from ella_dbo.db_manager import create_connection, get_user_data_by_field, close_connection

        SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.modify"]
        GMAIL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gmail_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        if not os.path.exists(GMAIL_TOKEN_PATH) or not os.path.exists(GOOGLE_CREDENTIALS_PATH):
            return f"Error: Token or credentials file not found. GMAIL_TOKEN_PATH: {GMAIL_TOKEN_PATH}, GOOGLE_CREDENTIALS_PATH: {GOOGLE_CREDENTIALS_PATH}"

        conn = create_connection()
        try:
            user_data = get_user_data_by_field(conn, "memgpt_user_id", user_id)
            recipient_email = user_data.get('email')
            if not recipient_email:
                return "Error: No valid recipient email address available."

            utils = GoogleUtils(user_id, GMAIL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH, SCOPES)
            
            if not utils.gmail_service:
                return "Error: Failed to authenticate Gmail service"

            result = utils.send_email(recipient_email, subject, body, message_id)

            if result['status'] == 'success':
                return f"Message was successfully sent. Message ID: {result['message_id']}"
            else:
                return f"Message failed to send with error: {result['message']}"

        finally:
            close_connection(conn)

    except Exception as e:
        logger.error(f"Error in send_email: {str(e)}", exc_info=True)
        return f"Error sending email: {str(e)}"

# Update the CUSTOM_TOOLS list
CUSTOM_TOOLS = [schedule_event, fetch_events, update_event, delete_event, send_email]



