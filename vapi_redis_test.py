import httpx
import asyncio
from dotenv import load_dotenv
import os


# Use an absolute path to the .env file
project_dir = os.path.dirname(os.path.abspath(__file__))  # Current script's directory
dotenv_path = os.path.join(project_dir, '.env')  # Adjust as needed

import logging
logging.basicConfig(level=logging.INFO)  # Ensure logging is set up

logging.info("Loading dotenv from path: %s", dotenv_path)  # Confirm path
load_dotenv(dotenv_path=dotenv_path)  # Load the .env file

# Check if the environment variable is loaded
api_key = os.getenv("MEMGPT_SERVER_PASS", "default_key")
base_url = os.getenv('MEMGPT_API_URL', 'default_url')
memgpt_user_api_key= os.getenv("TEST_MEMGPT_USER_API_KEY", "default_key")
memgpt_user_id= os.getenv("TEST_MEMGPT_USER_ID", "default_key")
memgpt_agent_key= os.getenv("TEST_MEMGPT_AGENT_KEY", "default_key")
memgpt_vapi_key= os.getenv("TEST_MEMGPT_VAPI_KEY", "default_key")
logging.info("MEMGPT_SERVER_PASS: %s", api_key)
logging.info("MEMGPT_API_URL: %s", base_url)
logging.info("TEST_MEMGPT_USER_API_KEY: %s", memgpt_user_api_key)
logging.info("TEST_MEMGPT_USER_ID: %s", memgpt_user_id)
logging.info("TEST_MEMGPT_AGENT_KEY: %s", memgpt_agent_key)
logging.info("TEST_MEMGPT_VAPI_KEY: %s", memgpt_vapi_key)





async def test_voice_input():
    url = 'http://localhost:8000/stream'
    data = {'text': 'Hi, 28.', 'id':'myidentifier'}
    headers = {'Content-Type': 'application/json'}

    # Increased verbosity in client handling
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=None)) as client:
        response = await client.post(url, json=data, headers=headers)
        print(f"raw response: {response.text}")
        try:
            # Check response status to ensure it's ready for streaming
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                async for line in response.aiter_lines():
                    if line.startswith('data:'):
                        print("Received:", line)
                        break  # Optionally continue to process more lines as needed
        except Exception as e:
            print(f"Error during SSE reception: {e}")





# Asynchronous function to test streaming with a POST request
async def test_voice_input2():
    url = 'http://localhost:9000/memgpt-sse/chat/completions'
    data = {
    "call": {
        "serverUrlSecret": str(memgpt_user_api_key)+':'+str(memgpt_agent_key)
    },
    "messages": [
        {"content": "How do you think coffee has shaped the history of human civilization?"}
        ]
    }

    headers = {'Content-Type': 'application/json'}

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=None)) as client:
        # Send POST request with JSON data and set stream=True
        async with client.stream("POST", url, json=data, headers=headers) as response:
            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                # Read the streamed response line by line
                async for line in response.aiter_lines():
                    if line:
                        print("Received:", line)
            else:
                print("Failed to get a successful response")

if __name__ == "__main__":
    asyncio.run(test_voice_input2())









