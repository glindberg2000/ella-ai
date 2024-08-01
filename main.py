import logging
# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)



from datetime import datetime, timezone
from typing import Dict, Any
import pytz

import json
import os
import sys

# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import and run setup_env
from setup_env import setup_env
setup_env()

from typing import Any, Dict, Optional

# Your secret key for signing the JWT - keep it secure and do not expose it
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

from chainlit.server import app
import chainlit as cl
from chainlit.user import User
from chainlit.user_session import user_session


from fastapi import HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)

from dotenv import load_dotenv

from ella_memgpt.extendedRESTclient import ExtendedRESTClient
from memgpt.client.admin import Admin as AdminRESTClient
from ella_memgpt.memgpt_admin import create_memgpt_user_and_api_key, manage_agents

from ella_vapi.vapi_client import VAPIClient
from ella_dbo.db_manager import (
    create_connection,
    create_table,
    get_user_data_by_field,
    upsert_user
)


from agent_creation import handle_default_agent, update_custom_tools

debug = True  # Turn on debug mode to see detailed logs

# Load environment variables from .env file
load_dotenv()
BASE_URL = os.getenv("MEMGPT_API_URL", "http://localhost:8283")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")
openai_api_key = os.getenv("OPENAI_API_KEY", "defaultopenaikey")
#default_preset = os.getenv('DEFAULT_PRESET', 'ella_3')

# Define default values
DEFAULT_API_KEY = os.getenv("DEFAULT_API_KEY", "000000")
DEFAULT_AGENT_ID = os.getenv("DEFAULT_AGENT_ID", "000000")

CHATBOT_NAME = "Ella AI"



@app.get("/voice-chat")
async def new_test_page():
    return RedirectResponse(
        url="https://vapi.ai/?demo=true&shareKey=c87ea74e-bebf-4196-aebb-fbd77d5f28c0&assistantId=7d444afe-1c8b-4708-8f45-5b6592e60b47"
    )



def get_phone_from_email(email):
    # Convert the email to a format suitable for environment variable names
    key = 'USER_' + email.replace('@', '_').replace('.', '_') + '_PHONE'
    # Convert the entire key to upper case
    key = key.upper()
    # Log the generated key to help with debugging
    logging.debug(f"Generated environment variable key: {key}")
    phone = os.getenv(key)
    if phone:
        logging.info(f"Phone number retrieved for {email}: {phone}")
    else:
        logging.warning(f"No phone number found for {email} using key {key}")
    return phone


def update_agent_memory(base_url: str, memgpt_user_api_key: str, default_agent_key: str, memgpt_user_id: str):
    """
    Update the agent's core memory with the specified details.

    Parameters:
    - base_url: str, the base URL for the MemGPT REST API.
    - memgpt_user_api_key: str, the API key for authenticating with MemGPT.
    - default_agent_key: str, the key for the agent whose memory is to be updated.
    - memgpt_user_id: str, the user ID to inject into the memory.
    """
    # Initialize the REST client
    user_api = ExtendedRESTClient(base_url, memgpt_user_api_key)

    # Fetch the existing memory
    agent_memory = user_api.get_agent_memory(default_agent_key)
    logging.info(f"Existing Agent Memory: {agent_memory}")

    # Extract core_memory object
    core_memory = agent_memory.core_memory
    existing_human = core_memory.human
    existing_persona = core_memory.persona

    # New data to inject
    user_id = memgpt_user_id
    agent_key = default_agent_key

    # Prepare the new memory contents
    new_memory_contents = {}

    # Check if user_id is already in the human memory
    if f"user_id: {user_id}" not in existing_human:
        new_memory_contents["human"] = f"user_id: {user_id}\n{existing_human}"

    # Check if agent_key is already in the persona memory
    if f"agent_key: {agent_key}" not in existing_persona:
        new_memory_contents["persona"] = f"agent_key: {agent_key}\n{existing_persona}"

    # Update the agent memory with the new memory contents if there are any changes
    if new_memory_contents:
        updated_memory = user_api.update_agent_core_memory(default_agent_key, new_memory_contents)
        logging.info(f"Updated Agent Core Memory: {updated_memory}")
    else:
        logging.info("No changes required for agent memory.")

    update_custom_tools(user_api)

