# #reminder_service.py
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import logging
import os
import asyncio
from datetime import datetime, timedelta
from dateutil.parser import isoparse
import pytz
from setup_env import setup_env
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from memgpt.client.client import RESTClient
from typing import List, Dict, Any, Optional
from ella_dbo.db_manager import get_user_data_by_field, get_active_users, get_db_connection
from ella_memgpt.tools.google_utils import GoogleCalendarUtils, UserDataManager, is_valid_timezone, parse_datetime
from ella_memgpt.tools.memgpt_email_router import MemGPTEmailRouter

# Setup environment
setup_env()

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Constants
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovememgpt1")
GCAL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gcal_token.json')
GMAIL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gmail_token.json')
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MemGPTEmailRouter
email_router = MemGPTEmailRouter(base_url, GMAIL_TOKEN_PATH, GCAL_TOKEN_PATH)

# FastAPI app
reminder_app = FastAPI()

def convert_to_utc_time(local_time_str, timezone='America/Los_Angeles'):
    return parse_datetime(local_time_str, timezone).astimezone(pytz.UTC)

def convert_to_local_time(utc_time_str, timezone='America/Los_Angeles'):
    return parse_datetime(utc_time_str, 'UTC').astimezone(pytz.timezone(timezone))

async def fetch_upcoming_events_for_user(user_id: str, memgpt_user_api_key: str, user_timezone: str) -> dict:
    calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GMAIL_TOKEN_PATH)
    time_min = datetime.now(pytz.timezone(user_timezone)).isoformat()
    time_max = (datetime.now(pytz.timezone(user_timezone)) + timedelta(days=1)).isoformat()
    logger.info(f"Fetching events for user {user_id} between {time_min} and {time_max}")
    events = calendar_utils.fetch_upcoming_events(user_id, max_results=10, time_min=time_min, time_max=time_max, local_timezone=user_timezone)
    logger.info(f"Fetched events for user {user_id}: {events}")
    return events

def process_reminders(event: Dict[str, Any], user_timezone: str, current_time: datetime) -> List[Dict[str, Any]]:
    processed_reminders = []
    start_time = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), user_timezone)
    time_until_event = start_time - current_time

    def add_reminder(minutes: int, reminder_type: str):
        alert_time = start_time - timedelta(minutes=minutes)
        if alert_time > current_time:
            processed_reminders.append({
                'alert_time': alert_time,
                'alert_type': f"send_{reminder_type}",
                'minutes': minutes
            })

    if 'extendedProperties' in event and 'private' in event['extendedProperties']:
        custom_reminders_str = event['extendedProperties']['private'].get('customReminders')
        if custom_reminders_str:
            try:
                custom_reminders = json.loads(custom_reminders_str)
                for reminder in custom_reminders:
                    add_reminder(reminder['minutes'], reminder['type'])
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in customReminders for event {event['id']}")

    if event['reminders'].get('useDefault', True):
        user_prefs = UserDataManager.get_user_reminder_prefs(event['creator']['email'])
        default_reminder_time = user_prefs['default_reminder_time']
        default_methods = user_prefs['reminder_method'].split(',')
        
        for method in default_methods:
            add_reminder(default_reminder_time, method)
    else:
        for reminder in event['reminders'].get('overrides', []):
            add_reminder(reminder['minutes'], reminder['method'])

    if not processed_reminders and time_until_event > timedelta(0):
        immediate_reminder_minutes = min(5, max(0, time_until_event.total_seconds() // 60))
        add_reminder(int(immediate_reminder_minutes), 'popup')

    return processed_reminders

async def poll_calendar_for_events() -> None:
    logger.info("Starting Calendar polling task")
    calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GCAL_TOKEN_PATH)
    
    while True:
        logger.info("Polling for upcoming events...")
        try:
            active_users = get_active_users()
            for user in active_users:
                memgpt_user_id = user['memgpt_user_id']
                memgpt_user_api_key = user['memgpt_user_api_key']
                default_agent_key = user['default_agent_key']
                user_timezone = user['local_timezone']
                if not is_valid_timezone(user_timezone):
                    logger.warning(f"Invalid timezone for user {memgpt_user_id}: {user_timezone}. Using default.")
                    user_timezone = 'America/Los_Angeles'
                
                events = await fetch_upcoming_events_for_user(memgpt_user_id, memgpt_user_api_key, user_timezone)
                current_time = datetime.now(pytz.timezone(user_timezone))
                
                for event in events.get('items', []):
                    try:
                        start_time = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), user_timezone)
                        reminders = process_reminders(event, user_timezone, current_time)

                        for reminder in reminders:
                            alert_time = reminder['alert_time']
                            time_until_event = start_time - current_time

                            logger.info(
                                f"Event: {event['summary']}, Start time: {start_time}, "
                                f"Alert time: {alert_time}, Now: {current_time}, Time until event: {time_until_event}"
                            )

                            if current_time <= alert_time <= (current_time + timedelta(minutes=5)):
                                reminder_key = f"{reminder['alert_type']}_{reminder['minutes']}"
                                
                                if not calendar_utils.check_reminder_status(memgpt_user_id, event['id'], reminder_key):
                                    await send_alert_to_llm(event, memgpt_user_api_key, default_agent_key, user_timezone, reminder, user['email'])
                                    if calendar_utils.update_reminder_status(memgpt_user_id, event['id'], reminder_key):
                                        logger.info(f"Sent and recorded reminder: {reminder_key} for event {event['id']}")
                                    else:
                                        logger.warning(f"Sent reminder but failed to record status: {reminder_key} for event {event['id']}")
                                else:
                                    logger.info(f"Reminder already sent: {reminder_key} for event {event['id']}")

                    except Exception as e:
                        logger.error(f"Error processing event: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Error during polling: {str(e)}", exc_info=True)
        logger.info("Finished checking for upcoming events. Waiting for 1 minute before the next check.")
        await asyncio.sleep(60)  # Check every 1 minute

