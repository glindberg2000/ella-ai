from memgpt.client.admin import Admin as AdminRESTClient
from ella_memgpt.extendedRESTclient import ExtendedRESTClient

import os
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8283")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")

def create_memgpt_user_and_api_key():
    """Create a MemGPT user and API key."""
    admin_api = AdminRESTClient(base_url, master_api_key)

    # Create a MemGPT user
    memgpt_user = admin_api.create_user()

    # Return the MemGPT user ID and API key using direct attribute access
    return {
        "memgpt_user_id": str(memgpt_user.user_id),  # Directly access the user_id attribute
        "memgpt_user_api_key": memgpt_user.api_key  # Directly access the api_key attribute
    }



def manage_agents(memgpt_user_api_key):
    # Use the get_agents function to fetch the list of agents
    user_api = ExtendedRESTClient(base_url, memgpt_user_api_key)

    # agents = api.get_agents(memgpt_user_api_key)
    agents = user_api.list_agents()

    # If there are no agents, create a new default agent
    if not agents or agents.get("num_agents", 0) == 0:
        # No agents found, creating new default agent
        config = {
            "name": "Anna",
            "preset": "memgpt_chat",
            "human": "cs_phd",
            "persona": "anna_pa",
        }

        # Call to create a new agent with the specified config
        user_api.create_agent(config)

    # Re-fetch the agents after creating a new one to include it in the list
    agents = user_api.list_agents()

    # Now, regardless of whether agents were initially found or a new one was created,
    # you have an up-to-date list of agents for the display logic.
    # If there are now agents, get the list of agent IDs and names
    if agents and agents.get("num_agents") > 0:
        agent_list = agents.get("agents", [])
        agent_keys = [{"id": agent["id"], "name": agent["name"]} for agent in agent_list]
        return agent_keys
    else:
        return []