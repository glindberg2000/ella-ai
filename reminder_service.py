from fastapi import FastAPI, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import logging
import os
import asyncio
from datetime import datetime, timedelta
from dateutil.parser import isoparse
import pytz
from setup_env import setup_env  # Import setup_env
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
from ella_memgpt.tools.google_utils import GoogleCalendarUtils, UserDataManager

# Setup environment
setup_env()

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Constants
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")
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
    local_tz = pytz.timezone(timezone)
    local_time = isoparse(local_time_str)
    if local_time.tzinfo is None:
        local_time = local_tz.localize(local_time)
    utc_time = local_time.astimezone(pytz.utc)
    return utc_time

def convert_to_local_time(utc_time_str, timezone='America/Los_Angeles'):
    utc_time = isoparse(utc_time_str)
    local_tz = pytz.timezone(timezone)
    local_time = utc_time.astimezone(local_tz)
    return local_time

async def fetch_upcoming_events_for_user(user_id: str, memgpt_user_api_key: str, user_timezone: str) -> dict:
    """
    Fetch upcoming events from Google Calendar for a specific user.
    """
    calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GMAIL_TOKEN_PATH)
    time_min = datetime.now(pytz.timezone(user_timezone)).isoformat()
    time_max = (datetime.now(pytz.timezone(user_timezone)) + timedelta(days=1)).isoformat()
    logger.info(f"Fetching events for user {user_id} between {time_min} and {time_max}")
    events = calendar_utils.fetch_upcoming_events(user_id, max_results=10, time_min=time_min, time_max=time_max, user_timezone=user_timezone)
    logger.info(f"Fetched events for user {user_id}: {events}")
    return events

async def send_alert_to_llm(event: dict, memgpt_user_api_key: str, agent_key: str) -> None:
    """
    Send an alert to the LLM about an upcoming event.
    """
    local_start_time = convert_to_local_time(event['start']['dateTime'])
    alert_type = 'send_message'
    if event['reminders'].get('useDefault'):
        alert_type = 'send_message'
    else:
        for reminder in event['reminders'].get('overrides', []):
            if reminder['method'] == 'email':
                alert_type = 'send_email'
            elif reminder['method'] == 'sms':
                alert_type = 'send_text'
            elif reminder['method'] == 'popup':
                alert_type = 'send_voice_message'

    formatted_message = (
        f"[EVENT REMINDER] "
        f"[event_id: {event['id']}] "
        f"[summary: {event['summary']}] "
        f"[start: {local_start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}] "
        f"[end: {convert_to_local_time(event['end']['dateTime']).strftime('%Y-%m-%d %H:%M:%S %Z')}] "
        f"[message: {event['description']}] "
        f"[alert_type: {alert_type}] "
    )

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
                    events = await fetch_upcoming_events_for_user(memgpt_user_id, memgpt_user_api_key)
                    now = datetime.now(pytz.timezone(user_timezone))
                    events_within_alert = []
                    for event in events.get('items', []):
                        try:
                            start_time = pytz.timezone(user_timezone).localize(datetime.fromisoformat(event['start']['dateTime']))
                            alert_time = None
                            if event['reminders'].get('useDefault'):
                                alert_time = start_time - timedelta(minutes=30)  # Default alert 30 minutes before
                            else:
                                for reminder in event['reminders'].get('overrides', []):
                                    if reminder['method'] in ['email', 'sms', 'popup']:
                                        alert_time = start_time - timedelta(minutes=reminder['minutes'])
                                        break

                            time_until_event = start_time - now

                            logger.info(
                                f"Event: {event['summary']}, Start time: {start_time}, "
                                f"Alert time: {alert_time}, Now: {now}, Time until event: {time_until_event}"
                            )

                            if alert_time and now <= alert_time <= (now + timedelta(minutes=5)):
                                events_within_alert.append(event)
                                await send_alert_to_llm(event, memgpt_user_api_key, default_agent_key)
                        except Exception as e:
                            logger.error(f"Error parsing event start time: {e}")
                    if not events_within_alert:
                        logger.info(f"No events fall within the alert window for user {memgpt_user_id}")
        except Exception as e:
            logger.error(f"Error during polling: {str(e)}")
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