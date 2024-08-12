#reminder_service.py
#polls google calendar for events and sends to LLM for response and dispatch

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
import json
from typing import List, Dict, Any, Optional

from ella_dbo.db_manager import (
    create_connection,
    get_user_data_by_field,
    close_connection
)
from ella_memgpt.tools.google_utils import GoogleCalendarUtils, UserDataManager, is_valid_timezone, parse_datetime

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

# Pretty print the import details
import_details = {
    "base_url": base_url,
    "master_api_key": master_api_key,
    "GCAL_TOKEN_PATH": GCAL_TOKEN_PATH,
    "GMAIL_TOKEN_PATH": GMAIL_TOKEN_PATH,
    "GMAIL_SCOPES": GMAIL_SCOPES
}
logger.info(f"Import details:\n{json.dumps(import_details, indent=4)}")

# Verify paths are set
logger.info(f"Google Calendar token path: {GCAL_TOKEN_PATH}")
logger.info(f"Gmail token path: {GMAIL_TOKEN_PATH}")

if not GCAL_TOKEN_PATH or not os.path.exists(GCAL_TOKEN_PATH):
    logger.error(f"Google Calendar token path not set or file does not exist: {GCAL_TOKEN_PATH}")
if not GMAIL_TOKEN_PATH or not os.path.exists(GMAIL_TOKEN_PATH):
    logger.error(f"Gmail token path not set or file does not exist: {GMAIL_TOKEN_PATH}")

# FastAPI app
reminder_app = FastAPI()

def convert_to_utc_time(local_time_str, timezone='America/Los_Angeles'):
    return parse_datetime(local_time_str, timezone).astimezone(pytz.UTC)

def convert_to_local_time(utc_time_str, timezone='America/Los_Angeles'):
    return parse_datetime(utc_time_str, 'UTC').astimezone(pytz.timezone(timezone))

async def fetch_upcoming_events_for_user(user_id: str, memgpt_user_api_key: str, user_timezone: str) -> dict:
    """
    Fetch upcoming events from Google Calendar for a specific user.
    """
    calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GMAIL_TOKEN_PATH)
    time_min = datetime.now(pytz.timezone(user_timezone)).isoformat()
    time_max = (datetime.now(pytz.timezone(user_timezone)) + timedelta(days=1)).isoformat()
    logger.info(f"Fetching events for user {user_id} between {time_min} and {time_max}")
    events = calendar_utils.fetch_upcoming_events(user_id, max_results=10, time_min=time_min, time_max=time_max, local_timezone=user_timezone)
    logger.info(f"Fetched events for user {user_id}: {events}")
    return events