async def send_alert_to_llm(event: dict, memgpt_user_api_key: str, agent_key: str, user_timezone: str, reminder: dict, user_email: str) -> None:
    local_start_time = convert_to_local_time(event['start']['dateTime'], user_timezone)
    local_end_time = convert_to_local_time(event['end']['dateTime'], user_timezone)
    
    event_info = {
        "event_id": event['id'],
        "summary": event['summary'],
        "start": local_start_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        "end": local_end_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        "description": event.get('description', 'No description'),
        "reminder_type": reminder['alert_type'],
        "minutes_before": reminder['minutes']
    }
    
    instruction_template = """
    [SYSTEM] Event reminder alert received. Please process the following event information:
    {event_info}

    [INSTRUCTIONS] 
    1. Analyze the event information.
    2. Compose a concise and relevant reminder message for the user. Use an appropriate writing style and length based on the '{reminder_type}' alert type.
    3. The reminder should include key details like event title, time, and any crucial information from the description. 
    4. Generate the reminder message only. Do not include any function calls or additional instructions in your response.
    """

    context = {
        "event_info": json.dumps(event_info, indent=2),
        "reminder_type": reminder['alert_type']
    }

    try:
        reminder_content = await generate_reminder_content(context, memgpt_user_api_key, agent_key, instruction_template)
        
        if not reminder_content:
            logging.error("Failed to generate reminder content")
            return

        if reminder['alert_type'] == 'send_email':
            await send_email_alert(event, reminder_content, memgpt_user_api_key, agent_key, user_email)
        elif reminder['alert_type'] == 'send_sms':
            await send_sms_alert(event, reminder_content, user_email)
        elif reminder['alert_type'] == 'send_voice':
            await send_voice_alert(event, reminder_content, user_email)
        else:
            logging.warning(f"Unsupported alert type: {reminder['alert_type']}")

    except Exception as e:
        logging.error(f"Failed to send alert: {str(e)}")

async def generate_reminder_content(context: dict, memgpt_user_api_key: str, agent_key: str, instruction_template: str) -> str:
    try:
        client = RESTClient(base_url=base_url, token=memgpt_user_api_key)
        formatted_message = instruction_template.format(**context)
        response = client.user_message(agent_id=agent_key, message=formatted_message)
        return email_router.extract_email_content(response)
    except Exception as e:
        logging.error(f"Error in generating reminder content: {str(e)}")
        return None

