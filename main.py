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
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)


import chainlit as cl
from chainlit.user import User
from chainlit.user_session import user_session


from ella_memgpt.extendedRESTclient import ExtendedRESTClient
from memgpt.client.admin import Admin as AdminRESTClient
from ella_memgpt.memgpt_admin import create_memgpt_user_and_api_key, manage_agents
from ella_vapi.vapi_client import VAPIClient


# Import the database management functions from db_manager module
from ella_dbo.db_manager import (
    create_connection,
    create_table,
    get_user_data,
    upsert_user
)
#from openai_proxy import router as openai_proxy_router


debug = True  # Turn on debug mode to see detailed logs


#app.include_router(openai_proxy_router, prefix="/api")

# Load environment variables from .env file
load_dotenv()
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8283")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovellms")
openai_api_key = os.getenv("OPENAI_API_KEY", "defaultopenaikey")

# Define default values
DEFAULT_USER_ID = "d48465a1-8153-448d-9115-93fdaae4b290"
DEFAULT_API_KEY = "sk-614ca012fa835acffa3879729c364124eba195fca46b190b"
DEFAULT_AGENT_ID = "31b3722a-ebc1-418a-9056-4ef780d2f494"
DEFAULT_AGENT_CONFIG = {
    "name": "DefaultAgent5",
    "preset": "memgpt_chat",
    "human": "cs_phd",
    "persona": "anna_pa",
}
CHATBOT_NAME = "Ella AI"

# from chainlit.context import init_http_context

from vapi_voice import *
# Mount imported endpoints to the FastAPI app
# app.include_router(vapi_call_handler())
# app.include_router(custom_memgpt_sse_handler())

@app.get("/test")
async def test_endpoint2():
    return {"message": "Hello, world!"}

@app.get("/voice-chat")
async def new_test_page():
    return RedirectResponse(
        url="https://vapi.ai/?demo=true&shareKey=c87ea74e-bebf-4196-aebb-fbd77d5f28c0&assistantId=7d444afe-1c8b-4708-8f45-5b6592e60b47"
    )

def handle_default_agent(memgpt_user_id, user_api):
    logging.info(f"Checking for default agent for user {memgpt_user_id}")
    try:
        agent_info = user_api.list_agents()
        if not agent_info.num_agents:
            logging.info(f"No agents found for user {memgpt_user_id}, creating default agent")
            agent_response = user_api.create_agent()  # This should return an object with an AgentState attribute
            default_agent_key = agent_response.id  # Access attributes directly
            logging.info(f"Created default agent {default_agent_key} for user {memgpt_user_id}")
        else:
            default_agent_key = agent_info.agents[0].id  # Assume agents is a list of objects, not dictionaries
            logging.info(f"Multiple agents found for user {memgpt_user_id}. Selecting first agent found: {default_agent_key}")
        return default_agent_key
    except Exception as e:
        logging.error(f"An error occurred while handling agent data for user {memgpt_user_id}: {e}")
        raise


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
    memgpt_user_id, memgpt_user_api_key, default_agent_key, vapi_assistant_id = get_user_data(conn, auth0_user_id)

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

        if not vapi_assistant_id:
            # Create VAPI Assistant using the VAPIClient and a preset template
            vapi_client = VAPIClient()
            preset_name = 'asteria'  # Example preset name
            customizations = {"serverUrlSecret": str(memgpt_user_api_key)+':'+str(default_agent_key)}
            vapi_assistant_response = await vapi_client.create_assistant(preset_name, customizations)
            vapi_assistant_id = vapi_assistant_response.get('id')  # Extract the 'id' from the response
            await vapi_client.close()
            logging.info(f"VAPI Assistant created with ID: {vapi_assistant_id}")


   # Update the database with new or existing data
    upsert_user(
        conn,
        auth0_user_id=auth0_user_id,
        roles=roles_str,
        email=user_email,
        name=user_name,
        memgpt_user_id=memgpt_user_id,
        memgpt_user_api_key=memgpt_user_api_key,
        default_agent_key=default_agent_key,
        vapi_assistant_id=vapi_assistant_id
    )
    conn.close()

    custom_user = cl.User(
        identifier=user_name,
        metadata={
            "auth0_user_id": auth0_user_id,
            "email": user_email,
            "name": user_name,
            "roles": user_roles,
            "memgpt_user_id": str(memgpt_user_id),  # Ensure this is a string
            "memgpt_user_api_key": str(memgpt_user_api_key),  # Ensure this is a string
            "default_agent_key": str(default_agent_key),  # Ensure this is a string
            "vapi_assistant_id": str(vapi_assistant_id)  # Ensure this is a string
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
    display_message = f"Successfuly loaded roles: {roles}"
    custom_message = f"Hello {user_name}, {display_message}"

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
    user_api_key = DEFAULT_API_KEY
    #agent_id = DEFAULT_AGENT_ID

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



