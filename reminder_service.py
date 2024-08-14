# #reminder_service.py
import json
import logging
import os
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from dateutil.parser import isoparse
import pytz
from fastapi import FastAPI, HTTPException, BackgroundTasks
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from setup_env import setup_env
from memgpt.client.client import RESTClient
from ella_dbo.db_manager import get_user_data_by_field, get_active_users, get_db_connection
from ella_memgpt.tools.google_utils import GoogleCalendarUtils, is_valid_timezone, parse_datetime
from ella_memgpt.tools.memgpt_email_router import MemGPTEmailRouter
from ella_memgpt.tools.voice_call_manager import VoiceCallManager
from ella_memgpt.tools.google_service_manager import google_service_manager


# Setup environment
setup_env()

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Constants
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovememgpt1")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MemGPTEmailRouter
email_router = MemGPTEmailRouter()

# Initialize VoiceCallManager
voice_call_manager = VoiceCallManager()

# FastAPI app
reminder_app = FastAPI()

calendar_utils = GoogleCalendarUtils(google_service_manager.get_calendar_service())





def convert_to_utc_time(local_time_str, timezone='America/Los_Angeles'):
    return parse_datetime(local_time_str, timezone).astimezone(pytz.UTC)

def convert_to_local_time(utc_time_str, timezone='America/Los_Angeles'):
    return parse_datetime(utc_time_str, 'UTC').astimezone(pytz.timezone(timezone))

# async def fetch_upcoming_events_for_user(user_id: str, user_timezone: str) -> dict:
#     calendar_utils = GoogleCalendarUtils(GCAL_TOKEN_PATH, GMAIL_TOKEN_PATH)
#     time_min = datetime.now(pytz.timezone(user_timezone)).isoformat()
#     time_max = (datetime.now(pytz.timezone(user_timezone)) + timedelta(days=1)).isoformat()
#     logger.info(f"Fetching events for user {user_id} between {time_min} and {time_max}")
#     events = calendar_utils.fetch_upcoming_events(user_id, max_results=10, time_min=time_min, time_max=time_max, local_timezone=user_timezone)
#     logger.info(f"Fetched events for user {user_id}: {events}")
#     return events

async def fetch_upcoming_events_for_user(user_id: str, user_timezone: str) -> dict:
    time_min = datetime.now(pytz.timezone(user_timezone)).isoformat()
    time_max = (datetime.now(pytz.timezone(user_timezone)) + timedelta(days=1)).isoformat()
    logger.info(f"Fetching events for user {user_id} between {time_min} and {time_max}")
    try:
        events = calendar_utils.fetch_upcoming_events(user_id, max_results=10, time_min=time_min, time_max=time_max, local_timezone=user_timezone)
        logger.info(f"Fetched events for user {user_id}: {events}")
        return events
    except Exception as e:
        logger.error(f"Error fetching events for user {user_id}: {str(e)}")
        return {"items": []}

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
    
    while True:
        logger.info("Polling for upcoming events...")
        try:
            google_service_manager.refresh_credentials()
            active_users = get_active_users()
            for user in active_users:
                memgpt_user_id = user['memgpt_user_id']
                user_timezone = user['local_timezone']
                if not is_valid_timezone(user_timezone):
                    logger.warning(f"Invalid timezone for user {memgpt_user_id}: {user_timezone}. Using default.")
                    user_timezone = 'America/Los_Angeles'
                
                events = await fetch_upcoming_events_for_user(memgpt_user_id, user_timezone)
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
                                    await send_alert_to_llm(event, memgpt_user_id, user_timezone, reminder)
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


