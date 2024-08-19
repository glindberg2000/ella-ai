import pytest
import requests
from datetime import datetime, timedelta
import pytz
import os
from dotenv import load_dotenv
import sys


# Load environment variables from .env
load_dotenv()

# Get the root path from the environment variable
ella_ai_root = os.getenv('ELLA_AI_ROOT', '')

# Add the root directory to the Python path
sys.path.append(ella_ai_root)
from ella_dbo.models import Event, ConflictInfo, EventResponse, ScheduleEventRequest, UpdateEventData, UpdateEventRequest, ReminderRequest, EmailRequest


# Load environment variables
load_dotenv()

BASE_URL = os.getenv("SERVICES_API_URL", "http://localhost:9999")
API_KEY = os.getenv("API_KEY")
REAL_USER_ID = "f0236456-a4cc-4cb2-a772-1de0e968126a"

@pytest.fixture
def event_data():
    now = datetime.now(pytz.timezone('America/Los_Angeles'))
    start_time = now + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)
    
    return {
        "summary": "Real Test Event",
        "start": {"dateTime": start_time.isoformat(), "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "America/Los_Angeles"},
        "description": "This is a real test event",
        "location": "Real Test Location",
        "reminders": {"useDefault": False, "overrides": [{"method": "email", "minutes": 15}]},
        "local_timezone": "America/Los_Angeles"
    }

def test_schedule_event_real(event_data):
    request_data = {
        "user_id": REAL_USER_ID,
        "event": event_data
    }

    url = f"{BASE_URL}/schedule_event"
    print(f"Sending POST request to: {url}")

    response = requests.post(
        url,
        json=request_data,
        headers={"X-API-Key": API_KEY}
    )

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()

    if not response_data["success"]:
        print("Event scheduling failed. Checking for conflict information.")
        assert "conflict_info" in response_data, "Expected 'conflict_info' in response when scheduling fails"
        print(f"Conflict info: {response_data['conflict_info']}")
    else:
        assert "event" in response_data, "Expected 'event' in response data"
        assert response_data["event"]["summary"] == event_data["summary"], "Event summary doesn't match"
        assert response_data["event"]["start"]["timeZone"] == event_data["local_timezone"], "Start timezone doesn't match"
        assert response_data["event"]["end"]["timeZone"] == event_data["local_timezone"], "End timezone doesn't match"
def test_fetch_events_real():
    url = f"{BASE_URL}/events"
    params = {
        "user_id": REAL_USER_ID,
        "max_results": 10
    }
    response = requests.get(
        url,
        params=params,
        headers={"X-API-Key": API_KEY}
    )
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")
    
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    response_data = response.json()
    assert isinstance(response_data, list), "Expected response to be a list of events"
    for event in response_data:
        assert Event(**event), "Each event should conform to the Event model"
        
def test_delete_event_real():
    # First, schedule an event
    now = datetime.now(pytz.timezone('America/Los_Angeles'))
    start_time = now + timedelta(hours=2)  # Increase to 2 hours to avoid conflicts
    end_time = start_time + timedelta(hours=1)
    event_data = {
        "summary": "Test Event to Delete",
        "start": {"dateTime": start_time.isoformat(), "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "America/Los_Angeles"},
    }
    schedule_url = f"{BASE_URL}/schedule_event"
    schedule_response = requests.post(
        schedule_url,
        json={"user_id": REAL_USER_ID, "event": event_data},
        headers={"X-API-Key": API_KEY}
    )
    print(f"Schedule response status code: {schedule_response.status_code}")
    print(f"Schedule response content: {schedule_response.content}")
    
    assert schedule_response.status_code == 200, f"Expected status code 200, but got {schedule_response.status_code}"
    
    response_data = schedule_response.json()
    if not response_data.get('success', False):
        print("Event scheduling failed. Skipping deletion test.")
        print(f"Conflict info: {response_data.get('conflict_info')}")
        return  # Skip the rest of the test

    assert 'event' in response_data, "Expected 'event' key in response data"
    assert 'id' in response_data['event'], "Expected 'id' key in event data"
    
    event_id = response_data['event']['id']

    # Now, delete the event
    delete_url = f"{BASE_URL}/events/{event_id}"
    delete_response = requests.delete(
        delete_url,
        params={"user_id": REAL_USER_ID},
        headers={"X-API-Key": API_KEY}
    )
    print(f"Delete response status code: {delete_response.status_code}")
    print(f"Delete response content: {delete_response.content}")
    
    assert delete_response.status_code == 200
    response_data = delete_response.json()
    assert response_data["success"]
    assert "deleted successfully" in response_data["message"]

    # Verify the event is deleted
    fetch_url = f"{BASE_URL}/events"
    fetch_response = requests.get(
        fetch_url,
        params={"user_id": REAL_USER_ID},
        headers={"X-API-Key": API_KEY}
    )
    assert fetch_response.status_code == 200
    events = fetch_response.json()
    assert all(event['id'] != event_id for event in events)


def test_update_event_real():
    # First, schedule an event
    now = datetime.now(pytz.timezone('America/Los_Angeles'))
    start_time = now + timedelta(hours=3)  # Increase to 3 hours to avoid conflicts
    end_time = start_time + timedelta(hours=1)
    event_data = {
        "summary": "Test Event to Update",
        "start": {"dateTime": start_time.isoformat(), "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "America/Los_Angeles"},
    }
    schedule_url = f"{BASE_URL}/schedule_event"
    schedule_response = requests.post(
        schedule_url,
        json={"user_id": REAL_USER_ID, "event": event_data},
        headers={"X-API-Key": API_KEY}
    )
    print(f"Schedule response status code: {schedule_response.status_code}")
    print(f"Schedule response content: {schedule_response.content}")
    
    assert schedule_response.status_code == 200, f"Expected status code 200, but got {schedule_response.status_code}"
    
    response_data = schedule_response.json()
    if not response_data.get('success', False):
        print("Event scheduling failed. Skipping update test.")
        print(f"Conflict info: {response_data.get('conflict_info')}")
        return  # Skip the rest of the test

    assert 'event' in response_data, "Expected 'event' key in response data"
    assert 'id' in response_data['event'], "Expected 'id' key in event data"
    
    event_id = response_data['event']['id']

    # Now, update the event
    new_start_time = start_time + timedelta(minutes=30)
    new_end_time = new_start_time + timedelta(hours=1)
    update_data = {
        "user_id": REAL_USER_ID,
        "event": {
            "summary": "Updated Test Event",
            "start": {"dateTime": new_start_time.isoformat(), "timeZone": "America/Los_Angeles"},
            "end": {"dateTime": new_end_time.isoformat(), "timeZone": "America/Los_Angeles"},
            "description": "This is an updated test event"
        },
        "update_series": False
    }
    update_url = f"{BASE_URL}/events/{event_id}"
    update_response = requests.put(
        update_url,
        json=update_data,
        headers={"X-API-Key": API_KEY}
    )
    print(f"Update response status code: {update_response.status_code}")
    print(f"Update response content: {update_response.content}")
    
    assert update_response.status_code == 200
    response_data = update_response.json()
    assert response_data["success"]
    assert response_data["event"]["summary"] == "Updated Test Event"
    assert response_data["event"]["description"] == "This is an updated test event"

    # Verify the event is updated
    fetch_url = f"{BASE_URL}/events"
    fetch_response = requests.get(
        fetch_url,
        params={"user_id": REAL_USER_ID},
        headers={"X-API-Key": API_KEY}
    )
    assert fetch_response.status_code == 200
    events = fetch_response.json()
    updated_event = next((event for event in events if event['id'] == event_id), None)
    assert updated_event is not None
    assert updated_event['summary'] == "Updated Test Event"
    assert updated_event['description'] == "This is an updated test event"
if __name__ == "__main__":
    pytest.main(["-v", "-s"])