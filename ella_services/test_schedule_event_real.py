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

REAL_USER_ID = "20ef8d14-2123-46ae-b4c6-892316a9660e"
REAL_USER_TIMEZONE = os.getenv("TEST_USER_TIMEZONE", "America/Los_Angeles")
BASE_URL = os.getenv("SERVICES_API_URL", "http://localhost:9999")

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        print(f"TestClient created with base URL: {BASE_URL}")
        yield client

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
    print(f"Test calendar created with ID: {created_calendar['id']}")
    yield created_calendar['id']
    # Clean up: delete the temporary calendar after the test
    calendar_service.calendars().delete(calendarId=created_calendar['id']).execute()
    print(f"Test calendar deleted: {created_calendar['id']}")

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

def test_schedule_event_mocked(client: TestClient, test_calendar: str, real_event_data: Event):
    # Use a mocked user ID and calendar
    mocked_user_id = "mocked_user_123"
    
    # Mock the get_or_create_user_calendar method
    original_method = EventManagementUtils.get_or_create_user_calendar
    EventManagementUtils.get_or_create_user_calendar = lambda user_id: test_calendar

    # Mock the get_user_data method
    original_get_user_data = UserDataManager.get_user_data
    UserDataManager.get_user_data = lambda user_id: {
        "email": "mocked_user@example.com",
        "local_timezone": "America/Los_Angeles"
    }

    try:
        request_data = ScheduleEventRequest(user_id=mocked_user_id, event=real_event_data)
        url = f"{BASE_URL}/schedule_event"
        print(f"Sending POST request to: {url}")
        response = client.post(
            url,
            json=request_data.model_dump(),
            headers={"X-API-Key": API_KEY}
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"]
        assert "event" in response_data
        assert response_data["event"]["summary"] == real_event_data.summary
        assert response_data["event"]["start"]["timeZone"] == real_event_data.local_timezone
        assert response_data["event"]["end"]["timeZone"] == real_event_data.local_timezone
        
    finally:
        EventManagementUtils.get_or_create_user_calendar = original_method
        UserDataManager.get_user_data = original_get_user_data

def test_schedule_event_real(client: TestClient, real_event_data: Event):
    # Use the real user ID
    try:
        request_data = ScheduleEventRequest(user_id=REAL_USER_ID, event=real_event_data)
        url = f"{BASE_URL}/schedule_event"
        print(f"Sending POST request to: {url}")
        response = client.post(
            url,
            json=request_data.model_dump(),
            headers={"X-API-Key": API_KEY}
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"]
        assert "event" in response_data
        assert response_data["event"]["summary"] == real_event_data.summary
        assert response_data["event"]["start"]["timeZone"] == real_event_data.local_timezone
        assert response_data["event"]["end"]["timeZone"] == real_event_data.local_timezone
        
    except AssertionError as e:
        print(f"Test failed. Response status: {response.status_code}")
        print(f"Response content: {response.content}")
        raise e

def test_get_or_create_user_calendar():
    calendar_id = EventManagementUtils.get_or_create_user_calendar(REAL_USER_ID)
    assert calendar_id is not None, f"Failed to get or create calendar for user {REAL_USER_ID}"
    print(f"Successfully got or created calendar: {calendar_id}")

if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])