@cl.oauth_callback
async def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, Any],
    default_user: cl.User,
) -> Optional[cl.User]:
    # Extract user info from raw_user_data
    auth0_user_id = raw_user_data.get("sub", "Unknown ID")
    user_email = raw_user_data.get("email", None)
    user_name = raw_user_data.get("name", None)
    user_roles = raw_user_data.get("https://ella-ai/auth/roles", ["none"])
    roles_str = ", ".join(user_roles)

    # Database operations
    conn = create_connection()
    create_table(conn)

    # Retrieve user data including the new fields
    try:
        user_data = get_user_data_by_field(conn, 'auth0_user_id', auth0_user_id)
        if user_data:
            memgpt_user_id = user_data.get('memgpt_user_id', None)
            memgpt_user_api_key = user_data.get('memgpt_user_api_key', None)
            email = user_data.get('email', None)
            phone = user_data.get('phone', None)
            default_agent_key = user_data.get('default_agent_key', None)
            vapi_assistant_id = user_data.get('vapi_assistant_id', None)
            calendar_id = user_data.get('calendar_id', None)
            local_timezone = user_data.get('local_timezone', 'America/Los_Angeles')  # Add this line
        else:
            # Handle the case where no data is found
            print("No user data found for the provided ID")
            memgpt_user_id = None
            memgpt_user_api_key = None
            email = None
            phone = None
            default_agent_key = None
            vapi_assistant_id = None
            calendar_id = None
            local_timezone = 'America/Los_Angeles'  # Add this line, using default value
        
        logging.info(f"Retrieved user data for Auth0 user ID {auth0_user_id}: "
                    f"MemGPT User ID = {memgpt_user_id}, "
                    f"API Key = {memgpt_user_api_key}, "
                    f"Email = {email}, "
                    f"Phone = {phone}, "
                    f"Default Agent Key = {default_agent_key}, "
                    f"VAPI Assistant ID = {vapi_assistant_id}, "
                    f"Calendar ID = {calendar_id}, "
                    f"Local Timezone = {local_timezone}")  # Add this line
    except Exception as e:
        logging.error(f"Failed to retrieve user data for Auth0 user ID {auth0_user_id}: {e}")

    # MemGPT and VAPI Assistant Setup
    if not memgpt_user_id or not memgpt_user_api_key or not vapi_assistant_id or not default_agent_key:
        admin_api = AdminRESTClient(BASE_URL, master_api_key)

        if not memgpt_user_id:
            # Create MemGPT user
            memgpt_user = admin_api.create_user()
            memgpt_user_id = str(memgpt_user.user_id)
            memgpt_user_api_key = memgpt_user.api_key
            logging.info(f"New memgpt user created: {memgpt_user_id}")

        if not memgpt_user_api_key:
            # Create MemGPT API key
            memgpt_user_api_key = admin_api.create_key(memgpt_user_id)
            logging.info(f"New memgpt API key created: {memgpt_user_api_key}")

        if not default_agent_key:
            # Check for default agent
            user_api = ExtendedRESTClient(BASE_URL, memgpt_user_api_key, debug)
            default_agent_key, agent_state = handle_default_agent(memgpt_user_id, user_api)
            logging.info(f"Default agent key: {default_agent_key}")
            
            # Print out the LLM config
            llm_config = agent_state.llm_config
            logging.info(f"LLM Config for agent {default_agent_key}:")
            logging.info(json.dumps(llm_config.__dict__, indent=2))


        if not vapi_assistant_id:
            # Create VAPI Assistant using the VAPIClient and a preset template
            vapi_client = VAPIClient()
            preset_name = 'asteria'  # Example preset name
            customizations = {"serverUrlSecret": str(memgpt_user_api_key)+':'+str(default_agent_key)}
            vapi_assistant_response = await vapi_client.create_assistant(preset_name, customizations)
            vapi_assistant_id = vapi_assistant_response.get('id')  # Extract the 'id' from the response
            await vapi_client.close()
            logging.info(f"VAPI Assistant created with ID: {vapi_assistant_id}")

    # Check and update email and phone if necessary
    if not email and user_email is not None:
        email = user_email
        logging.info(f"Retrieved email from user data: {email}")

    if not phone:  # Check environment variable for a matching email-phone pair
        env_phone = get_phone_from_email(email)  # Assuming environment variables are named after emails
        logging.info(f"Retrieved phone number from environment variable: {env_phone}")
        phone = env_phone if env_phone else None

    # Update the user data in the memgpt core memory to include the user_id for handling calanedars etc. 
    update_agent_memory(BASE_URL, memgpt_user_api_key, default_agent_key, memgpt_user_id)

    try:
        # Log the data before the upsert operation
        logging.info(f"Preparing to upsert data for Auth0 user ID {auth0_user_id}: "
                    f"Roles: {roles_str}, Email: {email}, Phone: {phone}, "
                    f"Name: {user_name}, MemGPT User ID: {memgpt_user_id}, "
                    f"MemGPT API Key: {memgpt_user_api_key}, Default Agent Key: {default_agent_key}, "
                    f"VAPI Assistant ID: {vapi_assistant_id}, Local Timezone: {local_timezone}")
        
        # Upsert the updated user data into the database
        upsert_user(
            conn,
            "auth0_user_id",
            auth0_user_id,
            roles=roles_str,
            email=email,
            phone=phone,
            name=user_name,
            memgpt_user_id=memgpt_user_id,
            memgpt_user_api_key=memgpt_user_api_key,
            default_agent_key=default_agent_key,
            vapi_assistant_id=vapi_assistant_id,
            calendar_id=calendar_id,
            local_timezone=local_timezone  # Add this line
        )
        logging.info("Upsert operation completed successfully.")
    except Exception as e:
        logging.error(f"Database error during upsert: {e}")
    finally:
        conn.close()
        logging.info("Database connection closed.")

        # Create and return the custom user object
        custom_user = cl.User(
            identifier=user_name,
            metadata={
                "auth0_user_id": auth0_user_id,
                "email": email,
                "name": user_name,
                "roles": user_roles,
                "memgpt_user_id": str(memgpt_user_id),
                "memgpt_user_api_key": str(memgpt_user_api_key),
                "default_agent_key": str(default_agent_key),
                "vapi_assistant_id": str(vapi_assistant_id),
                "phone": phone,
                "calendar_id": calendar_id,
                "local_timezone": local_timezone  # Add this line
            }
        )
        return custom_user


