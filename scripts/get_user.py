import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the bearer token from the .env variable
bearer_token = os.getenv("TEST_MEMGPT_USER_API_KEY")

url = "http://localhost:8080/api/tools"

headers = {
    "accept": "application/json",
    "authorization": f"Bearer {bearer_token}"
}

response = requests.get(url, headers=headers)

print(response.text)