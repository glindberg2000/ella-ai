import logging
# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

import json
import os
from typing import Any, AsyncGenerator, Dict, Optional
import jwt
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
    get_user_data,
    upsert_user
)

debug = True  # Turn on debug mode to see detailed logs

# Load environment variables from .env file
load_dotenv()
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8283")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")
openai_api_key = os.getenv("OPENAI_API_KEY", "defaultopenaikey")
default_preset = os.getenv('DEFAULT_PRESET', 'ella_3')

# Define default values
DEFAULT_API_KEY = os.getenv("DEFAULT_API_KEY", "000000")
DEFAULT_AGENT_ID = os.getenv("DEFAULT_AGENT_ID", "000000")

CHATBOT_NAME = "Ella AI"

# from chainlit.context import init_http_context


# @app.get("/test")
# async def test_endpoint2():
#     return {"message": "Hello, world!"}

@app.get("/voice-chat")
async def new_test_page():
    return RedirectResponse(
        url="https://vapi.ai/?demo=true&shareKey=c87ea74e-bebf-4196-aebb-fbd77d5f28c0&assistantId=7d444afe-1c8b-4708-8f45-5b6592e60b47"
    )


def read_file_contents(file_path: str) -> str:
    """
    Read the contents of a file given its full path.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None

def handle_default_agent(memgpt_user_id, user_api):
    logging.info(f"Checking for default agent for user {memgpt_user_id}")
    try:
        agent_info = user_api.list_agents()
        if not agent_info.num_agents:
            logging.info(f"No agents found for user {memgpt_user_id}, creating default agent")

            # Read the contents of the persona and human templates
            base_dir = os.path.expanduser("~/.memgpt")
            human_content = read_file_contents(os.path.join(base_dir, "humans", "plato.txt"))
            persona_content = read_file_contents(os.path.join(base_dir, "personas", "ella_persona.txt"))

            if human_content is None or persona_content is None:
                logging.error("Failed to read human or persona files.")
                raise FileNotFoundError("Required template files are missing.")

            # Create an agent with the contents of the templates
            agent_response = user_api.create_agent(preset=default_preset, human=human_content, persona=persona_content)
            default_agent_key = agent_response.id
            logging.info(f"Created default agent {default_agent_key} for user {memgpt_user_id}")
        else:
            default_agent_key = agent_info.agents[0].id
            logging.info(f"Multiple agents found for user {memgpt_user_id}. Selecting first agent found: {default_agent_key}")
        return default_agent_key
    except Exception as e:
        logging.error(f"An error occurred while handling agent data for user {memgpt_user_id}: {e}")
        raise



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
        memgpt_user_id, memgpt_user_api_key, email, phone, default_agent_key, vapi_assistant_id = get_user_data(conn, auth0_user_id)
        logging.info(f"Retrieved user data for Auth0 user ID {auth0_user_id}: MemGPT User ID = {memgpt_user_id}, API Key = {memgpt_user_api_key}, Email = {email}, Phone = {phone}, Default Agent Key = {default_agent_key}, VAPI Assistant ID = {vapi_assistant_id}")
    except Exception as e:
        logging.error(f"Failed to retrieve user data for Auth0 user ID {auth0_user_id}: {e}")



    # MemGPT and VAPI Assistant Setup
    if not memgpt_user_id or not memgpt_user_api_key or not vapi_assistant_id:
        admin_api = AdminRESTClient(base_url, master_api_key)

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
            user_api = ExtendedRESTClient(base_url, memgpt_user_api_key, debug)
            default_agent_key = handle_default_agent(memgpt_user_id, user_api)
            logging.info(f"Default agent key: {default_agent_key}")

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

    # Update the user data in the memgpt core memory
    update_agent_memory(base_url, memgpt_user_api_key, default_agent_key, memgpt_user_id)

    try:
        # Log the data before the upsert operation
        logging.info(f"Preparing to upsert data for Auth0 user ID {auth0_user_id}: "
                    f"Roles: {roles_str}, Email: {email}, Phone: {phone}, "
                    f"Name: {user_name}, MemGPT User ID: {memgpt_user_id}, "
                    f"MemGPT API Key: {memgpt_user_api_key}, Default Agent Key: {default_agent_key}, "
                    f"VAPI Assistant ID: {vapi_assistant_id}")

        # Upsert the updated user data into the database
        upsert_user(
            conn,
            auth0_user_id=auth0_user_id,
            roles=roles_str,
            email=email,
            phone=phone,
            name=user_name,
            memgpt_user_id=memgpt_user_id,
            memgpt_user_api_key=memgpt_user_api_key,
            default_agent_key=default_agent_key,
            vapi_assistant_id=vapi_assistant_id
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
                "phone": phone  # Added phone to metadata if you want to include it
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

    await cl.Message(content=custom_message, author=CHATBOT_NAME).send()


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


@cl.on_message
async def on_message(message: cl.Message):

    # Attempt to access user details from the cl.User object
    try:
        app_user = cl.user_session.get("user")  #retrieval of user session with chainlit context
        agent_id = app_user.metadata.get("default_agent_key", DEFAULT_AGENT_ID)
        user_api_key = app_user.metadata.get("memgpt_user_api_key", DEFAULT_API_KEY)
        logging.info(f"Retrieved user data from session: {app_user.metadata}")
    except Exception as e:
        logging.error(f"Failed to retrieve user data from session: {e}")
        await cl.Message(
            content="An error occurred while processing your request. Please try again.",
            author=CHATBOT_NAME,
        ).send()
        return

    user_api = ExtendedRESTClient(base_url, user_api_key, debug)

    logging.info(f"Received message from user {message.author} with content: {message.content}")
    # Call the guardian agent function to analyze the message and potentially add notes
    guardian_note = guardian_agent_analysis2(message.content)

    # Prepare the message for MemGPT, appending the guardian's note if it exists
    message_for_memgpt = message.content
    if guardian_note:
        logging.info(f"Appending staff note to message: {guardian_note}")
        # Use an async step to visualize the staff note addition
        async with cl.Step(name="Adding Staff Note", type="note") as note_step:
            note_step.input = message.content
            note_step.output = guardian_note
            logging.info("Finished appending staff note addition.")  # Debugging statement

        # Append the note to the user's message, ensuring a clear separation
        message_for_memgpt += f"\n\n{guardian_note}"
    else:
        logging.info("No staff note added.")  # Debugging statement

    # Send the message to the MemGPT agent
    async with cl.Step(name=CHATBOT_NAME, type="llm", root=True) as root_step:
        root_step.input = message.content
        assistant_message = ""
        # Adjusted to pass the modified message content, now including the staff note
        async for part in user_api.send_message_to_agent_streamed(
            agent_id, message_for_memgpt
        ):
            if part.startswith("data: "):
                data_content = part[6:]  # Extract JSON content
                part = json.loads(data_content)  # Now part is a dictionary
                if "internal_monologue" in part:
                    monologue = part["internal_monologue"]
                    async with cl.Step(
                        name="Internal Monologue", type="thought"
                    ) as monologue_step:
                        monologue_step.output = monologue
                elif "function_call" in part:
                    func_call = part["function_call"]
                    async with cl.Step(
                        name="Function Call", type="call"
                    ) as func_call_step:
                        func_call_step.output = func_call
                elif "function_return" in part:
                    func_return = f"Function Return: {part.get('function_return', 'No return value')}, Status: {part.get('status', 'No status')}"
                    async with cl.Step(
                        name="Function Return", type="return"
                    ) as func_return_step:
                        func_return_step.output = func_return
                elif "assistant_message" in part:
                    assistant_message += part["assistant_message"]
                    async with cl.Step(
                        name="Assistant Response", type="output"
                    ) as assistant_step:
                        assistant_step.output = assistant_message

            root_step.output = assistant_message



