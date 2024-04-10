import json
import os

import aiohttp
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class MemGPTAPI:
    def __init__(self):
        # Load environment variables
        self.base_url = os.getenv("MEMGPT_API_URL", "default_base_url_if_not_set")
        self.master_api_key = os.getenv(
            "MEMGPT_SERVER_PASS", "default_api_key_if_not_set"
        )

    def get_users(self):
        """Retrieve a list of users from the memGPT API."""
        url = f"{self.base_url}/admin/users"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.master_api_key}",
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def get_user_api_key(self, user_id):
        """Retrieve the API key for a specific user."""
        url = f"{self.base_url}/admin/users/keys?user_id={user_id}"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.master_api_key}",
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    # Create a new Api key works:
    def create_user_api_key(self, user_id):
        """Retrieve the API key for a specific user."""
        url = f"{self.base_url}/admin/users/keys"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.master_api_key}",
        }
        # Now using POST and including user_id in the JSON body
        payload = {"user_id": user_id}
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            # Parse the response based on the actual structure
            # Adjust the parsing as necessary based on the API's response structure
            api_key = response.json().get("api_key", [])
            return api_key
        else:
            return None
            # Handle non-200 responses or add more specific error handling as needed

    def create_user(self):
        """Create a new user in the memGPT API."""
        url = f"{self.base_url}/admin/users"
        # payload = {"user_id": user_id}
        payload = {}
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.master_api_key}",
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 201]:  # Success or Created
            return response.json()
        else:
            return None

    def get_agents(self, user_api_key):
        """Retrieve a list of agents for a specific user from the memGPT API."""
        url = f"{self.base_url}/api/agents"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {user_api_key}",
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()  # Returns the list of agents in the specified format
        else:
            return None

    def create_agent(self, user_api_key, config):
        """Create a new agent with a specific configuration for the user in the memGPT API."""
        url = f"{self.base_url}/api/agents"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {user_api_key}",
        }
        payload = {"config": config}
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code in [200, 201]:  # Success or Created
            agent_data = response.json()
            # Adjust the return statement as per the actual response structure
            return agent_data.get("agent_state", {}).get("id")  # Extract the agent ID
        else:
            return None

    def send_message_to_agent(self, user_api_key, agent_id, message):
        """Send a message to a specific agent with the given configuration."""
        url = (
            f"{self.base_url}/api/agents/message"  # Adjust if the endpoint is different
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_api_key}",
        }
        payload = {
            "agent_id": agent_id,
            "message": message,
            "stream": "False",
            "role": "user",
        }
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            # Handle successful response
            print(f"Raw Response:", response.text)
            return response.text  # Parse and return the response as needed
        else:
            # Handle errors or unsuccessful attempts
            print(f"Raw Response:", response.text)
            return {"message": "error"}

    async def send_message_to_agent_streamed(self, user_api_key, agent_id, message):
        url = f"{self.base_url}/api/agents/message"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_api_key}",
        }
        payload = {
            "agent_id": agent_id,
            "message": message,
            "stream": "True",
            "role": "user",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                async for line in response.content:
                    decoded_line = line.decode("utf-8").strip()
                    if not decoded_line:  # Skip empty lines
                        continue
                    print(f"Raw streamed data: {decoded_line}")
                    try:
                        # Remove the "data: " prefix before parsing JSON
                        if decoded_line.startswith("data: "):
                            json_str = decoded_line[6:]  # Skip the "data: " part
                            data = json.loads(json_str)
                            yield data
                        else:
                            print("Streamed line doesn't start with 'data: '")
                    except json.JSONDecodeError:
                        print("Error parsing JSON from streamed data")
                        continue


# Example usage
if __name__ == "__main__":
    api = MemGPTAPI()
    user_id = "mycustomuser"

    # users = api.get_users()
    # if users and any(user['user_id'] == user_id for user in users.get('user_list', [])):
    #     print("User exists, fetching API key...")
    #     user_key = api.get_user_api_key(user_id)
    #     print(f"User API Key: {user_key}")
    # else:
    #     print("User does not exist, creating user...")
    #     new_user = api.create_user(user_id)
    #     print(f"New User Created: {new_user}")

    agents = api.get_agents("sk-cb20905260d5c4f8d133e32873a56d41b776d50d4e36c0fc")
    print(agents)