async def send_alert_to_llm(
    event: Dict[str, Any], 
    memgpt_user_id: str,
    user_timezone: str, 
    reminder: Dict[str, Any]
) -> None:
    try:
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
        2. Compose a thoughtful and encouraging reminder message for the user. Use an appropriate writing style and length based on the '{reminder_type}' alert type.
        3. The reminder should include key details like event title, time, and any crucial information from the description but you can also add other conversational creative language much like a human would.
        4. Generate the reminder message only. Do not include any function calls or additional instructions in your response.
        """

        context = {
            "event_info": json.dumps(event_info, indent=2),
            "reminder_type": reminder['alert_type']
        }

        user_data = get_user_data_by_field('memgpt_user_id', memgpt_user_id)
        reminder_content = await generate_reminder_content(context, user_data['memgpt_user_api_key'], user_data['default_agent_key'], instruction_template)
        
        if not reminder_content:
            logger.error(f"Failed to generate reminder content for event: {event['summary']}")
            return

        alert_function = {
            'send_email': send_email_alert,
            'send_sms': send_sms_alert,
            'send_voice': send_voice_alert
        }.get(reminder['alert_type'])

        if alert_function:
            await alert_function(event, reminder_content, memgpt_user_id)
        else:
            logger.warning(f"Unsupported alert type: {reminder['alert_type']} for event: {event['summary']}")

    except Exception as e:
        logger.error(f"Failed to send alert for event {event['summary']}: {str(e)}", exc_info=True)

async def generate_reminder_content(context: dict, memgpt_user_api_key: str, agent_key: str, instruction_template: str) -> str:
    try:
        client = RESTClient(base_url=base_url, token=memgpt_user_api_key)
        formatted_message = instruction_template.format(**context)
        response = client.user_message(agent_id=agent_key, message=formatted_message)
        return email_router.extract_email_content(response)
    except Exception as e:
        logging.error(f"Error in generating reminder content: {str(e)}")
        return None

async def send_email_alert(event: Dict[str, Any], reminder_content: str, memgpt_user_api_key: str, agent_key: str, user_email: str) -> None:
    try:
        await email_router.generate_and_send_email(
            to_email=user_email,
            subject=f"Reminder: {event['summary']}",
            context={"body": reminder_content},
            memgpt_user_api_key=memgpt_user_api_key,
            agent_key=agent_key,
            is_reply=False
        )
        logger.info(f"Email reminder sent to {user_email} for event: {event['summary']}")
    except Exception as e:
        logger.error(f"Failed to send email reminder for event {event['summary']}: {str(e)}", exc_info=True)

async def send_sms_alert(event: Dict[str, Any], reminder_content: str, memgpt_user_api_key: str, agent_key: str, user_email: str) -> None:
    logger.info(f"SMS reminder to be sent to user: {user_email} for event: {event['summary']}")
    logger.info(f"SMS Content: {reminder_content}")
    # TODO: Implement actual SMS sending

async def send_voice_alert(event: Dict[str, Any], reminder_content: str, memgpt_user_api_key: str, agent_key: str, user_email: str) -> None:
    try:
        # Retrieve the user_id based on the user_email
        user_data = UserDataManager.get_user_data_by_email(user_email)
        if not user_data:
            logger.error(f"User data not found for email: {user_email}")
            return

        user_id = user_data.get('memgpt_user_id')
        if not user_id:
            logger.error(f"MemGPT user ID not found for email: {user_email}")
            return

        # Prepare the voice message content
        voice_message = f"Reminder for event: {event['summary']}. {reminder_content}"

        # Use the VoiceCallManager to send the voice call
        result = await voice_call_manager.send_voice_call(user_id, voice_message)
        
        logger.info(f"Voice reminder result for user {user_email}: {result}")
    except Exception as e:
        logger.error(f"Failed to send voice reminder for event {event['summary']}: {str(e)}", exc_info=True)



# Update the reminder_app_lifespan to close the voice_call_manager
@asynccontextmanager
async def reminder_app_lifespan(app: FastAPI):
    logger.info("Reminder app startup tasks")
    task = asyncio.create_task(poll_calendar_for_events())
    try:
        yield
    finally:
        task.cancel()
        await task
        await voice_call_manager.close()

reminder_app.router.lifespan_context = reminder_app_lifespan

@reminder_app.get("/status")
async def reminder_status():
    return {"status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(reminder_app, host="0.0.0.0", port=9400)
