# custom_tools.py

from memgpt.agent import Agent
from typing import Any, Optional
import logging
import os
import sys
from typing import Optional, List, Dict, Union
from dotenv import load_dotenv
from enum import Enum
import aiosqlite  # Add this import

def schedule_event(
    self: 'Agent',
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
    Schedule a new event in the user's Google Calendar with unified reminder support.
    Version: 1.0.2
    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        title (str): The title of the event.
        start (str): The start time in ISO 8601 format.
        end (str): The end time in ISO 8601 format.
        description (Optional[str]): The description of the event.
        location (Optional[str]): The location of the event.
        reminders (Optional[str]): JSON string representation of reminders.
            Format: '[{"type": "email", "minutes": 30}, {"type": "popup", "minutes": 10}, {"type": "voice", "minutes": 60}]'
            Supported reminder types: 'email', 'popup', 'sms', 'voice', 'app', etc.
        recurrence (Optional[str]): Recurrence rule in RRULE format (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,TU").
        local_timezone (Optional[str]): The timezone for the event. If None, the user's default timezone will be used.

    Returns:
        str: A JSON string indicating success or failure of the event creation.
    """
    import os
    import sys
    import json
    from typing import Optional
    import requests
    from dotenv import load_dotenv

 
    # Load environment variables
    load_dotenv()

    # Add project root and ella_dbo directory to sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    ella_dbo_dir = os.getenv('DB_PATH')

    sys.path.extend([project_root, ella_dbo_dir])

    # Import models
    from models import Event, ScheduleEventRequest

    # Check if required environment variables are set
    API_BASE_URL = os.getenv('SERVICES_API_URL')
    API_KEY = os.getenv('API_KEY')

    if not API_BASE_URL or not API_KEY or not ella_dbo_dir:
        return json.dumps({"success": False, "message": "SERVICES_API_URL, API_KEY, or DB_PATH not set in environment variables"})

    endpoint = f"{API_BASE_URL}/schedule_event"

    # Parse reminders and format them correctly
    if reminders:
        reminders_list = json.loads(reminders)
        reminders_dict = {
            "useDefault": False,
            "overrides": [
                {"method": reminder["type"], "minutes": reminder["minutes"]}
                for reminder in reminders_list
            ]
        }
    else:
        reminders_dict = None

    # Create an Event object
    event_data = Event(
        summary=title,
        start={"dateTime": start, "timeZone": local_timezone},
        end={"dateTime": end, "timeZone": local_timezone},
        description=description,
        location=location,
        reminders=reminders_dict,
        recurrence=[recurrence] if recurrence else None,
        local_timezone=local_timezone
    )

    # Create a ScheduleEventRequest object
    request_data = ScheduleEventRequest(user_id=user_id, event=event_data)

    # Prepare headers with API key
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(endpoint, json=request_data.model_dump(), headers=headers)
        response.raise_for_status()
        response_json = response.json()
        return json.dumps(response_json)
    except requests.RequestException as e:
        error_message = f"Error scheduling event: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_message += f"\nResponse status code: {e.response.status_code}"
            error_message += f"\nResponse content: {e.response.text}"
        return json.dumps({"success": False, "message": error_message})
    except json.JSONDecodeError:
        return json.dumps({"success": False, "message": "Invalid JSON response from server"})

def update_event(
    self: 'Agent',
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
    Version: 1.0.3
    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        event_id (str): The unique identifier for the event to be updated.
        title (Optional[str]): The new title for the event.
        start (Optional[str]): The new start time in ISO 8601 format.
        end (Optional[str]): The new end time in ISO 8601 format.
        description (Optional[str]): The new description for the event.
        location (Optional[str]): The new location for the event.
        reminders (Optional[str]): JSON string representation of new reminders.
        recurrence (Optional[str]): New recurrence rule in RRULE format.
        update_series (bool): If True, update the entire event series if the event is part of a recurring series.
        local_timezone (Optional[str]): The timezone for the event.

    Returns:
        str: A JSON string containing the API response.
    """
    import os
    import json
    import requests
    from dotenv import load_dotenv

 
    load_dotenv()

    API_BASE_URL = os.getenv('SERVICES_API_URL')
    API_KEY = os.getenv('API_KEY')

    if not API_BASE_URL or not API_KEY:
        return json.dumps({"success": False, "message": "SERVICES_API_URL or API_KEY not set in environment variables"})

    endpoint = f"{API_BASE_URL}/events/{event_id}"

    update_data = {
        "user_id": user_id,
        "event": {},
        "update_series": update_series
    }

    # Only include non-None values in the update data
    if title is not None:
        update_data["event"]["summary"] = title
    if start is not None:
        update_data["event"]["start"] = {"dateTime": start, "timeZone": local_timezone or "UTC"}
    if end is not None:
        update_data["event"]["end"] = {"dateTime": end, "timeZone": local_timezone or "UTC"}
    if description is not None:
        update_data["event"]["description"] = description
    if location is not None:
        update_data["event"]["location"] = location
    if reminders is not None:
        update_data["event"]["reminders"] = json.loads(reminders)
    if recurrence is not None:
        update_data["event"]["recurrence"] = [recurrence] if recurrence else None

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.put(endpoint, json=update_data, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        error_message = f"Error updating event: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_message += f"\nResponse status code: {e.response.status_code}"
            error_message += f"\nResponse content: {e.response.text}"
        return json.dumps({"success": False, "message": error_message})

def fetch_events(    
    self: 'Agent',
    user_id: str,
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    local_timezone: Optional[str] = None
) -> str:
    """
    Fetch upcoming events from the user's Google Calendar within the specified time range.
    Version: 1.0.2
    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        max_results (int): The maximum number of events to return. Default is 10.
        time_min (Optional[str]): The minimum time to filter events in ISO 8601 format.
            Example: "2024-01-01T00:00:00Z" to fetch events starting from January 1, 2024.
        time_max (Optional[str]): The maximum time to filter events in ISO 8601 format.
            Example: "2024-01-14T23:59:59Z" to fetch events up to January 14, 2024.
        local_timezone (Optional[str]): The timezone for the events. If None, the user's default timezone will be used.

    Returns:
        str: A JSON string describing the fetched events, including standard and custom reminders.
    """
    import os
    import sys
    import json
    from typing import Optional
    import requests
    from dotenv import load_dotenv

 
    # Load environment variables
    load_dotenv()

    # Add project root and ella_dbo directory to sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    ella_dbo_dir = os.getenv('DB_PATH')

    sys.path.extend([project_root, ella_dbo_dir])

    # Check if required environment variables are set
    API_BASE_URL = os.getenv('SERVICES_API_URL')
    API_KEY = os.getenv('API_KEY')

    if not API_BASE_URL or not API_KEY or not ella_dbo_dir:
        return json.dumps({"success": False, "message": "SERVICES_API_URL, API_KEY, or DB_PATH not set in environment variables"})

    endpoint = f"{API_BASE_URL}/events"

    # Prepare headers with API key
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    # Prepare query parameters
    params = {
        "user_id": user_id,
        "max_results": max_results,
        "time_min": time_min,
        "time_max": time_max,
        "local_timezone": local_timezone
    }

    # Remove None values from the params
    params = {k: v for k, v in params.items() if v is not None}

    try:
        response = requests.get(endpoint, params=params, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        error_message = f"Error fetching events: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_message += f"\nResponse status code: {e.response.status_code}"
            error_message += f"\nResponse content: {e.response.text}"
        return json.dumps({"success": False, "message": error_message})
    except json.JSONDecodeError:
        return json.dumps({"success": False, "message": "Invalid JSON response from server"})
    
def delete_event(
    self: 'Agent',
    user_id: str,
    event_id: str,
    delete_series: bool = False
) -> str:
    """
    Delete an event from the user's Google Calendar.
    Version: 1.0.2
    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier for the user.
        event_id (str): The unique identifier for the event to be deleted.
        delete_series (bool): If True, attempts to delete all instances of a recurring event series.
                              If False, deletes only the specified instance of a recurring event.
                              Defaults to False.

    Returns:
        str: A JSON string indicating success or failure of the event deletion.
    """
    import os
    import sys
    import json
    import requests
    from dotenv import load_dotenv

 
    # Load environment variables
    load_dotenv()

    # Add project root and ella_dbo directory to sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    ella_dbo_dir = os.getenv('DB_PATH')

    sys.path.extend([project_root, ella_dbo_dir])

    # Check if required environment variables are set
    API_BASE_URL = os.getenv('SERVICES_API_URL')
    API_KEY = os.getenv('API_KEY')

    if not API_BASE_URL or not API_KEY or not ella_dbo_dir:
        return json.dumps({"success": False, "message": "SERVICES_API_URL, API_KEY, or DB_PATH not set in environment variables"})

    endpoint = f"{API_BASE_URL}/events/{event_id}"

    # Prepare headers with API key
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    # Prepare query parameters
    params = {
        "user_id": user_id,
        "delete_series": delete_series
    }

    try:
        response = requests.delete(endpoint, params=params, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        error_message = f"Error deleting event: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_message += f"\nResponse status code: {e.response.status_code}"
            error_message += f"\nResponse content: {e.response.text}"
        return json.dumps({"success": False, "message": error_message})
    except json.JSONDecodeError:
        return json.dumps({"success": False, "message": "Invalid JSON response from server"})

# def send_sms(
#     self: Agent,
#     user_id: str,
#     body: str,
#     message_id: Optional[str] = None
# ) -> str:
#     """
#     Send an SMS message via Twilio using a MemGPT user ID.
#     Version: 0.9
    
#     This function retrieves the user's phone number from the database using the provided MemGPT user ID.
#     If successful, an SMS message is sent using the Twilio API.
    
#     Args:
#         self (Agent): The agent instance calling the tool.
#         user_id (str): The unique identifier for the user (recipient).
#         body (str): The content of the SMS message.
#         message_id (Optional[str]): An optional message ID for reference (not used in SMS, but included for consistency).
        
#     Returns:
#         str: A status message indicating success or failure.
#     """
#     import logging
#     import os
#     import sys
#     from dotenv import load_dotenv
#     from typing import Optional
 

#     logger = logging.getLogger(__name__)
#     logger.setLevel(logging.DEBUG)

#     try:
#         load_dotenv()
#         MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
#         CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
#         account_sid = os.getenv("TWILIO_ACCOUNT_SID")
#         auth_token = os.getenv("TWILIO_AUTH_TOKEN")
#         from_number = os.getenv("TWILIO_FROM_NUMBER")

#         if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
#             return "Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"
        
#         logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
#         logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")
        
#         if MEMGPT_TOOLS_PATH not in sys.path:
#             sys.path.append(MEMGPT_TOOLS_PATH)
        
#         # Now that the path is set up, we can import UserDataManager
#         from google_utils import UserDataManager
#         # Initialize Twilio client
#         from twilio.rest import Client
        
#         if not account_sid or not auth_token or not from_number:
#             return "Error: Twilio credentials not set in environment variables"
        
#         client = Client(account_sid, auth_token)
        
#         # Retrieve recipient's phone number
#         recipient_phone = UserDataManager.get_user_phone(user_id)
#         if not recipient_phone:
#             return "Error: No valid recipient phone number available."
        
#         message_status = client.messages.create(
#             body=body,
#             from_=from_number,
#             to=recipient_phone
#         )
#         logger.info(f"Message sent to {recipient_phone}: {message_status.sid}")
#         return "Message was successfully sent."
#     except Exception as e:
#         logger.error(f"Message failed to send with error: {str(e)}", exc_info=True)
#         return f"Error: Message failed to send. {str(e)}"

# def send_voice(
#     self: Agent,
#     user_id: str,
#     body: str,
# ) -> str:
#     """
#     Send a voice call reminder using the VAPI API.
    
#     This function retrieves the user's phone number and assistant ID from the database using the provided MemGPT user ID.
#     If successful, a voice call is initiated using the VAPI API.
    
#     Args:
#         self (Agent): The agent instance calling the tool.
#         user_id (str): The unique identifier for the user (recipient).
#         body (str): The content of the voice message to be spoken.
        
#     Returns:
#         str: A status message indicating success or failure of the voice call initiation.
#     """
#     import logging
#     import os
#     import sys
#     from dotenv import load_dotenv
#     from typing import Optional
#     import asyncio

#     logger = logging.getLogger(__name__)
#     logger.setLevel(logging.DEBUG)

#     try:
#         load_dotenv()
#         MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
#         VAPI_TOOLS_PATH = os.getenv('VAPI_TOOLS_PATH')
#         CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')

#         if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH or not VAPI_TOOLS_PATH:
#             return "Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH or VAPI_TOOLS_PATH not set in environment variables"
        
#         logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
#         logger.debug(f"VAPI_TOOLS_PATH: {VAPI_TOOLS_PATH}")
#         logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")
        
#         if MEMGPT_TOOLS_PATH not in sys.path:
#             sys.path.append(MEMGPT_TOOLS_PATH)
#         if VAPI_TOOLS_PATH not in sys.path:
#             sys.path.append(VAPI_TOOLS_PATH)
        
#         # Import UserDataManager and VAPIClient
#         from google_utils import UserDataManager
#         from vapi_client import VAPIClient
        
#         # Retrieve all user data at once
#         user_data = UserDataManager.get_user_data(user_id)

#         # Extract specific fields from the user data dictionary
#         recipient_phone = user_data.get('phone')
#         if not recipient_phone:
#             return "Error: No valid recipient phone number available."
        
#         # Extract assistant ID, fallback to environment variable if not found
#         assistant_id = user_data.get('vapi_assistant_id')
#         if not assistant_id:
#             assistant_id = os.getenv('VAPI_DEFAULT_ASSISTANT_ID')
#             logging.warning(f"No assistant ID found for user {user_id}. Using default: {assistant_id}")
#         else:
#             logging.info(f"Found assistant ID for user {user_id}: {assistant_id}")
            
#         # Initialize VAPI client
#         client = VAPIClient()
        
#         # Prepare call details
#         assistant_overrides = {
#             "firstMessage": body,
#             "recordingEnabled": True,
#             "maxDurationSeconds": 600,  # 10 minutes max call duration
#             "endCallPhrases": ["end the call", "goodbye", "hang up"]
#         }
        
#         # Initiate the call
#         async def make_call():
#             result = await client.start_call(
#                 name="Assistant Outbound Call",
#                 assistant_id=assistant_id,
#                 customer_number=recipient_phone,
#                 assistant_overrides=assistant_overrides
#             )
#             #await client.close()
#             return result
        
#         call_result = asyncio.run(make_call())
        
#         if 'id' in call_result:
#             logger.info(f"Voice call successfully initiated. Call ID: {call_result['id']}")
#             return f"Voice call successfully initiated. Call ID: {call_result['id']}"
#         else:
#             logger.error(f"Failed to initiate voice call: {call_result}")
#             return f"Error: Voice call failed to initiate. Details: {call_result}"
    
#     except Exception as e:
#         logger.error(f"Error in send_voice: {str(e)}", exc_info=True)
#         return f"Error initiating voice call: {str(e)}"

def send_email(
    self: 'Agent',
    user_id: str,
    subject: str,
    body: str,
    message_id: Optional[str] = None
) -> str:
    """
    Send an email using the email API endpoint.
    Version: 1.0.4
    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier of the user to whom the email will be sent.
        subject (str): The subject line of the email.
        body (str): The main content of the email.
        message_id (Optional[str]): An optional message ID for threading replies.

    Returns:
        str: A message indicating success or failure of the email sending process.
    """
    # Import necessary modules
    import logging
    import requests
    import os
    from dotenv import load_dotenv
    from urllib.parse import urljoin

    # Load environment variables
    load_dotenv()

    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info(f"Attempting to send email for user: {user_id}")
    
    # Get base API URL from environment variable
    base_url = os.getenv('SERVICES_API_URL')
    if not base_url:
        logger.error("SERVICES_API_URL environment variable is not set")
        return "Error: SERVICES_API_URL is not configured"
    
    # Construct the full API endpoint URL
    api_endpoint = urljoin(base_url, '/send_email')
    
    payload = {
        "user_id": user_id,
        "subject": subject,
        "body": body,
        "message_id": message_id
    }
    
    try:
        response = requests.post(api_endpoint, json=payload)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        
        result = response.json()
        
        if result.get('success', False):
            logger.info(f"Email sent successfully. Message ID: {result.get('message_id')}")
            return f"Message was successfully sent. Message ID: {result.get('message_id')}"
        else:
            logger.error(f"Failed to send email: {result.get('message', 'Unknown error')}")
            return f"Message failed to send with error: {result.get('message', 'Unknown error')}"
    
    except requests.RequestException as e:
        logger.error(f"Error sending email via API: {str(e)}", exc_info=True)
        return f"Error sending email: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in send_email: {str(e)}", exc_info=True)
        return f"Unexpected error sending email: {str(e)}"


def send_sms(
    self: 'Agent',
    user_id: str,
    subject: str,
    body: str,
    message_id: Optional[str] = None
) -> str:
    """
    Send an email using the email API endpoint. This is a test to overwrit the bad sms function.
    Version: 1.0.6
    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier of the user to whom the email will be sent.
        subject (str): The subject line of the email.
        body (str): The main content of the email.
        message_id (Optional[str]): An optional message ID for threading replies.

    Returns:
        str: A message indicating success or failure of the email sending process.
    """
    # Import necessary modules
    import logging
    import requests
    import os
    from dotenv import load_dotenv
    from urllib.parse import urljoin

    # Load environment variables
    load_dotenv()

    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info(f"Attempting to send email for user: {user_id}")
    
    # Get base API URL from environment variable
    base_url = os.getenv('SERVICES_API_URL')
    if not base_url:
        logger.error("SERVICES_API_URL environment variable is not set")
        return "Error: SERVICES_API_URL is not configured"
    
    # Construct the full API endpoint URL
    api_endpoint = urljoin(base_url, '/send_email')
    
    payload = {
        "user_id": user_id,
        "subject": subject,
        "body": body,
        "message_id": message_id
    }
    
    try:
        response = requests.post(api_endpoint, json=payload)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        
        result = response.json()
        
        if result.get('success', False):
            logger.info(f"Email sent successfully. Message ID: {result.get('message_id')}")
            return f"Message was successfully sent. Message ID: {result.get('message_id')}"
        else:
            logger.error(f"Failed to send email: {result.get('message', 'Unknown error')}")
            return f"Message failed to send with error: {result.get('message', 'Unknown error')}"
    
    except requests.RequestException as e:
        logger.error(f"Error sending email via API: {str(e)}", exc_info=True)
        return f"Error sending email: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in send_email: {str(e)}", exc_info=True)
        return f"Unexpected error sending email: {str(e)}"

def send_voice(
    self: 'Agent',
    user_id: str,
    subject: str,
    body: str,
    message_id: Optional[str] = None
) -> str:
    """
    Send an email using the email API endpoint. This is a test to overwrite the bad voice function.
    Version: 1.0.6
    Args:
        self (Agent): The agent instance calling the tool.
        user_id (str): The unique identifier of the user to whom the email will be sent.
        subject (str): The subject line of the email.
        body (str): The main content of the email.
        message_id (Optional[str]): An optional message ID for threading replies.

    Returns:
        str: A message indicating success or failure of the email sending process.
    """
    # Import necessary modules
    import logging
    import requests
    import os
    from dotenv import load_dotenv
    from urllib.parse import urljoin

    # Load environment variables
    load_dotenv()

    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info(f"Attempting to send email for user: {user_id}")
    
    # Get base API URL from environment variable
    base_url = os.getenv('SERVICES_API_URL')
    if not base_url:
        logger.error("SERVICES_API_URL environment variable is not set")
        return "Error: SERVICES_API_URL is not configured"
    
    # Construct the full API endpoint URL
    api_endpoint = urljoin(base_url, '/send_email')
    
    payload = {
        "user_id": user_id,
        "subject": subject,
        "body": body,
        "message_id": message_id
    }
    
    try:
        response = requests.post(api_endpoint, json=payload)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        
        result = response.json()
        
        if result.get('success', False):
            logger.info(f"Email sent successfully. Message ID: {result.get('message_id')}")
            return f"Message was successfully sent. Message ID: {result.get('message_id')}"
        else:
            logger.error(f"Failed to send email: {result.get('message', 'Unknown error')}")
            return f"Message failed to send with error: {result.get('message', 'Unknown error')}"
    
    except requests.RequestException as e:
        logger.error(f"Error sending email via API: {str(e)}", exc_info=True)
        return f"Error sending email: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in send_email: {str(e)}", exc_info=True)
        return f"Unexpected error sending email: {str(e)}"


# List of all custom tools
# CUSTOM_TOOLS = [schedule_event, update_event, fetch_events, delete_event, send_email]
CUSTOM_TOOLS = [schedule_event, fetch_events, delete_event, update_event, send_email, send_sms, send_voice]



# def schedule_event(
#     self: 'Agent',
#     user_id: str,
#     title: str,
#     start: str,
#     end: str,
#     description: Optional[str] = None,
#     location: Optional[str] = None,
#     reminders: Optional[str] = None,
#     recurrence: Optional[str] = None,
#     local_timezone: Optional[str] = None
# ) -> str:
#     """
#     Schedule a new event in the user's Google Calendar with unified reminder support.

#     Args:
#         self (Agent): The agent instance calling the tool.
#         user_id (str): The unique identifier for the user.
#         title (str): The title of the event.
#         start (str): The start time in ISO 8601 format.
#         end (str): The end time in ISO 8601 format.
#         description (Optional[str]): The description of the event.
#         location (Optional[str]): The location of the event.
#         reminders (Optional[str]): JSON string representation of reminders.
#             Format: '[{"type": "email", "minutes": 30}, {"type": "popup", "minutes": 10}, {"type": "voice", "minutes": 60}]'
#             Supported reminder types: 'email', 'popup', 'sms', 'voice', 'app', etc.
#         recurrence (Optional[str]): Recurrence rule in RRULE format (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,TU").
#         local_timezone (Optional[str]): The timezone for the event. If None, the user's default timezone will be used.

#     Returns:
#         str: A JSON string indicating success or failure of the event creation.

#     Examples:
#         1. Schedule a one-time event with multiple reminder types:
#             schedule_event(
#                 self,
#                 user_id='user123',
#                 title='Doctor Appointment',
#                 start='2024-08-01T10:00:00',
#                 end='2024-08-01T11:00:00',
#                 description='Annual check-up',
#                 location='123 Clinic Street',
#                 reminders='[{"type": "email", "minutes": 30}, {"type": "popup", "minutes": 10}, {"type": "voice", "minutes": 60}]'
#             )

#         2. Schedule a weekly recurring event with default reminders:
#             schedule_event(
#                 self,
#                 user_id='user123',
#                 title='Morning Jog',
#                 start='2024-08-01T07:00:00',
#                 end='2024-08-01T08:00:00',
#                 description='Time for a refreshing jog!',
#                 location='The park',
#                 recurrence='RRULE:FREQ=WEEKLY;BYDAY=MO,TU',
#                 local_timezone='America/New_York'
#             )
#     """
#     import logging
#     import os
#     import sys
#     from typing import Optional, List, Dict, Union
#     from dotenv import load_dotenv
#     import json
#     from datetime import datetime, timedelta
#     import pytz

#     logger = logging.getLogger(__name__)
#     logger.setLevel(logging.DEBUG)

#     try:
#         load_dotenv()
#         MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
#         CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
#         if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
#             return json.dumps({"success": False, "message": "MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"})

#         if MEMGPT_TOOLS_PATH not in sys.path:
#             sys.path.append(MEMGPT_TOOLS_PATH)

#         GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
#         GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

#         from google_utils import GoogleCalendarUtils, UserDataManager, is_valid_timezone

#         calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

#         if not local_timezone:
#             local_timezone = UserDataManager.get_user_timezone(user_id)
#         elif not is_valid_timezone(local_timezone):
#             return json.dumps({"success": False, "message": f"Invalid timezone: {local_timezone}"})

#         # Check for conflicts
#         conflict_check = calendar_utils.check_conflicts(user_id, start, end, local_timezone=local_timezone)
#         if not conflict_check["success"]:
#             return json.dumps(conflict_check)  # Return conflict information

#         event_data = calendar_utils.prepare_event_data(
#             user_id, title, start, end, description, location, reminders, recurrence, local_timezone
#         )

#         result = calendar_utils.create_calendar_event(user_id, event_data, local_timezone)

#         if result.get("success", False):
#             return json.dumps({"success": True, "message": f"Event created: ID: {result.get('id', 'Unknown')}, Link: {result.get('htmlLink', 'No link available')}"})
#         else:
#             return json.dumps({"success": False, "message": result.get('message', 'Failed to create event')})

#     except Exception as e:
#         logger.error(f"Error in schedule_event: {str(e)}", exc_info=True)
#         return json.dumps({"success": False, "message": f"Error scheduling event: {str(e)}"})

# def update_event(
#     self: 'Agent',
#     user_id: str,
#     event_id: str,
#     title: Optional[str] = None,
#     start: Optional[str] = None,
#     end: Optional[str] = None,
#     description: Optional[str] = None,
#     location: Optional[str] = None,
#     reminders: Optional[str] = None,
#     recurrence: Optional[str] = None,
#     update_series: bool = False,
#     local_timezone: Optional[str] = None
# ) -> str:
#     """
#     Update an existing event in the user's Google Calendar with enhanced reminder support.

#     Args:
#         self (Agent): The agent instance calling the tool.
#         user_id (str): The unique identifier for the user.
#         event_id (str): The unique identifier for the event to be updated.
#         title (Optional[str]): The new title for the event. If None, the title remains unchanged.
#         start (Optional[str]): The new start time in ISO 8601 format. If None, the start time remains unchanged.
#         end (Optional[str]): The new end time in ISO 8601 format. If None, the end time remains unchanged.
#         description (Optional[str]): The new description for the event. If None, the description remains unchanged.
#         location (Optional[str]): The new location for the event. If None, the location remains unchanged.
#         reminders (Optional[str]): JSON string representation of new reminders.
#             Format: '[{"type": "email", "minutes": 30}, {"type": "popup", "minutes": 10}, {"type": "voice", "minutes": 60}]'
#             Supported reminder types: 'email', 'popup', 'sms', 'voice', 'app', etc.
#             If None, reminders remain unchanged. If an empty list '[]' is provided, all reminders will be removed.
#         recurrence (Optional[str]): New recurrence rule in RRULE format (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,TU"). 
#             If None, recurrence remains unchanged. If an empty string is provided, recurrence will be removed.
#         update_series (bool): If True, update the entire event series if the event is part of a recurring series.
#         local_timezone (Optional[str]): The new timezone for the event. If None, the timezone remains unchanged.

#     Returns:
#         str: A JSON string containing information about the success or failure of the event update.

#     Examples:
#         1. Update the title and add multiple types of reminders to an existing event:
#             update_event(
#                 self,
#                 user_id='user123',
#                 event_id='event123',
#                 title='Updated Doctor Appointment',
#                 reminders='[{"type": "email", "minutes": 45}, {"type": "popup", "minutes": 15}, {"type": "voice", "minutes": 60}]'
#             )

#         2. Change the time and recurrence of a recurring event:
#             update_event(
#                 self,
#                 user_id='user123',
#                 event_id='event123',
#                 start='2024-08-01T08:00:00',
#                 end='2024-08-01T09:00:00',
#                 recurrence='RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR',
#                 update_series=True
#             )

#         3. Remove all reminders from an event:
#             update_event(
#                 self,
#                 user_id='user123',
#                 event_id='event123',
#                 reminders='[]'
#             )
#     """
#     import logging
#     import os
#     import sys
#     from typing import Optional, List, Dict, Union
#     from dotenv import load_dotenv
#     import json
#     from datetime import datetime, timedelta
#     import pytz

#     logger = logging.getLogger(__name__)
#     logger.setLevel(logging.DEBUG)

#     try:
#         load_dotenv()
#         MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
#         CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
#         if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
#             return json.dumps({"success": False, "message": "MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"})

#         if MEMGPT_TOOLS_PATH not in sys.path:
#             sys.path.append(MEMGPT_TOOLS_PATH)

#         GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
#         GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

#         from google_utils import GoogleCalendarUtils, UserDataManager, is_valid_timezone

#         calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

#         if not local_timezone:
#             local_timezone = UserDataManager.get_user_timezone(user_id)
#         elif not is_valid_timezone(local_timezone):
#             return json.dumps({"success": False, "message": f"Invalid timezone: {local_timezone}"})

#         # Fetch the existing event
#         existing_event = calendar_utils.get_calendar_event(user_id, event_id)
#         if not existing_event:
#             return json.dumps({"success": False, "message": f"Event with ID {event_id} not found"})

#         # Check for conflicts if start or end time is being updated
#         if start is not None or end is not None:
#             new_start = start or existing_event['start'].get('dateTime', existing_event['start'].get('date'))
#             new_end = end or existing_event['end'].get('dateTime', existing_event['end'].get('date'))
#             conflict_check = calendar_utils.check_conflicts(user_id, new_start, new_end, event_id, local_timezone)
#             if not conflict_check["success"]:
#                 return json.dumps(conflict_check)  # Return conflict information

#         # Prepare the update data
#         update_data = calendar_utils.prepare_event_data(
#             user_id,
#             title or existing_event['summary'],
#             start or existing_event['start'].get('dateTime', existing_event['start'].get('date')),
#             end or existing_event['end'].get('dateTime', existing_event['end'].get('date')),
#             description if description is not None else existing_event.get('description'),
#             location if location is not None else existing_event.get('location'),
#             reminders,
#             recurrence if recurrence is not None else existing_event.get('recurrence'),
#             local_timezone
#         )

#         # Remove any fields that weren't specified in the update
#         if title is None:
#             del update_data['summary']
#         if start is None and end is None:
#             del update_data['start']
#             del update_data['end']
#         if description is None:
#             update_data.pop('description', None)
#         if location is None:
#             update_data.pop('location', None)
#         if reminders is None:
#             update_data.pop('reminders', None)
#             update_data.pop('extendedProperties', None)
#         if recurrence is None:
#             update_data.pop('recurrence', None)

#         result = calendar_utils.update_calendar_event(user_id, event_id, update_data, update_series, local_timezone)

#         if result.get("success", False):
#             return json.dumps({"success": True, "event_id": result['event']['id'], "message": "Event updated successfully"})
#         else:
#             return json.dumps({"success": False, "message": result.get('message', 'Unknown error')})

#     except Exception as e:
#         logger.error(f"Error in update_event: {str(e)}", exc_info=True)
#         return json.dumps({"success": False, "message": f"Error updating event: {str(e)}"})
    
# def fetch_events(
#     self: 'Agent',
#     user_id: str,
#     max_results: int = 10,
#     time_min: Optional[str] = None,
#     time_max: Optional[str] = None,
#     local_timezone: Optional[str] = None
# ) -> str:
#     """
#     Fetch upcoming events from the user's Google Calendar within the specified time range.

#     Args:
#         self (Agent): The agent instance calling the tool.
#         user_id (str): The unique identifier for the user.
#         max_results (int): The maximum number of events to return. Default is 10.
#         time_min (Optional[str]): The minimum time to filter events in ISO 8601 format. Default is None.
#             Example: "2024-01-01T00:00:00Z" to fetch events starting from January 1, 2024.
#         time_max (Optional[str]): The maximum time to filter events in ISO 8601 format. Default is None.
#             Example: "2024-01-14T23:59:59Z" to fetch events up to January 14, 2024.
#         local_timezone (Optional[str]): The timezone for the events. If None, the user's default timezone will be used.

#     Returns:
#         str: A JSON string describing the fetched events, including standard and custom reminders.
#     """
#     import os
#     import sys
#     import logging
#     from dotenv import load_dotenv
#     import json
#     from datetime import datetime, timedelta
#     import pytz
#     from typing import Optional

#     logger = logging.getLogger(__name__)
#     logger.setLevel(logging.DEBUG)

#     try:
#         load_dotenv()
#         MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
#         CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
#         if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
#             return json.dumps({"success": False, "message": "MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables"})

#         if MEMGPT_TOOLS_PATH not in sys.path:
#             sys.path.append(MEMGPT_TOOLS_PATH)

#         GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
#         GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

#         from google_utils import GoogleCalendarUtils, UserDataManager, is_valid_timezone, parse_datetime

#         calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

#         if not local_timezone:
#             local_timezone = UserDataManager.get_user_timezone(user_id)
#         elif not is_valid_timezone(local_timezone):
#             return json.dumps({"success": False, "message": f"Invalid timezone: {local_timezone}"})

#         logger.debug(f"Fetching events for user_id: {user_id}, timezone: {local_timezone}")

#         tz = pytz.timezone(local_timezone)
#         now = datetime.now(tz)

#         if not time_min:
#             time_min = now.isoformat()
#         if not time_max:
#             time_max = (now + timedelta(days=1)).isoformat()

#         logger.debug(f"Time range: {time_min} to {time_max}")

#         events_data = calendar_utils.fetch_upcoming_events(user_id, max_results, time_min, time_max, local_timezone)
#         logger.debug(f"Fetched events data: {events_data}")

#         if not events_data.get('items', []):
#             return json.dumps({"success": True, "message": "No upcoming events found.", "events": []})

#         event_list = []
#         for event in events_data['items']:
#             event_summary = {
#                 'id': event['id'],
#                 'title': event['summary'],
#                 'start': event['start'].get('dateTime', event['start'].get('date')),
#                 'end': event['end'].get('dateTime', event['end'].get('date')),
#                 'description': event.get('description', ''),
#                 'location': event.get('location', ''),
#                 'reminders': []
#             }

#             # Handle standard reminders
#             if 'reminders' in event and 'overrides' in event['reminders']:
#                 for reminder in event['reminders']['overrides']:
#                     event_summary['reminders'].append({
#                         'type': reminder['method'],
#                         'minutes': reminder['minutes']
#                     })

#             # Handle custom reminders from extended properties
#             if 'extendedProperties' in event and 'private' in event['extendedProperties']:
#                 custom_reminders = event['extendedProperties']['private'].get('customReminders')
#                 if custom_reminders:
#                     try:
#                         custom_reminders_list = json.loads(custom_reminders)
#                         event_summary['reminders'].extend(custom_reminders_list)
#                     except json.JSONDecodeError:
#                         logger.warning(f"Invalid JSON in customReminders for event {event['id']}")

#             # Handle recurrence
#             if 'recurrence' in event:
#                 event_summary['recurrence'] = event['recurrence']

#             event_list.append(event_summary)

#         result = {
#             "success": True,
#             "events": event_list
#         }

#         return json.dumps(result)

#     except Exception as e:
#         logger.error(f"Error in fetch_events: {str(e)}", exc_info=True)
#         return json.dumps({"success": False, "message": f"Error fetching events: {str(e)}"})
    
# def delete_event(
#     self: Agent,
#     user_id: str,
#     event_id: str,
#     delete_series: bool = False
# ) -> str:
#     """
#     Delete an event from the user's Google Calendar.

#     Args:
#         self (Agent): The agent instance calling the tool.
#         user_id (str): The unique identifier for the user.
#         event_id (str): The unique identifier for the event to be deleted.
#         delete_series (bool): If True, attempts to delete all instances of a recurring event series.
#                               If False, deletes only the specified instance of a recurring event.
#                               Defaults to False.

#     Returns:
#         str: A message indicating success or failure of the event deletion.
#     """
#     import logging
#     import os
#     from googleapiclient.errors import HttpError

#     logger = logging.getLogger(__name__)
#     logger.setLevel(logging.DEBUG)

#     try:
#         CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
#         if not CREDENTIALS_PATH:
#             return "Error: CREDENTIALS_PATH not set in environment variables"

#         logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

#         GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
#         GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

#         # Comment out internal imports for testing purposes
#         from google_utils import GoogleCalendarUtils

#         calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

#         calendar_id = calendar_utils.get_or_create_user_calendar(user_id)
#         if not calendar_id:
#             return "Error: Unable to get or create user calendar"

#         try:
#             event = calendar_utils.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            
#             if delete_series and 'recurringEventId' in event:
#                 # This is part of a recurring series, so we'll delete the series
#                 series_id = event['recurringEventId']
#                 result = calendar_utils.delete_calendar_event(user_id, series_id)
#                 message = f"Event series deleted successfully. ID: {series_id}"
#             else:
#                 # Delete the specific instance or non-recurring event
#                 result = calendar_utils.delete_calendar_event(user_id, event_id)
#                 message = f"Event deleted successfully. ID: {event_id}"

#             logger.debug(f"Result message: {message}")

#             if isinstance(result, dict):
#                 if result.get('success', False):
#                     return message
#                 else:
#                     return f"Failed to delete event: {result.get('message', 'Unknown error')}"
#             elif isinstance(result, bool):
#                 if result:
#                     return message
#                 else:
#                     return "Failed to delete event. It may not exist or you may not have permission to delete it."
#             else:
#                 return f"Unexpected result type from delete_calendar_event: {type(result)}"

#         except HttpError as e:
#             if e.resp.status == 410:
#                 return f"Event (ID: {event_id}) has already been deleted."
#             else:
#                 logger.error(f"HttpError in delete_event: {str(e)}", exc_info=True)
#                 return f"Error deleting event: {str(e)}"
#         except Exception as e:
#             logger.error(f"Error getting or deleting event: {str(e)}", exc_info=True)
#             return f"Error deleting event: {str(e)}"

#     except Exception as e:
#         logger.error(f"Error in delete_event: {str(e)}", exc_info=True)
#         return f"Error in delete_event function: {str(e)}"

# def send_email(
#     self: 'Agent',
#     user_id: str,
#     subject: str,
#     body: str,
#     message_id: Optional[str] = None
# ) -> str:
#     """
#     Send an email using the Google Gmail API.
    
#     Args:
#     self (Agent): The agent instance calling the tool.
#     user_id (str): The unique identifier for the user (recipient) in the MemGPT system.
#     subject (str): The subject of the email.
#     body (str): The body content of the email.
#     message_id (Optional[str]): An optional message ID for threading replies.
    
#     Returns:
#     str: A message indicating success or failure of the email sending process.
#     """
#     # Logging configuration
#     import logging
#     logging.basicConfig(level=logging.INFO)
#     logger = logging.getLogger(__name__)

#     from google_utils import GoogleEmailUtils
#     try:
#         result = GoogleEmailUtils.send_email(user_id, subject, body, message_id)
        
#         if result['status'] == 'success':
#             return f"Message was successfully sent. Message ID: {result['message_id']}"
#         else:
#             return f"Message failed to send with error: {result['message']}"
#     except Exception as e:
#         logger.error(f"Error in send_email: {str(e)}", exc_info=True)
#         return f"Error sending email: {str(e)}"
    




# Global imports for testing purposes only. Comment out the internal import versions while testing.
# from google_utils import GoogleCalendarUtils, UserDataManager, GoogleEmailUtils
# from twilio.rest import Client

#proposed API based function:
# custom_tools.py

# from memgpt.agent import Agent
# from typing import Optional
# import logging
# import requests
# import json

# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # API configuration
# API_BASE_URL = "http://localhost:8000"  # Update this to your actual API URL
# API_KEY = "your-secret-api-key"  # Update this to your actual API key

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
#     Schedule a new event using the EventManagementService API.

#     Args:
#         self (Agent): The agent instance calling the tool.
#         user_id (str): The unique identifier for the user.
#         title (str): The title of the event.
#         start (str): The start time in ISO 8601 format.
#         end (str): The end time in ISO 8601 format.
#         description (Optional[str]): The description of the event.
#         location (Optional[str]): The location of the event.
#         reminders (Optional[str]): JSON string representation of reminders.
#         recurrence (Optional[str]): Recurrence rule in RRULE format.

#     Returns:
#         str: A JSON string indicating success or failure of the event creation.
#     """
#     try:
#         url = f"{API_BASE_URL}/schedule_event"
#         headers = {
#             "Content-Type": "application/json",
#             "X-API-Key": API_KEY
#         }
#         payload = {
#             "user_id": user_id,
#             "event": {
#                 "summary": title,
#                 "start_time": start,
#                 "end_time": end,
#                 "description": description,
#                 "location": location,
#                 "reminders": reminders,
#                 "recurrence": recurrence
#             }
#         }
        
#         response = requests.post(url, headers=headers, json=payload)
#         response.raise_for_status()
        
#         result = response.json()
        
#         if "id" in result:
#             return json.dumps({"success": True, "message": f"Event created: ID: {result['id']}"})
#         else:
#             return json.dumps({"success": False, "message": "Failed to create event"})
    
#     except requests.exceptions.RequestException as e:
#         logger.error(f"Error in schedule_event: {str(e)}", exc_info=True)
#         return json.dumps({"success": False, "message": f"Error scheduling event: {str(e)}"})

# ... (other tools to be updated similarly)



