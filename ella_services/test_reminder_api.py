import pytest
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add a file handler to capture logs
file_handler = logging.FileHandler('test_logs.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:9999")
API_KEY = os.getenv("API_KEY", "your-secret-api-key")
REAL_USER_ID = os.getenv("TEST_MEMGPT_USER_ID")

@pytest.mark.asyncio
async def test_api_health():
    logger.info("Starting API health check")
    url = f"{API_BASE_URL}/"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as response:
                logger.info(f"Health check response status: {response.status}")
                response_text = await response.text()
                logger.info(f"Health check response body: {response_text}")
                assert response.status == 200, f"Expected status 200, got {response.status}"
        except asyncio.TimeoutError:
            logger.error("API health check timed out after 5 seconds")
            pytest.fail("API health check timed out")
        except Exception as e:
            logger.error(f"API health check failed: {str(e)}")
            pytest.fail(f"API health check failed: {str(e)}")

@pytest.mark.asyncio
async def test_send_reminder():
    await test_api_health()  # Ensure API is healthy before proceeding
    logger.info("Starting test_send_reminder")
    url = f"{API_BASE_URL}/send_reminder"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "user_id": REAL_USER_ID,
        "event_id": "test_event_id",
        "event_summary": "Test Event",
        "event_start": "2024-08-15T10:00:00-07:00",
        "event_end": "2024-08-15T11:00:00-07:00",
        "event_description": "This is a test event for the reminder system",
        "reminder_type": "email",
        "minutes_before": 30
    }
    logger.info(f"Sending request to {url}")
    logger.debug(f"Request payload: {payload}")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload, timeout=90) as response:
                logger.info(f"Response status: {response.status}")
                response_text = await response.text()
                logger.info(f"Response body: {response_text}")
                try:
                    response_json = json.loads(response_text)
                    logger.info(f"Response JSON: {json.dumps(response_json, indent=2)}")
                except json.JSONDecodeError:
                    logger.error("Response is not valid JSON")
                assert response.status == 200, f"Expected status 200, got {response.status}. Response: {response_text}"
                result = await response.json()
                assert result['success'] is True, f"Expected success to be True, got {result.get('success')}"
                assert result['message'] == "Reminder sent successfully", f"Expected message 'Reminder sent successfully', got '{result.get('message')}'"
                assert 'message_id' in result, "Expected 'message_id' in response"
                assert 'recipient' in result, "Expected 'recipient' in response"
                logger.info(f"Reminder sent successfully to {result['recipient']}. Message ID: {result['message_id']}")
                print(f"\nReminder email sent to: {result['recipient']}")
                print(f"Message ID: {result['message_id']}")
        except asyncio.TimeoutError:
            logger.error("Request timed out after 90 seconds")
            pytest.fail("Request timed out after 90 seconds")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            pytest.fail(f"Test failed: {str(e)}")
    logger.info("test_send_reminder completed")

if __name__ == "__main__":
    pytest.main([__file__, "-vv", "--capture=no"])
    
    # Print the contents of the log file
    with open('test_logs.log', 'r') as log_file:
        print("\nTest Logs:")
        print(log_file.read())