def process_reminders(event: Dict[str, Any], user_timezone: str, current_time: datetime) -> List[Dict[str, Any]]:
    """
    Process reminders for an event, accommodating both short-notice and long-term reminders.
    
    Args:
        event (Dict[str, Any]): The event data from Google Calendar.
        user_timezone (str): The user's timezone.
        current_time (datetime): The current time.

    Returns:
        List[Dict[str, Any]]: A list of processed reminders with alert times and types.
    """
    processed_reminders = []
    start_time = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), user_timezone)
    time_until_event = start_time - current_time

    # Function to add a reminder if it's still in the future
    def add_reminder(minutes: int, reminder_type: str):
        alert_time = start_time - timedelta(minutes=minutes)
        if alert_time > current_time:
            processed_reminders.append({
                'alert_time': alert_time,
                'alert_type': f"send_{reminder_type}",
                'minutes': minutes
            })

    # Process custom reminders first
    if 'extendedProperties' in event and 'private' in event['extendedProperties']:
        custom_reminders_str = event['extendedProperties']['private'].get('customReminders')
        if custom_reminders_str:
            try:
                custom_reminders = json.loads(custom_reminders_str)
                for reminder in custom_reminders:
                    add_reminder(reminder['minutes'], reminder['type'])
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in customReminders for event {event['id']}")

    # Process standard reminders
    if event['reminders'].get('useDefault', True):
        user_prefs = UserDataManager.get_user_reminder_prefs(event['creator']['email'])
        default_reminder_time = user_prefs['default_reminder_time']
        default_methods = user_prefs['reminder_method'].split(',')
        
        for method in default_methods:
            add_reminder(default_reminder_time, method)
    else:
        for reminder in event['reminders'].get('overrides', []):
            add_reminder(reminder['minutes'], reminder['method'])

    # If no valid reminders and the event is in the future, add an immediate reminder
    if not processed_reminders and time_until_event > timedelta(0):
        immediate_reminder_minutes = min(5, max(0, time_until_event.total_seconds() // 60))
        add_reminder(int(immediate_reminder_minutes), 'popup')  # Default to popup for immediate reminders

    return processed_reminders


async def poll_calendar_for_events() -> None:
    logger.info("Starting Calendar polling task")
    calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GCAL_TOKEN_PATH)
    
    while True:
        logger.info("Polling for upcoming events...")
        conn = create_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT memgpt_user_id FROM users")
            active_users = cur.fetchall()
            for user in active_users:
                memgpt_user_id = user[0]
                user_data = get_user_data_by_field(conn, 'memgpt_user_id', memgpt_user_id)
                if user_data:
                    memgpt_user_api_key = user_data.get('memgpt_user_api_key')
                    default_agent_key = user_data.get('default_agent_key')
                    user_timezone = user_data.get('local_timezone', 'America/Los_Angeles')
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

                                # Check if the reminder should be sent and hasn't been sent before
                                if current_time <= alert_time <= (current_time + timedelta(minutes=5)):
                                    reminder_key = f"{reminder['alert_type']}_{reminder['minutes']}"
                                    
                                    if not calendar_utils.check_reminder_status(memgpt_user_id, event['id'], reminder_key):
                                        await send_alert_to_llm(event, memgpt_user_api_key, default_agent_key, user_timezone, reminder)
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
        finally:
            close_connection(conn)
        logger.info("Finished checking for upcoming events. Waiting for 1 minute before the next check.")
        await asyncio.sleep(60)  # Check every 1 minute

async def send_alert_to_llm(event: dict, memgpt_user_api_key: str, agent_key: str, user_timezone: str, reminder: dict) -> None:
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
    
    formatted_message = f"""
    [SYSTEM] Event reminder alert received. Please process the following event information:
    {json.dumps(event_info, indent=2)}

    [INSTRUCTIONS] 
    1. Analyze the event information.
    2. Compose a concise and relevant reminder message for the user. Use an appropriate writing style and length based on the '{reminder['alert_type']}' function which will be used for delivering the note.
    3. The reminder should include key details like event title, time, and any crucial information from the description. 
    4. Use the '{reminder['alert_type']}' function to send the reminder to the user.
    5. If using 'send_voice' function for voice call, ensure the message is conversational and suitable for spoken delivery.
    6. Only use the specified function to send the reminder.
    """

    client = RESTClient(base_url=base_url, token=memgpt_user_api_key)
    try:
        response = client.user_message(agent_id=agent_key, message=formatted_message)
        logging.info(f"MemGPT API response: {response}")
    except Exception as e:
        logging.error(f"Sending message to MemGPT API failed: {str(e)}")


@asynccontextmanager
async def reminder_app_lifespan(app: FastAPI):
    """
    Lifespan context manager for the reminder app.
    """
    logger.info("Reminder app startup tasks")
    task = asyncio.create_task(poll_calendar_for_events())
    try:
        yield
    finally:
        task.cancel()
        await task

reminder_app.router.lifespan_context = reminder_app_lifespan

# Additional endpoints for the reminder_app if needed
@reminder_app.get("/status")
async def reminder_status():
    return {"status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(reminder_app, host="0.0.0.0", port=9400)