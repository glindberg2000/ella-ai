
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

# Import necessary modules from Zep Python SDK and ChainLit.
from zep_python import ZepClient
from zep_python.memory import Memory, Session
from zep_python.message import Message
from zep_python.user import CreateUserRequest
import chainlit as cl
import uuid
import os
from openai import AsyncOpenAI
import logging


# Retrieve API keys from environment variables.
ZEP_API_KEY = os.environ.get("ZEP_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize clients for OpenAI GPT-4 and Zep with respective API keys.
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
zep = ZepClient(api_key=ZEP_API_KEY)
# Get all attributes of the module

# Import the database management functions from db_manager module
from ella_dbo.db_manager import (
    create_connection,
    create_table,
    get_user_data,
    upsert_user
)
from openai_proxy import router as openai_proxy_router


debug = True  # Turn on debug mode to see detailed logs
# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app.include_router(openai_proxy_router, prefix="/api")

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

from chainlit.context import init_http_context



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




async def check_and_register_user_in_zep(client: ZepClient, user_id: str, session_id: str, user_details, metadata={}):
    """
    Check if a user and session exist before creating new ones.
    """
    try:
        # Check if the user already exists (without using 'await' if method isn't asynchronous)
        user = client.user.get(user_id)  # Ensure this is a synchronous call

        if user:
            # If the user exists, check if the session exists
            sessions = client.memory.list_sessions(limit=10, cursor=0)  # Non-asynchronous
            session_exists = any(s.session_id == session_id for s in sessions)

            if session_exists:
                return f"Session {session_id} already exists for user {user_id}."

            # Create a new session if it doesn't exist
            new_session = Session(
                session_id=session_id,
                user_id=user_id,
                metadata=metadata,
            )
            client.memory.add_session(new_session)
            return f"Session {session_id} created for user {user_id}."

    except Exception as e:
        if "not found" in str(e).lower():
            # If the user doesn't exist, create them
            user_request = CreateUserRequest(
                user_id=user_id,
                email=user_details["email"],
                first_name=user_details["first_name"],
                last_name=user_details["last_name"],
                metadata=metadata,
            )
            client.user.add(user_request)  # Ensure this is a synchronous call

            # Create a new session for the newly created user
            new_session = Session(
                session_id=session_id,
                user_id=user_id,
                metadata=metadata,
            )
            client.memory.add_session(new_session)
            return f"New user {user_id} created, and session {session_id} started."

        # Handle other exceptions
        logging.error(f"Error creating user or session: {e}")
        raise e


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

    ##ZEP##
    """Handles the event triggered at the start of a new chat through ChainLit."""
    try:
        # Retrieve user details from the current session
        user_id = app_user.metadata.get("memgpt_user_id")
        #session_id = str(uuid.uuid4())  # Create a unique session ID
        session_id = app_user.metadata.get("default_agent_key")

        # Check if the user exists in Zep and register a new session
        result_message = await check_and_register_user_in_zep(zep, user_id, session_id, user_name, {'metadata':'info'})

        # Save user and session identifiers in the current session context
        cl.user_session.set("session_id", session_id)

        await cl.Message(content=result_message, author="Chatbot").send()

    except Exception as e:
        await cl.Message(
            content=f"Error initializing chat: {e}",
            author="Guardian",
        ).send()


@cl.step(name="session classification", type="tool")
async def classify_session(session_id: str):
    if not session_id:
        raise ValueError("Session ID must be provided.")

    classes = ["General", "Travel", "Shopping", "Cars"]

    try:
        # Attempt classification
        classification = await zep.memory.aclassify_session(
            session_id, "session_classification", classes, persist=True,
            instruction="Helpful assistant..."
        )
        return classification
    except Exception as e:
        # Log the error and return a default value or None
        logging.error(f"Error classifying session: {e}")
        return None



@cl.step(name="OpenAI", type="llm")
async def call_openai(session_id):
    """Invokes the OpenAI API to generate a response based on the  session message history."""
    # Fetch session messages from Zep.
    memory = await zep.message.aget_session_messages(session_id)
    memory_history = [m.to_dict() for m in memory]
    
    # Prepare data, excluding certain fields for privacy/security.
    cleaned_data = [{k: v for k, v in item.items() if k not in ['created_at', 'role_type', 'token_count', 'uuid']} for item in memory_history]
    
    logging.info('cleaned data for openai: %s', cleaned_data)
    # Generate a response from OpenAI using the cleaned session data.

    response = await openai_client.chat.completions.create(
        model="gpt-4",
        temperature=0.1,
        messages=cleaned_data,
    )
    return response.choices[0].message


@cl.on_message
async def on_message(message: cl.Message):
    try:
        # Retrieve session ID
        session_id = cl.user_session.get("session_id")
        if not session_id:
            raise ValueError("Session ID must be provided in cl user_session.")

        # Initialize classify_sess
        classify_sess = await classify_session(session_id)
        
        # Check if classification was successful
        if not classify_sess:
            raise ValueError("Classification failed.")

        # Store the incoming message in Zep's session memory with the classified dialog
        await zep.memory.aadd_memory(
            session_id,
            Memory(messages=[Message(
                role_type="user",
                content=message.content + "\n" + "conversation_topic: " + (classify_sess.class_ if classify_sess else "Unknown"),
                role="user"
            )]),
        )

        # Retrieve a response from the OpenAI model.
        response_message = await call_openai(session_id)
        logging.info(f"response.content from openai: %s", response_message.content)
        logging.info(f"response from openai: %s", response_message)
        logging.info(f"session_id: %s", session_id)
        # Send the generated response back through ChainLit.
        msg = cl.Message(author="Answer", content=(response_message.content))
        await msg.send()
        logging.info(f"session_id after msg.send(): %s", session_id)
        # Update Zep's session memory with the assistant's response for continuity.
        await zep.memory.aadd_memory(
            session_id,
            Memory(messages=[Message(role_type="assistant", content=response_message.content, role="assistant")]),
        )

    except Exception as e:
        # Handle errors and inform the user
        await cl.Message(
            content=f"An error occurred: {e}",
            author="Chatbot",
        ).send()
