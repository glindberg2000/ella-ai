

import argparse
import requests
import os
import sys
import json
from dotenv import load_dotenv
from prettytable import PrettyTable
import textwrap


# Add the ella_dbo directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ella_dbo')))

# Import the database management functions from db_manager module
from db_manager import (
    create_connection,
    get_user_data_by_memgpt_id
)


# Load environment variables from .env file one directory above
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)
api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")
base_url = os.getenv('MEMGPT_API_URL', 'http://localhost:8283')

def get_messages_by_agent_row(user_api_key, user_id, agent_row, start=0, count=10):
    agents = list_agents(user_api_key, user_id)  # Ensure this function returns a list
    if 1 <= agent_row <= len(agents):
        agent_id = agents[agent_row - 1]['id']
        print(f"Fetching messages for agent ID: {agent_id}")
        get_messages_by_agent_id(user_api_key, agent_id, start, count)
    else:
        print(f"Invalid agent index: {agent_row}. Please provide a value between 1 and {len(agents)}.")


def wrap_text(text, width):
    """
    Wrap text to the specified width.
    Args:
    text (str): The text to wrap.
    width (int): The width to wrap to.
    
    Returns:
    str: The wrapped text.
    """
    return '\n'.join(textwrap.wrap(text, width))

def parse_nested_json(text, wrap_width=50):
    try:
        # Attempt to parse the text as JSON
        parsed_json = json.loads(text)
        # Convert parsed JSON to a nicely formatted string
        formatted_json = json.dumps(parsed_json, indent=4)
        # Wrap the formatted JSON for better table display
        return "\n".join(textwrap.wrap(formatted_json, wrap_width))
    except json.JSONDecodeError:
        # Wrap the original text if it's not a JSON string
        return "\n".join(textwrap.wrap(text, wrap_width))

def clean_text(text):
    # Strip leading and trailing spaces and replace multiple spaces with a single space
    return ' '.join(text.split())

def get_messages_by_agent_id(user_api_key, agent_id, start=0, count=10):
    url = f"{base_url}/api/agents/{agent_id}/messages?start={start}&count={count}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {user_api_key}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        messages_data = json.loads(response.text)
        if 'messages' in messages_data and messages_data['messages']:
            table = PrettyTable()
            table.field_names = ["Message ID", "Role", "Text", "Tool Calls", "Timestamp"]
            for message in messages_data['messages']:
                if message:
                    # Handle potentially nested JSON in the 'text' field
                    text_content = parse_nested_json(message.get('text', ''))
                    
                    # Extract and format tool call details if present
                    tool_calls = message.get('tool_calls')
                    tool_call_details = "\n".join(textwrap.wrap(json.dumps(tool_calls, indent=4), 50)) if tool_calls else "None"
                    
                    # Add cleaned and wrapped data to the table
                    table.add_row([
                        clean_text(message.get('id', 'N/A')),
                        clean_text(message.get('role', 'N/A')),
                        clean_text(text_content),
                        clean_text(tool_call_details),
                        clean_text(message.get('created_at', 'N/A'))
                    ])
            print(table)
        else:
            print("No messages found.")
    else:
        print(f"Error fetching messages for agent {agent_id}: {response.status_code} - {response.text}")


def list_agents(user_api_key,user_id):
    url = f"{base_url}/api/agents"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {user_api_key}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        agents = json.loads(response.text)
        table = PrettyTable()
        # Update table title or headers to include user_id for clarity
        table.title = f"Agents for User ID {user_id}"
        table.field_names = ["Index", "Agent ID"]
        # Enumerate through agents to add index and agent ID
        for index, agent in enumerate(agents.get('agents', []), start=1):
            table.add_row([index, agent.get('id', 'N/A')])
        print(table)
    else:
        print(f"Error listing agents for user {user_id}: {response.status_code} - {response.text}")
    return agents.get('agents', [])


def get_agent_count(api_token, user_id):
    # Use the get_user_api_key function to get the API key for the user
    user_api_key = get_user_api_key(api_token, user_id)
    if not user_api_key:
        return 0

    url = f"{base_url}/api/agents"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {user_api_key}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        agents_data = json.loads(response.text)
        return agents_data.get('num_agents', 0)  # Directly use the num_agents field from the response
    else:
        print(f"Error listing agents for user {user_id}: {response.status_code} - {response.text}")
        return "Error listing agents"

