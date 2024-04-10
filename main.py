import logging

# Configure the root logger to log debug information
logging.basicConfig(level=logging.INFO)
import json
import os
import time
from typing import Any, AsyncGenerator, Dict, Optional

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
from memgpt.client.admin import Admin as AdminRESTClient

import chainlit as cl
from ella_memgpt.extendedRESTclient import ExtendedRESTClient
#from ella_memgpt.memgpt_api import MemGPTAPI
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


@app.get("/hello")
def hello(request: Request):
    print(request.headers)
    return HTMLResponse("Hello World")


# from chainlit.server import app
# from fastapi import Request
# from fastapi.responses import (
#     HTMLResponse,
# )

from chainlit.context import init_http_context

import chainlit as cl


@app.get("/hello2")
async def hello(
    request: Request,
):
    init_http_context()
    await cl.Message(content="Hello World whith context").send()
    return HTMLResponse("Hello World with context")


@app.get("/test-page", response_class=HTMLResponse)
async def test_page(request: Request):
    headers = request.headers
    cookies = request.cookies

    headers_list = "<br>".join([f"{key}: {value}" for key, value in headers.items()])
    cookies_list = "<br>".join([f"{key}: {value}" for key, value in cookies.items()])

    html_content = f"""
    <html>
        <head>
            <title>Test Page</title>
        </head>
        <body>
            <h2>Headers</h2>
            <p>{headers_list}</p>
            <h2>Cookies</h2>
            <p>{cookies_list}</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/new-test-page")
async def new_test_page():
    return FileResponse("public/test_page.html")


@app.get("/voice-chat")
async def new_test_page():
    return RedirectResponse(
        url="https://vapi.ai/?demo=true&shareKey=c87ea74e-bebf-4196-aebb-fbd77d5f28c0&assistantId=7d444afe-1c8b-4708-8f45-5b6592e60b47"
    )


@app.post("/test/post")
async def test_post(request: Request):
    data = await request.json()  # Attempt to read the JSON body of the request
    print("Received POST request with data:", data)  # Log to console

    # Construct a simple response
    response = {
        "status": "success",
        "message": "POST request received.",
        "received_data": data,
    }

    return JSONResponse(content=response)


from fastapi import FastAPI, Request, Response


@app.get("/protected-page", response_class=HTMLResponse)
def protected_page():
    print("trying protected page....")
    try:
        # Attempt to retrieve the Chainlit user session
        app_user = user_session.get("user")
        # app_user = None

        # Print the user session data to the console for debugging
        logger.error(f"User session data: {app_user}")
        print(f"User session data: {app_user}")

        if app_user and "user" in app_user.metadata.get("roles", []):
            # If the user is authenticated and authorized, return a simple HTML page
            return HTMLResponse(
                content=f"""
            <html>
                <head>
                    <title>Protected Page</title>
                </head>
                <body>
                    <h1>Welcome, {app_user.metadata['name']}</h1>
                    <p>This is a protected page.</p>
                </body>
            </html>
            """
            )
        else:
            # User not authorized to access this page
            logger.info("Access denied: User not authorized or session missing.")
            return HTMLResponse(
                content="""
            <html>
                <head>
                    <title>Access Denied</title>
                </head>
                <body>
                    <h1>Access Denied</h1>
                    <p>You must be a valid user to view this page.</p>
                </body>
            </html>
            """,
                status_code=403,
            )
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=401, detail="Authentication error. Please try again."
        )


from datetime import datetime, timedelta
from typing import Dict

import jwt

# Your secret key for signing the JWT - keep it secure and do not expose it
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


def generate_jwt_for_user(user_details: Dict[str, any]) -> str:
    """
    Generates a JWT for an authenticated user with the provided user details.

    :param user_details: A dictionary containing details about the user.
    :return: A JWT as a string.
    """
    # Define the token expiration time (e.g., 24 hours from now)
    expiration_time = datetime.utcnow() + timedelta(hours=24)

    # Define your JWT payload
    payload = {"user_details": user_details, "exp": expiration_time}  # Expiration time

    # Encode the JWT
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


import jwt
from chainlit.user import User
from chainlit.user_session import user_session


def generate_jwt(user: User):
    jwt_secret = SECRET_KEY
    # Additional claims based on the user's profile or permissions
    claims = {
        "sub": user.identifier,
        "name": user.metadata.get("name"),
        "roles": user.metadata.get("roles"),
    }
    token = jwt.encode(claims, jwt_secret, algorithm="HS256")
    # Store the token in the user's session for later validation
    user_session.set("jwt_token", token)
    print("token being set: ", token)
    return token


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

    custom_user = cl.User(
        identifier=user_name,
        metadata={
            "auth0_user_id": auth0_user_id,
            "email": user_email,
            "name": user_name,
            "roles": user_roles,
        },
    )
    # user_session.set(identifier=user_name)

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


async def stream_assistant_messages(
    agent_id: str, message: str, user_api: ExtendedRESTClient
) -> AsyncGenerator[str, None]:
    print("Debug: Inside stream_assistant_messages function")  # Debugging
    async for part in user_api.send_message_to_agent_streamed(agent_id, message):
        print(f"Debug: Received part from memgpt: {part}")  # Debugging
        if part.startswith("data: "):
            data_content = part[6:]  # Extract JSON content from the SSE message
            print(f"Debug: Extracted data content: {data_content}")  # Debugging
            part_dict = json.loads(data_content)  # Convert string to dictionary
            if "assistant_message" in part_dict:
                # Reformat and yield each assistant message maintaining SSE format
                formatted_message = f"data: {json.dumps({'assistant_message': part_dict['assistant_message']})}\n\n"
                print(
                    f"Debug: Yielding formatted message: {formatted_message}"
                )  # Debugging
                yield formatted_message


@app.post("/api/memgpt/chat/completions")
async def custom_llm_openai_sse_handler(request: Request) -> StreamingResponse:
    print("Debug: Endpoint hit /api/memgpt/chat/completions")  # Debugging
    user_api_key = DEFAULT_API_KEY
    agent_id = DEFAULT_AGENT_ID
    request_data = await request.json()
    message = request_data.get("messages", [{}])[-1].get("content", "")
    print(f"Debug: Received message: {message}")  # Debugging

    user_api = ExtendedRESTClient(
        base_url, user_api_key
    )  # Initialize with your actual base_url and user_api_key

    try:
        stream = stream_assistant_messages(agent_id, message, user_api)
        return StreamingResponse(stream, media_type="text/event-stream")
    except Exception as e:
        print(f"Error: {e}")  # Debugging
        raise HTTPException(status_code=500, detail=str(e))


import asyncio
import json


@app.post("/api/dummy/chat/completions")
async def dummy_llm_openai_sse_handler(request: Request):
    request_data = await request.json()
    print("Debug: Endpoint hit /api/dummy/chat/completions")  # Debugging
    print(request_data)

    async def message_stream():
        # First message
        yield f"data: {json.dumps({'assistant_message': 'Processing your request, please hold on.'})}\n\n"
        await asyncio.sleep(0.1)  # Wait for 1 seconds

        # Second message
        yield f"data: {json.dumps({'assistant_message': 'Still working on your request, almost there...'})}\n\n"
        await asyncio.sleep(0.15)  # Wait for 1 more seconds

        # Final message
        yield f"data: {json.dumps({'assistant_message': 'Request processed, thank you for waiting!'})}\n\n"

    return StreamingResponse(message_stream(), media_type="text/event-stream")


# @cl.action_callback("action_button")
# async def on_action(action):
#     await cl.Message(content=f"Executed {action.name} with value {action.value}").send()
#     # Optionally remove the action button from the chatbot user interface
#     await action.remove()

# @cl.on_chat_start
# async def start():
#     # Sending multiple action buttons within a chatbot message
#     actions = [
#         cl.Action(name="action_button_1", value="value_1", description="Click me!"),
#         cl.Action(name="action_button_2", value="value_2", description="Click me too!"),
#         # Add more buttons as needed
#     ]

#     await cl.Message(content="Interact with these action buttons:", actions=actions).send()