@cl.on_chat_start
async def on_chat_start():
    # Attempt to access user details from the cl.User object
    try:
        app_user = cl.user_session.get("user")  #retrieval of user session with chainlit context
        roles = app_user.metadata.get("roles", [])
        # Directly check for 'user' role in user roles
        if "user" not in roles:
            await cl.Message(
                content=f"You must be an valid user to use this chat. Roles detected: {roles}",
                author=CHATBOT_NAME,
            ).send()
            return  # Exit if user is not an admin
    except Exception as e:
        await cl.Message(
            "Authentication error. Please try again.", author=CHATBOT_NAME
        ).send()
        logging.error(f"Authentication check failed: {e}")

    user_name = app_user.metadata.get("name", "Unknown Name")
    phone=app_user.metadata.get("phone", "Unknown Phone")
    user_email = app_user.metadata.get("email", "Unknown Email")
    display_message = f"Successfuly loaded roles: {roles}"
    custom_message = f"Hello {user_name}, {display_message}, Phone number on file: {phone}, Email: {user_email}"

    logging.info({custom_message})

    #await cl.Message(content=custom_message, author=CHATBOT_NAME).send()


# Assuming the guardian_agent_analysis function returns a string (the note) or None,
# TBD: replace with Autogen Teachable Agent with pre prompt hook
def guardian_agent_analysis(message_content):
    logging.info(f"Guardian Agent Analysis called for message: {message_content}")
    if "medication" in message_content.lower():
        note = "Note from staff: Remind user to take their meds since it's been over 24 hours."
        logging.info(f"Guardian note generated: {note}")
        return note
    return None


# Assuming the guardian_agent_analysis function returns a string (the note) or None
def guardian_agent_analysis2(message_content):
    logging.info("guardian_agent_analysis2 called.")  # Debugging statement
    if "tired" in message_content.lower():
        note = "Note from staff: Remind user to get some exercise and fresh air."
        logging.info(f"Guardian note generated: {note}")
        return note
    return None

# Assuming the guardian_agent_analysis function returns a string (the note) or None
def guardian_agent_analysis3(message_content):

    note = '''[Invisible Assistant Reminder: 
    To send a visible message to the user, use the send_message function.
    'send_message' is the ONLY action that sends a notification to the user. The user does not see anything else you do.
    Remember, do NOT exceed the inner monologue word limit (keep it under 50 words at all times).]'''
    logging.info(f"Appended Function Reminder")
    return note