async def send_email_alert(event: dict, reminder_content: str, memgpt_user_api_key: str, agent_key: str, user_email: str):
    try:
        await email_router.generate_and_send_email(
            to_email=user_email,
            subject=f"Reminder: {event['summary']}",
            context={"body": reminder_content},
            memgpt_user_api_key=memgpt_user_api_key,
            agent_key=agent_key,
            is_reply=False
        )
        logging.info(f"Email reminder sent to {user_email} for event: {event['summary']}")
    except Exception as e:
        logging.error(f"Failed to send email reminder: {str(e)}")

async def send_sms_alert(event: dict, reminder_content: str, user_email: str):
    logging.info(f"SMS reminder to be sent to user: {user_email} for event: {event['summary']}")
    logging.info(f"SMS Content: {reminder_content}")
    # TODO: Implement actual SMS sending

async def send_voice_alert(event: dict, reminder_content: str, user_email: str):
    logging.info(f"Voice reminder to be initiated for user: {user_email} for event: {event['summary']}")
    logging.info(f"Voice Call Content: {reminder_content}")

@asynccontextmanager
async def reminder_app_lifespan(app: FastAPI):
    logger.info("Reminder app startup tasks")
    task = asyncio.create_task(poll_calendar_for_events())
    try:
        yield
    finally:
        task.cancel()
        await task

reminder_app.router.lifespan_context = reminder_app_lifespan

