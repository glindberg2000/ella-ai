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

async def send_alert_to_llm(event: dict, memgpt_user_api_key: str, agent_key: str, user_timezone: str) -> None:
    local_start_time = convert_to_local_time(event['start']['dateTime'], user_timezone)
    local_end_time = convert_to_local_time(event['end']['dateTime'], user_timezone)
    
    event_info = {
        "event_id": event['id'],
        "summary": event['summary'],
        "start": local_start_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        "end": local_end_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        "description": event.get('description', 'No description'),
    }
    
    alert_type = event.get('alert_type', 'send_email')  # Default to email if not specified

    formatted_message = f"""
    [SYSTEM] Event reminder alert received. Please process the following event information:
    {json.dumps(event_info, indent=2)}

    [INSTRUCTIONS] 
    1. Analyze the event information.
    2. Compose a concise and relevant reminder message for the user.
    3. Use the '{alert_type}' function to send the reminder to the user.
    4. The reminder should be brief but include key details like event title, time, and any crucial information from the description.
    5. Do not include any explanations or additional dialogue in your response. Only use the specified function to send the reminder.
    """

    client = RESTClient(base_url=base_url, token=memgpt_user_api_key)
    try:
        response = client.user_message(agent_id=agent_key, message=formatted_message)
        logging.info(f"MemGPT API response: {response}")
    except Exception as e:
        logging.error(f"Sending message to MemGPT API failed: {str(e)}")

async def poll_calendar_for_events() -> None:
    """
    Poll Google Calendar for upcoming events and send alerts.
    """
    logger.info("Starting Calendar polling task")
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
                    now = datetime.now(pytz.timezone(user_timezone))
                    
                    # Print next upcoming event
                    if events.get('items'):
                        next_event = min(events['items'], key=lambda e: parse_datetime(e['start']['dateTime'], user_timezone))
                        next_event_start = parse_datetime(next_event['start']['dateTime'], user_timezone)
                        time_until_event = next_event_start - now
                        minutes_until_event = time_until_event.total_seconds() / 60

                        logger.info(f"Next upcoming event for user {memgpt_user_id}:")
                        logger.info(f"  Title: {next_event['summary']}")
                        logger.info(f"  Start time: {next_event_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                        logger.info(f"  Minutes until event: {minutes_until_event:.2f}")

                        # Calculate minutes until alert
                        alert_time = None
                        if next_event['reminders'].get('useDefault', True):
                            user_prefs = UserDataManager.get_user_reminder_prefs(memgpt_user_id)
                            default_reminder_time = user_prefs['default_reminder_time']
                            alert_time = next_event_start - timedelta(minutes=default_reminder_time)
                        else:
                            for reminder in next_event['reminders'].get('overrides', []):
                                if reminder['method'] in ['email', 'sms', 'popup', 'voice']:
                                    alert_time = next_event_start - timedelta(minutes=reminder['minutes'])
                                    break

                        if alert_time:
                            minutes_until_alert = (alert_time - now).total_seconds() / 60
                            logger.info(f"  Minutes until alert: {minutes_until_alert:.2f}")
                        else:
                            logger.info("  No alert set for this event")
                    else:
                        logger.info(f"No upcoming events for user {memgpt_user_id}")

                    events_within_alert = []
                    for event in events.get('items', []):
                        try:
                            start_time = parse_datetime(event['start']['dateTime'], user_timezone)
                            alert_time = None
                            if event['reminders'].get('useDefault', True):
                                # Fetch user preferences
                                user_prefs = UserDataManager.get_user_reminder_prefs(memgpt_user_id)
                                default_reminder_time = user_prefs['default_reminder_time']
                                default_methods = user_prefs['reminder_method'].split(',')
                                
                                alert_time = start_time - timedelta(minutes=default_reminder_time)
                                alert_type = default_methods[0] if default_methods else 'send_email'
                            else:
                                for reminder in event['reminders'].get('overrides', []):
                                    if reminder['method'] in ['email', 'sms', 'popup', 'voice']:
                                        alert_time = start_time - timedelta(minutes=reminder['minutes'])
                                        alert_type = f"send_{reminder['method']}"
                                        break
                                
                            if not alert_time:
                                # Final fallback
                                alert_time = start_time - timedelta(minutes=30)
                                alert_type = 'send_email'

                            time_until_event = start_time - now

                            logger.info(
                                f"Event: {event['summary']}, Start time: {start_time}, "
                                f"Alert time: {alert_time}, Now: {now}, Time until event: {time_until_event}"
                            )

                            if alert_time and now <= alert_time <= (now + timedelta(minutes=5)):
                                events_within_alert.append(event)
                                await send_alert_to_llm(event, memgpt_user_api_key, default_agent_key, user_timezone)
                        except Exception as e:
                            logger.error(f"Error processing event: {e}", exc_info=True)
                    if not events_within_alert:
                        logger.info(f"No events fall within the alert window for user {memgpt_user_id}")
        except Exception as e:
            logger.error(f"Error during polling: {str(e)}", exc_info=True)
        finally:
            close_connection(conn)
        logger.info("Finished checking for upcoming events. Waiting for 5 minutes before the next check.")
        await asyncio.sleep(300)  # Check every 5 minutes

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