def append_human_memory_updates(message_content, memgpt_user_id):
    """
    Appends human memory updates to the message content.

    Args:
        message_content (str): The original message content.
        memgpt_user_id (str): The user ID.

    Returns:
        str: The message content with appended human memory updates.
    """

    # Define the local timezone for PST
    local_timezone = pytz.timezone('America/Los_Angeles')

    # Get the current time in UTC
    current_time_utc = datetime.utcnow()

    # Convert the UTC time to the local time zone
    current_time_local = current_time_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)

    # Get the current day of the week in local time
    current_day_of_week = current_time_local.strftime('%A')

    human_memory_updates = [
        f"current_time_utc: {current_time_utc.isoformat()}",
        f"current_time_local: {current_time_local.isoformat()}",
        f"current_day_of_week: {current_day_of_week}"
    ]

    print(human_memory_updates)

    separator = "\n\n---\n\n"  # Clear separator to distinguish appended content
    update_header = "# Update human memory\n"
    message_content_with_updates = (
        message_content 
        + separator 
        + update_header 
        + "\n".join(human_memory_updates)
    )
    return message_content_with_updates

# Example usage
# message_content = "This is the original message."
# memgpt_user_id = "user123"

# updated_message_content = append_human_memory_updates(message_content, memgpt_user_id)
# print(updated_message_content)

DEBUG = True  # Set this to False in production

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Check Your Calendar",
            message="Can you show me my schedule for today? I need to see my upcoming meetings, appointments, and tasks.",
            icon="/public/calendar.svg",
        ),
        cl.Starter(
            label="Daily Highlights",
            message="Can you provide me with today's highlights? I'd like to know the main events, important to-dos, and any key updates.",
            icon="/public/highlights.svg",
        ),
        cl.Starter(
            label="Mental Coaching",
            message="I need some mental coaching. Can you give me some tips or exercises to help improve my focus and reduce stress?",
            icon="/public/mental_coach.svg",
        ),
        cl.Starter(
            label="Store Important Information",
            message="I'd like to store some important information. Can you help me save details about words, people, or events that I should remember?",
            icon="/public/store_info.svg",
        ),
    ]

@cl.on_message
async def on_message(message: cl.Message):
    try:
        # Retrieve user data from session
        app_user = cl.user_session.get("user")
        agent_id = app_user.metadata.get("default_agent_key", DEFAULT_AGENT_ID)
        user_api_key = app_user.metadata.get("memgpt_user_api_key", DEFAULT_API_KEY)
        logging.info(f"Retrieved user data from session: {app_user.metadata}")
        
        user_api = ExtendedRESTClient(BASE_URL, user_api_key, DEBUG)
        agent_state = user_api.get_agent(agent_id=agent_id)

        # Print out the LLM config
        llm_config = agent_state.llm_config
        logging.info(f"LLM Config for agent {agent_id} on login:")
        logging.info(json.dumps(llm_config.__dict__, indent=2))
        
        # Analyze message with guardian agent
        guardian_note = guardian_agent_analysis3(message.content)
        message_for_memgpt = message.content

        # Add guardian note if it exists
        if guardian_note:
            guardian_step = cl.Step(name="Adding Staff Note", type="note")
            guardian_step.input = message.content
            guardian_step.output = guardian_note
            await guardian_step.send()
            message_for_memgpt += f"\n\n{guardian_note}"

        message_for_memgpt= append_human_memory_updates(message_for_memgpt, '')

        # Create the main step for the chatbot response
        root_step = cl.Step(name=CHATBOT_NAME, type="llm")
        root_step.input = message_for_memgpt
        await root_step.send()

        assistant_message = ""

        # Stream the response from the MemGPT agent
        async for part in user_api.send_message_to_agent_streamed(agent_id, message_for_memgpt):
            if part.startswith("data: "):
                data_content = part[6:]
                part = json.loads(data_content)

            if "internal_monologue" in part:
                monologue_step = cl.Step(name="Internal Monologue", type="thought")
                monologue_step.output = part["internal_monologue"]
                await monologue_step.send()

            elif "function_call" in part:
                func_call_step = cl.Step(name="Function Call", type="call")
                func_call_step.output = str(part["function_call"])
                await func_call_step.send()

            elif "function_return" in part:
                func_return = f"Function Return: {part.get('function_return', 'No return value')}, Status: {part.get('status', 'No status')}"
                func_return_step = cl.Step(name="Function Return", type="return")
                func_return_step.output = func_return
                await func_return_step.send()

            elif "assistant_message" in part:
                assistant_message += part["assistant_message"]
                await root_step.stream_token(part["assistant_message"])

        root_step.output = assistant_message
        await root_step.update()

        # Send the final message
        await cl.Message(content=assistant_message, author=CHATBOT_NAME).send()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        await cl.Message(
            content="An error occurred while processing your request. Please try again.",
            author=CHATBOT_NAME,
        ).send()