@reminder_app.get("/status")
async def reminder_status():
    return {"status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(reminder_app, host="0.0.0.0", port=9400)
# #polls google calendar for events and sends to LLM for response and dispatch

# import json
# from fastapi import FastAPI, HTTPException, BackgroundTasks
# from contextlib import asynccontextmanager
# import logging
# import os
# import asyncio
# from datetime import datetime, timedelta
# from dateutil.parser import isoparse
# import pytz
# from setup_env import setup_env
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# from memgpt.client.client import RESTClient
# from typing import List, Dict, Any, Optional
# from ella_dbo.db_manager import get_user_data_by_field
# from ella_memgpt.tools.google_utils import GoogleCalendarUtils, UserDataManager, is_valid_timezone, parse_datetime
# from ella_memgpt.tools.memgpt_email_router import MemGPTEmailRouter
# from ella_dbo.db_manager import get_active_users

# # In your poll_calendar_for_events function
# active_users = get_active_users()
# for user in active_users:
#     memgpt_user_id = user['memgpt_user_id']
#     # ... rest of your processing logic

# # Setup environment
# setup_env()

# # Load environment variables from .env file
# from dotenv import load_dotenv
# load_dotenv()

# # Constants
# base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
# master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovememgpt1")
# GCAL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gcal_token.json')
# GMAIL_TOKEN_PATH = os.path.join(os.getenv('CREDENTIALS_PATH', ''), 'gmail_token.json')
# GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# # Logging configuration
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Pretty print the import details
# import_details = {
#     "base_url": base_url,
#     "master_api_key": master_api_key,
#     "GCAL_TOKEN_PATH": GCAL_TOKEN_PATH,
#     "GMAIL_TOKEN_PATH": GMAIL_TOKEN_PATH,
#     "GMAIL_SCOPES": GMAIL_SCOPES
# }
# logger.info(f"Import details:\n{json.dumps(import_details, indent=4)}")

# # Verify paths are set
# logger.info(f"Google Calendar token path: {GCAL_TOKEN_PATH}")
# logger.info(f"Gmail token path: {GMAIL_TOKEN_PATH}")

# if not GCAL_TOKEN_PATH or not os.path.exists(GCAL_TOKEN_PATH):
#     logger.error(f"Google Calendar token path not set or file does not exist: {GCAL_TOKEN_PATH}")
# if not GMAIL_TOKEN_PATH or not os.path.exists(GMAIL_TOKEN_PATH):
#     logger.error(f"Gmail token path not set or file does not exist: {GMAIL_TOKEN_PATH}")

# # Initialize MemGPTEmailRouter
# email_router = MemGPTEmailRouter(base_url, GMAIL_TOKEN_PATH, GCAL_TOKEN_PATH)

# # FastAPI app
# reminder_app = FastAPI()

# def convert_to_utc_time(local_time_str, timezone='America/Los_Angeles'):
#     return parse_datetime(local_time_str, timezone).astimezone(pytz.UTC)

# def convert_to_local_time(utc_time_str, timezone='America/Los_Angeles'):
#     return parse_datetime(utc_time_str, 'UTC').astimezone(pytz.timezone(timezone))

# async def fetch_upcoming_events_for_user(user_id: str, memgpt_user_api_key: str, user_timezone: str) -> dict:
#     """
#     Fetch upcoming events from Google Calendar for a specific user.
#     """
#     calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GMAIL_TOKEN_PATH)
#     time_min = datetime.now(pytz.timezone(user_timezone)).isoformat()
#     time_max = (datetime.now(pytz.timezone(user_timezone)) + timedelta(days=1)).isoformat()
#     logger.info(f"Fetching events for user {user_id} between {time_min} and {time_max}")
#     events = calendar_utils.fetch_upcoming_events(user_id, max_results=10, time_min=time_min, time_max=time_max, local_timezone=user_timezone)
#     logger.info(f"Fetched events for user {user_id}: {events}")
#     return events


# def process_reminders(event: Dict[str, Any], user_timezone: str, current_time: datetime) -> List[Dict[str, Any]]:
#     """
#     Process reminders for an event, accommodating both short-notice and long-term reminders.
    
#     Args:
#         event (Dict[str, Any]): The event data from Google Calendar.
#         user_timezone (str): The user's timezone.
#         current_time (datetime): The current time.

#     Returns:
#         List[Dict[str, Any]]: A list of processed reminders with alert times and types.
#     """
#     processed_reminders = []
#     start_time = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), user_timezone)
#     time_until_event = start_time - current_time

#     # Function to add a reminder if it's still in the future
#     def add_reminder(minutes: int, reminder_type: str):
#         alert_time = start_time - timedelta(minutes=minutes)
#         if alert_time > current_time:
#             processed_reminders.append({
#                 'alert_time': alert_time,
#                 'alert_type': f"send_{reminder_type}",
#                 'minutes': minutes
#             })

#     # Process custom reminders first
#     if 'extendedProperties' in event and 'private' in event['extendedProperties']:
#         custom_reminders_str = event['extendedProperties']['private'].get('customReminders')
#         if custom_reminders_str:
#             try:
#                 custom_reminders = json.loads(custom_reminders_str)
#                 for reminder in custom_reminders:
#                     add_reminder(reminder['minutes'], reminder['type'])
#             except json.JSONDecodeError:
#                 logger.warning(f"Invalid JSON in customReminders for event {event['id']}")

#     # Process standard reminders
#     if event['reminders'].get('useDefault', True):
#         user_prefs = UserDataManager.get_user_reminder_prefs(event['creator']['email'])
#         default_reminder_time = user_prefs['default_reminder_time']
#         default_methods = user_prefs['reminder_method'].split(',')
        
#         for method in default_methods:
#             add_reminder(default_reminder_time, method)
#     else:
#         for reminder in event['reminders'].get('overrides', []):
#             add_reminder(reminder['minutes'], reminder['method'])

#     # If no valid reminders and the event is in the future, add an immediate reminder
#     if not processed_reminders and time_until_event > timedelta(0):
#         immediate_reminder_minutes = min(5, max(0, time_until_event.total_seconds() // 60))
#         add_reminder(int(immediate_reminder_minutes), 'popup')  # Default to popup for immediate reminders

#     return processed_reminders


# async def poll_calendar_for_events() -> None:
#     logger.info("Starting Calendar polling task")
#     calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GCAL_TOKEN_PATH)
    
#     while True:
#         logger.info("Polling for upcoming events...")
#         conn = create_connection()
#         try:
#             active_users = get_active_users()
#             for user in active_users:
#                 memgpt_user_id = user[0]
#                 user_data = get_user_data_by_field(conn, 'memgpt_user_id', memgpt_user_id)
#                 if user_data:
#                     memgpt_user_api_key = user_data.get('memgpt_user_api_key')
#                     default_agent_key = user_data.get('default_agent_key')
#                     user_timezone = user_data.get('local_timezone', 'America/Los_Angeles')
#                     if not is_valid_timezone(user_timezone):
#                         logger.warning(f"Invalid timezone for user {memgpt_user_id}: {user_timezone}. Using default.")
#                         user_timezone = 'America/Los_Angeles'
                    
#                     events = await fetch_upcoming_events_for_user(memgpt_user_id, memgpt_user_api_key, user_timezone)
#                     current_time = datetime.now(pytz.timezone(user_timezone))
                    
#                     for event in events.get('items', []):
#                         try:
#                             start_time = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), user_timezone)
#                             reminders = process_reminders(event, user_timezone, current_time)

#                             for reminder in reminders:
#                                 alert_time = reminder['alert_time']
#                                 time_until_event = start_time - current_time

#                                 logger.info(
#                                     f"Event: {event['summary']}, Start time: {start_time}, "
#                                     f"Alert time: {alert_time}, Now: {current_time}, Time until event: {time_until_event}"
#                                 )

#                                 # Check if the reminder should be sent and hasn't been sent before
#                                 if current_time <= alert_time <= (current_time + timedelta(minutes=5)):
#                                     reminder_key = f"{reminder['alert_type']}_{reminder['minutes']}"
                                    
#                                     if not calendar_utils.check_reminder_status(memgpt_user_id, event['id'], reminder_key):
#                                         await send_alert_to_llm(event, memgpt_user_api_key, default_agent_key, user_timezone, reminder, user_data['email'])
#                                         if calendar_utils.update_reminder_status(memgpt_user_id, event['id'], reminder_key):
#                                             logger.info(f"Sent and recorded reminder: {reminder_key} for event {event['id']}")
#                                         else:
#                                             logger.warning(f"Sent reminder but failed to record status: {reminder_key} for event {event['id']}")
#                                     else:
#                                         logger.info(f"Reminder already sent: {reminder_key} for event {event['id']}")

#                         except Exception as e:
#                             logger.error(f"Error processing event: {e}", exc_info=True)
                    
#         except Exception as e:
#             logger.error(f"Error during polling: {str(e)}", exc_info=True)
#         finally:
#             close_connection(conn)
#         logger.info("Finished checking for upcoming events. Waiting for 1 minute before the next check.")
#         await asyncio.sleep(60)  # Check every 1 minute

# # async def send_alert_to_llm(event: dict, memgpt_user_api_key: str, agent_key: str, user_timezone: str, reminder: dict) -> None:
# #     local_start_time = convert_to_local_time(event['start']['dateTime'], user_timezone)
# #     local_end_time = convert_to_local_time(event['end']['dateTime'], user_timezone)
    
# #     event_info = {
# #         "event_id": event['id'],
# #         "summary": event['summary'],
# #         "start": local_start_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
# #         "end": local_end_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
# #         "description": event.get('description', 'No description'),
# #         "reminder_type": reminder['alert_type'],
# #         "minutes_before": reminder['minutes']
# #     }
    
# #     formatted_message = f"""
# #     [SYSTEM] Event reminder alert received. Please process the following event information:
# #     {json.dumps(event_info, indent=2)}

# #     [INSTRUCTIONS] 
# #     1. Analyze the event information.
# #     2. Compose a concise and relevant reminder message for the user. Use an appropriate writing style and length based on the '{reminder['alert_type']}' function which will be used for delivering the note.
# #     3. The reminder should include key details like event title, time, and any crucial information from the description. 
# #     4. Use the '{reminder['alert_type']}' function to send the reminder to the user.
# #     5. If using 'send_voice' function for voice call, ensure the message is conversational and suitable for spoken delivery.
# #     6. Only use the specified function to send the reminder.
# #     """

# #     client = RESTClient(base_url=base_url, token=memgpt_user_api_key)
# #     try:
# #         response = client.user_message(agent_id=agent_key, message=formatted_message)
# #         logging.info(f"MemGPT API response: {response}")
# #     except Exception as e:
# #         logging.error(f"Sending message to MemGPT API failed: {str(e)}")

# async def send_alert_to_llm(event: dict, memgpt_user_api_key: str, agent_key: str, user_timezone: str, reminder: dict, user_email: str) -> None:
#     local_start_time = convert_to_local_time(event['start']['dateTime'], user_timezone)
#     local_end_time = convert_to_local_time(event['end']['dateTime'], user_timezone)
    
#     event_info = {
#         "event_id": event['id'],
#         "summary": event['summary'],
#         "start": local_start_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
#         "end": local_end_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
#         "description": event.get('description', 'No description'),
#         "reminder_type": reminder['alert_type'],
#         "minutes_before": reminder['minutes']
#     }
    
#     instruction_template = """
#     [SYSTEM] Event reminder alert received. Please process the following event information:
#     {event_info}

#     [INSTRUCTIONS] 
#     1. Analyze the event information.
#     2. Compose a concise and relevant reminder message for the user. Use an appropriate writing style and length based on the '{reminder_type}' alert type.
#     3. The reminder should include key details like event title, time, and any crucial information from the description. 
#     4. Generate the reminder message only. Do not include any function calls or additional instructions in your response.
#     """

#     context = {
#         "event_info": json.dumps(event_info, indent=2),
#         "reminder_type": reminder['alert_type']
#     }

#     try:
#         reminder_content = await generate_reminder_content(context, memgpt_user_api_key, agent_key, instruction_template)
        
#         if not reminder_content:
#             logging.error("Failed to generate reminder content")
#             return

#         if reminder['alert_type'] == 'send_email':
#             await send_email_alert(event, reminder_content, memgpt_user_api_key, agent_key, user_email)
#         elif reminder['alert_type'] == 'send_sms':
#             await send_sms_alert(event, reminder_content, user_email)
#         elif reminder['alert_type'] == 'send_voice':
#             await send_voice_alert(event, reminder_content, user_email)
#         else:
#             logging.warning(f"Unsupported alert type: {reminder['alert_type']}")

#     except Exception as e:
#         logging.error(f"Failed to send alert: {str(e)}")

# async def generate_reminder_content(context: dict, memgpt_user_api_key: str, agent_key: str, instruction_template: str) -> str:
#     try:
#         client = RESTClient(base_url=base_url, token=memgpt_user_api_key)
#         formatted_message = instruction_template.format(**context)
#         response = client.user_message(agent_id=agent_key, message=formatted_message)
#         return email_router.extract_email_content(response)
#     except Exception as e:
#         logging.error(f"Error in generating reminder content: {str(e)}")
#         return None

# async def send_email_alert(event: dict, reminder_content: str, memgpt_user_api_key: str, agent_key: str, user_email: str):
#     try:
#         await email_router.generate_and_send_email(
#             to_email=user_email,
#             subject=f"Reminder: {event['summary']}",
#             context={"body": reminder_content},
#             memgpt_user_api_key=memgpt_user_api_key,
#             agent_key=agent_key,
#             is_reply=False
#         )
#         logging.info(f"Email reminder sent to {user_email} for event: {event['summary']}")
#     except Exception as e:
#         logging.error(f"Failed to send email reminder: {str(e)}")


# async def send_sms_alert(event: dict, reminder_content: str, user_email: str):
#     # Implement SMS sending logic here
#     logging.info(f"SMS reminder to be sent to user: {user_email} for event: {event['summary']}")
#     logging.info(f"SMS Content: {reminder_content}")
#     # TODO: Implement actual SMS sending

# async def send_voice_alert(event: dict, reminder_content: str, user_email: str):
#     # Implement voice call logic here
#     logging.info(f"Voice reminder to be initiated for user: {user_email} for event: {event['summary']}")
#     logging.info(f"Voice Call Content: {reminder_content}")


# @asynccontextmanager
# async def reminder_app_lifespan(app: FastAPI):
#     """
#     Lifespan context manager for the reminder app.
#     """
#     logger.info("Reminder app startup tasks")
#     task = asyncio.create_task(poll_calendar_for_events())
#     try:
#         yield
#     finally:
#         task.cancel()
#         await task

# reminder_app.router.lifespan_context = reminder_app_lifespan

# # Additional endpoints for the reminder_app if needed
# @reminder_app.get("/status")
# async def reminder_status():
#     return {"status": "running"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(reminder_app, host="0.0.0.0", port=9400)