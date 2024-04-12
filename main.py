import logging

# Configure the root logger to log debug information
logging.basicConfig(level=logging.INFO)
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
from ella_memgpt.memgpt_admin import create_memgpt_user_and_api_key, manage_agents

# Import the database management functions from db_manager module
from ella_dbo.db_manager import (
    create_connection,
    create_table,
    get_memgpt_user_id_and_api_key,
    upsert_user,
)
from openai_proxy import router as openai_proxy_router

app.include_router(openai_proxy_router, prefix="/api")

# Add other routes or routers as needed

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
CHATBOT_NAME = "Ella"

from chainlit.context import init_http_context



@app.get("/voice-chat")
async def new_test_page():
    return RedirectResponse(
        url="https://vapi.ai/?demo=true&shareKey=c87ea74e-bebf-4196-aebb-fbd77d5f28c0&assistantId=7d444afe-1c8b-4708-8f45-5b6592e60b47"
    )


@cl.oauth_callback
def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, Any],
    default_user: cl.User,
) -> Optional[cl.User]:
    auth0_user_id = raw_user_data.get("sub", "Unknown ID")
    user_email = raw_user_data.get("email", None)
    user_name = raw_user_data.get("name", None)
    user_roles = raw_user_data.get(
        "https://ella-ai/auth/roles", ["none"]
    )  # Assign 'none' as a default role

    conn = create_connection()
    create_table(conn)
    roles_str = ", ".join(user_roles)
    upsert_user(
        conn,
        auth0_user_id=auth0_user_id,
        roles=roles_str,
        email=user_email,
        name=user_name,
    )

    # Check if the user has a MemGPT user ID and API key
    memgpt_user_id, memgpt_user_api_key = get_memgpt_user_id_and_api_key(conn, auth0_user_id)

   
    # If the user does not have a MemGPT user ID or API key, create them, 
    # we could update this to also just get the api key of the user
    # Assuming you are checking if either ID or key is None and then calling the creation function
    if not memgpt_user_id or not memgpt_user_api_key:
        user_values = create_memgpt_user_and_api_key()  # This will return the dictionary with new keys
        memgpt_user_id = user_values["memgpt_user_id"]  # Extract the user_id from the dictionary
        memgpt_user_api_key = user_values["memgpt_user_api_key"]  # Extract the API key from the dictionary

        # Update the user's MemGPT user ID and API key in the database
        upsert_user(
            conn,
            auth0_user_id=auth0_user_id,
            roles=roles_str,
            email=user_email,
            name=user_name,
            memgpt_user_id=memgpt_user_id,
            memgpt_user_api_key=memgpt_user_api_key,
        )
   
    conn.close()

    # Create the custom user object
    custom_user = cl.User(
        identifier=user_name,
        metadata={
            "auth0_user_id": auth0_user_id,
            "email": user_email,
            "name": user_name,
            "roles": user_roles,
            "memgpt_user_id": memgpt_user_id,
            "memgpt_user_api_key": memgpt_user_api_key,
        }
    )

    return custom_user



@cl.on_chat_start
async def on_chat_start():
    # Attempt to access user details from the cl.User object
    try:
        app_user = cl.user_session.get("user")  # Simulated retrieval of user session
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


# Assuming the guardian_agent_analysis function returns a string (the note) or None
def guardian_agent_analysis(message_content):
    print("Guardian Agent Analysis called.")  # Debugging statement
    if "medication" in message_content.lower():
        note = "Note from staff: Remind user to take their meds since it's been over 24 hours."
        print(f"Guardian note generated: {note}")  # Debugging statement
        return note
    return None


# Assuming the guardian_agent_analysis function returns a string (the note) or None
def guardian_agent_analysis2(message_content):
    print("Guardian Agent Analysis called.")  # Debugging statement
    if "tired" in message_content.lower():
        note = "Note from staff: Remind user to get some exercise and fresh air."
        print(f"Guardian note generated: {note}")  # Debugging statement
        return note
    return None


@cl.on_message
async def on_message(message: cl.Message):
    user_api_key = DEFAULT_API_KEY
    agent_id = DEFAULT_AGENT_ID
    user_api = ExtendedRESTClient(base_url, user_api_key)

    print(f"Received message: {message.content}")  # Debugging statement
    # Call the guardian agent function to analyze the message and potentially add notes
    guardian_note = guardian_agent_analysis2(message.content)

    # Prepare the message for MemGPT, appending the guardian's note if it exists
    message_for_memgpt = message.content
    if guardian_note:
        print(f"Appending staff note to message: {guardian_note}")  # Debugging
        # Use an async step to visualize the staff note addition
        async with cl.Step(name="Adding Staff Note", type="note") as note_step:
            note_step.input = message.content
            note_step.output = guardian_note
            print("Visualizing staff note addition.")  # Debugging statement

        # Append the note to the user's message, ensuring a clear separation
        message_for_memgpt += f"\n\n{guardian_note}"
    else:
        print("No staff note added.")  # Debugging statement

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



