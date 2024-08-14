import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import app from main, and get API_KEY from environment
from main import app, API_KEY
from dotenv import load_dotenv
load_dotenv()

REAL_USER_ID = os.getenv("TEST_MEMGPT_USER_ID")
REAL_USER_TIMEZONE = os.getenv("TEST_USER_TIMEZONE", "UTC")

# Import after environment is loaded
from utils import UserDataManager, EventManagementUtils

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_user_data():
    return {
        "memgpt_user_id": "test_user_123",
        "email": "test@example.com",
        "local_timezone": "UTC",
        "memgpt_user_api_key": "test_api_key",
        "default_agent_key": "test_agent_key"
    }

@pytest.fixture
def mock_event_data():
    return {
        "summary": "Test Event",
        "start_time": "2023-08-15T10:00:00",
        "end_time": "2023-08-15T11:00:00",
        "description": "This is a test event",
        "location": "Test Location",
        "reminders": '[{"method": "email", "minutes": 30}]',
        "recurrence": "RRULE:FREQ=DAILY;COUNT=3"
    }

@pytest.fixture
def real_event_data():
    now = datetime.now()
    start_time = now + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)
    return {
        "summary": "Real Test Event",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "description": "This is a real test event",
        "location": "Real Test Location",
        "reminders": '[{"method": "email", "minutes": 15}]'
    }

def test_schedule_event_mock(client, mock_user_data, mock_event_data):
    with patch.object(UserDataManager, 'get_user_data', return_value=mock_user_data):
        with patch.object(EventManagementUtils, 'schedule_event') as mock_schedule:
            mock_schedule.return_value = {
                "success": True,
                "event": {
                    "id": "test_event_id_123",
                    **mock_event_data
                }
            }

            response = client.post(
                "/schedule_event",
                json={
                    "user_id": mock_user_data["memgpt_user_id"],
                    "event": mock_event_data
                },
                headers={"X-API-Key": API_KEY}
            )

            assert response.status_code == 200
            assert response.json()["success"] == True
            assert response.json()["event"]["id"] == "test_event_id_123"
            assert response.json()["event"]["summary"] == mock_event_data["summary"]

@pytest.mark.skipif(not REAL_USER_ID, reason="Real user ID not provided")
def test_schedule_event_real(client, real_event_data):
    response = client.post(
        "/schedule_event",
        json={
            "user_id": REAL_USER_ID,
            "event": real_event_data
        },
        headers={"X-API-Key": API_KEY}
    )

    assert response.status_code == 200
    response_data = response.json()
    
    if response_data["success"]:
        assert "id" in response_data["event"]
        assert response_data["event"]["summary"] == real_event_data["summary"]
    else:
        assert "conflict_info" in response_data
        assert "available_slots" in response_data["conflict_info"]
        assert "message" in response_data["conflict_info"]

    return response_data  # Return the response data

@pytest.mark.skipif(not REAL_USER_ID, reason="Real user ID not provided")
def test_update_event_real(client, real_event_data):
    # First, schedule an event
    schedule_response = test_schedule_event_real(client, real_event_data)
    
    if not schedule_response["success"]:
        pytest.skip("Failed to schedule event for update test due to conflicts")

    event_id = schedule_response["event"]["id"]
    
    # Now, update the event
    updated_data = {
        **real_event_data,
        "summary": "Updated Real Test Event",
        "description": "This is an updated real test event"
    }

    response = client.put(
        f"/events/{event_id}",
        json={
            "user_id": REAL_USER_ID,
            "event": updated_data,
            "update_series": False
        },
        headers={"X-API-Key": API_KEY}
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] == True
    assert response_data["event"]["summary"] == "Updated Real Test Event"
    assert response_data["event"]["description"] == "This is an updated real test event"
    
@pytest.mark.skipif(not REAL_USER_ID, reason="Real user ID not provided")
def test_fetch_events_real(client):
    response = client.get(
        f"/events?user_id={REAL_USER_ID}",
        headers={"X-API-Key": API_KEY}
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] == True
    assert "events" in response_data
    assert isinstance(response_data["events"], list)

@pytest.mark.skipif(not REAL_USER_ID, reason="Real user ID not provided")
def test_delete_event_real(client, real_event_data):
    # First, schedule an event
    schedule_response = test_schedule_event_real(client, real_event_data)
    
    if not schedule_response["success"]:
        pytest.skip("Failed to schedule event for delete test due to conflicts")

    event_id = schedule_response["event"]["id"]

    # Now, delete the event
    response = client.delete(
        f"/events/{event_id}?user_id={REAL_USER_ID}",
        headers={"X-API-Key": API_KEY}
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] == True
    assert "message" in response_data
    assert "deleted successfully" in response_data["message"]

    # Verify that the event is deleted
    fetch_response = client.get(
        f"/events?user_id={REAL_USER_ID}",
        headers={"X-API-Key": API_KEY}
    )

    fetch_data = fetch_response.json()
    assert all(event["id"] != event_id for event in fetch_data["events"])

@pytest.mark.skipif(not REAL_USER_ID, reason="Real user ID not provided")
def test_schedule_conflicting_event_real(client, real_event_data):
    # First, schedule an event
    first_response = test_schedule_event_real(client, real_event_data)
    
    if not first_response["success"]:
        pytest.skip("Failed to schedule first event for conflict test due to existing conflicts")

    # Now, try to schedule a conflicting event
    conflicting_data = {
        **real_event_data,
        "summary": "Conflicting Event"
    }

    response = client.post(
        "/schedule_event",
        json={
            "user_id": REAL_USER_ID,
            "event": conflicting_data
        },
        headers={"X-API-Key": API_KEY}
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["success"] == False
    assert "conflict_info" in response_data
    assert "available_slots" in response_data["conflict_info"]
    assert "message" in response_data["conflict_info"]

@pytest.mark.skipif(not REAL_USER_ID, reason="Real user ID not provided")
def test_schedule_recurring_event_real(client):
    now = datetime.now()
    start_time = now + timedelta(hours=2)
    end_time = start_time + timedelta(hours=1)
    recurring_event_data = {
        "summary": "Recurring Test Event",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "description": "This is a recurring test event",
        "recurrence": "RRULE:FREQ=DAILY;COUNT=3"
    }

    response = client.post(
        "/schedule_event",
        json={
            "user_id": REAL_USER_ID,
            "event": recurring_event_data
        },
        headers={"X-API-Key": API_KEY}
    )

    assert response.status_code == 200
    response_data = response.json()
    
    if response_data["success"]:
        assert "recurrence" in response_data["event"]
    else:
        assert "conflict_info" in response_data
        assert "available_slots" in response_data["conflict_info"]
        assert "message" in response_data["conflict_info"]

if __name__ == "__main__":
    pytest.main([__file__])