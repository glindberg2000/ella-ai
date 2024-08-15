import os
import sys
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uuid

import pytz
from ella_dbo.models import Event, ScheduleEventRequest

# Ensure the current directory is first in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the main app and utilities from the local directory
from main import app, API_KEY
from utils import EventManagementUtils, UserDataManager
from google_service_manager import google_service_manager

# Load environment variables
load_dotenv()
REAL_USER_ID = os.getenv("TEST_MEMGPT_USER_ID")
REAL_USER_TIMEZONE = os.getenv("TEST_USER_TIMEZONE", "UTC")

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(scope="function")
def test_calendar():
    # Create a temporary calendar for testing
    calendar_service = google_service_manager.get_calendar_service()
    test_calendar_id = f"test_calendar_{uuid.uuid4().hex}"
    calendar = {
        'summary': test_calendar_id,
        'timeZone': 'America/Los_Angeles'
    }
    created_calendar = calendar_service.calendars().insert(body=calendar).execute()
    
    yield created_calendar['id']
    
    # Clean up: delete the temporary calendar after the test
    calendar_service.calendars().delete(calendarId=created_calendar['id']).execute()

@pytest.fixture
def real_event_data():
    now = datetime.now(pytz.timezone('America/Los_Angeles'))
    start_time = now + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)
    return Event(
        summary="Real Test Event",
        start={"dateTime": start_time.isoformat(), "timeZone": "America/Los_Angeles"},
        end={"dateTime": end_time.isoformat(), "timeZone": "America/Los_Angeles"},
        description="This is a real test event",
        location="Real Test Location",
        reminders={"useDefault": False, "overrides": [{"method": "email", "minutes": 15}]},
        local_timezone="America/Los_Angeles"
    )

def test_schedule_event_real(client: TestClient, test_calendar: str, real_event_data: Event):
    # Use the real user ID, but with a temporary test calendar
    original_method = EventManagementUtils.get_or_create_user_calendar
    EventManagementUtils.get_or_create_user_calendar = lambda user_id: test_calendar
    
    try:
        request_data = ScheduleEventRequest(user_id=REAL_USER_ID, event=real_event_data)
        response = client.post(
            "/schedule_event",
            json=request_data.model_dump(),
            headers={"X-API-Key": API_KEY}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"]
        assert "event" in response_data
        assert response_data["event"]["summary"] == real_event_data.summary
        assert response_data["event"]["start"]["timeZone"] == real_event_data.local_timezone
        assert response_data["event"]["end"]["timeZone"] == real_event_data.local_timezone
        
    finally:
        EventManagementUtils.get_or_create_user_calendar = original_method

# Add this utility function to utils.py or a new test_utils.py file
def clear_test_calendar(calendar_id: str):
    calendar_service = google_service_manager.get_calendar_service()
    events = calendar_service.events().list(calendarId=calendar_id).execute()
    for event in events.get('items', []):
        calendar_service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()