def search_agent_by_id(api_token, agent_id):
    url = f"{base_url}/admin/users"
    headers = {"accept": "application/json", "authorization": f"Bearer {api_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        users = json.loads(response.text).get('user_list', [])
        for user in users:
            user_api_key = get_user_api_key(api_token, user['user_id'])  # Fetch user's API key
            agents = list_agents(user_api_key, user['user_id'])  # Fetch list of agents for each user
            for agent in agents:
                if agent['id'] == agent_id:
                    print(f"Agent {agent_id} found under user ID {user['user_id']}")
                    return user['user_id'], user_api_key
        print("Agent not found")
        return None, None
    else:
        print(f"Error fetching users: {response.status_code} - {response.text}")
        return None, None



def list_users(api_token):
    # Create a database connection
    conn = create_connection()
    try:
        url = f"{base_url}/admin/users"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {api_token}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            users = json.loads(response.text)
            table = PrettyTable()
            table.field_names = ["Index", "User ID", "Agents", "API Key", "Default Agent Key", "VAPI Key"]
            for i, user in enumerate(users.get('user_list', []), start=1):
                user_id = user.get('user_id', 'N/A')
                agent_count = get_agent_count(api_token, user_id)
                api_key = get_user_api_key(api_token, user_id)  # Existing API key fetch

                # Fetch additional data from the database
                user_data = get_user_data_by_memgpt_id(conn, user_id)
                default_agent_key = user_data[1] if user_data else 'Unavailable'
                vapi_key = user_data[2] if user_data else 'Unavailable'

                table.add_row([i, user_id, agent_count, api_key, default_agent_key, vapi_key])
            print(table)
            return users['user_list']
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    finally:
        if conn:
            conn.close()  # Make sure to close the database connection

# Example call to list_users
# list_users('your_api_token', 'http://your_api_base_url', 'path_to_your_database.db')


# Example call to list_users
# list_users('your_api_token', 'http://your_api_base_url', 'path_to_your_database.db')

# def list_users(api_token):
#     url = f"{base_url}/admin/users"
#     headers = {
#         "accept": "application/json",
#         "authorization": f"Bearer {api_token}"
#     }
#     response = requests.get(url, headers=headers)
#     if response.status_code == 200:
#         users = json.loads(response.text)
#         table = PrettyTable()
#         table.field_names = ["Index", "User ID", "Agent Count", "API Key"]
#         for i, user in enumerate(users.get('user_list', []), start=1):
#             user_id = user.get('user_id', 'N/A')
#             agent_count = get_agent_count(api_token, user_id)
#             api_key = get_user_api_key(api_token, user_id)  # Fetch the API key
#             table.add_row([i, user_id, agent_count, api_key])
#         print(table)
#         return users['user_list']
#     else:
#         print(f"Error: {response.status_code} - {response.text}")
#         return None

def get_user_api_key(api_token, user_id):
    url = f"{base_url}/admin/users/keys?user_id={user_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        api_key_list = json.loads(response.text)
        if api_key_list['api_key_list']:
            return api_key_list['api_key_list'][0]  # Assuming the first key is usable
        else:
            return None
    else:
        print(f"Error fetching API key for user {user_id}: {response.status_code} - {response.text}")
        return None
import argparse

def main():
    parser = argparse.ArgumentParser(description="Test Suite for API commands")
    #parser.add_argument('--api_token', type=str, required=False, help='API token for authorization')
    
    # Creating subparsers for each command
    subparsers = parser.add_subparsers(dest='command', help='sub-command help')
    
    # Parser for listing users
    parser_list_users = subparsers.add_parser('list_users', help='List all users')
    
    # Parser for listing agents
    parser_list_agents = subparsers.add_parser('list_agents', help='List agents for a user')
    parser_list_agents.add_argument('user_index', type=int, help='Index of the user to list agents for')

    # Parser for searching an agent by ID across all users and displaying messages
    parser_search_agent = subparsers.add_parser('search_agent', help='Search for an agent by ID and display messages')
    parser_search_agent.add_argument('agent_id', type=str, help='Agent ID to search for')

    # Parser for getting messages for an agent by row number
    parser_get_messages = subparsers.add_parser('get_messages_by_row', help='Get messages for an agent by row')
    parser_get_messages.add_argument('user_index', type=int, help='Index of the user')
    parser_get_messages.add_argument('agent_index', type=int, help='Index of the agent')
    parser_get_messages.add_argument('--start', type=int, default=0, help='Starting index for messages')
    parser_get_messages.add_argument('--count', type=int, default=10, help='Number of messages to retrieve')

    args = parser.parse_args()
    
    if args.command == 'list_users':
        list_users(api_key)
    elif args.command == 'list_agents':
        users = list_users(api_key)  # First list users to get user list
        if users and 0 <= args.user_index - 1 < len(users):
            user = users[args.user_index - 1]
            user_api_key = get_user_api_key(api_key, user['user_id'])
            if user_api_key:
                list_agents(user_api_key, user['user_id'])
            else:
                print("Failed to retrieve user API key.")
        else:
            print("Invalid user index.")
    elif args.command == 'get_messages_by_row':
        users = list_users(api_key)  # First list users to get user list
        if users and 0 <= args.user_index - 1 < len(users):
            user = users[args.user_index - 1]
            user_api_key = get_user_api_key(api_key, user['user_id'])
            if user_api_key:
                agents = list_agents(user_api_key, user['user_id'])
                if agents and 0 <= args.agent_index - 1 < len(agents):
                    agent_id = agents[args.agent_index - 1]['id']
                    get_messages_by_agent_id(user_api_key, agent_id, args.start, args.count)
                else:
                    print("Invalid agent index.")
            else:
                print("Failed to retrieve user API key.")
        else:
            print("Invalid user index.")
    elif args.command == 'search_agent':
        user_id, user_api_key = search_agent_by_id(api_key, args.agent_id)
        if user_id and user_api_key:
            print(f"Displaying messages for user ID {user_id} and agent ID {args.agent_id}:")
            get_messages_by_agent_id(user_api_key, args.agent_id)  # Defaults to start=0, count=10
        else:
            print("No agent found with the provided ID or failed to retrieve messages.")

if __name__ == "__main__":
    main()
