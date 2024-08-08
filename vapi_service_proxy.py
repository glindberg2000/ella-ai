import os
import re
import logging
import hashlib
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from typing import AsyncGenerator, Dict, Optional, Tuple
import json
import asyncio
from memgpt.client.client import RESTClient
import uuid
from ella_dbo.db_manager import (
    create_connection,
    close_connection,
    get_user_data_by_field
)
from datetime import datetime, timedelta
from dateutil import parser


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

vapi_app = FastAPI()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = "https://api.openai.com/v1/chat/completions"

# MemGPT Configuration
MEMGPT_BASE_URL = "http://localhost:8080"
MEMGPT_AGENT_ID = "39efded6-74e6-420a-9aed-151720e97c2e"  # Replace with your actual agent ID
MEMGPT_TOKEN = "sk-8cc1b14f04ea1d13061022ae19648d57340d37b864e29740"  # Replace with your actual token


# Constants for different call types
WEB_CALL = "webCall"
INBOUND_PHONE_CALL = "inboundPhoneCall"
OUTBOUND_PHONE_CALL = "outboundPhoneCall"

# JSON schemas for different call types
WEB_CALL_SCHEMA = {
    "model": str,
    "messages": list,
    "temperature": float,
    "stream": bool,
    "max_tokens": int,
    "call": {
        "id": str,
        "orgId": str,
        "createdAt": str,
        "updatedAt": str,
        "type": str,
        "status": str,
        "assistantId": str,
        "webCallUrl": str
    },
    "metadata": dict
}

PHONE_CALL_SCHEMA = {
    "model": str,
    "messages": list,
    "temperature": float,
    "stream": bool,
    "max_tokens": int,
    "call": {
        "id": str,
        "orgId": str,
        "createdAt": str,
        "updatedAt": str,
        "type": str,
        "status": str,
        "phoneCallProvider": str,
        "phoneCallProviderId": str,
        "phoneCallTransport": str,
        "phoneNumberId": str,
        "assistantId": str,
        "customer": {
            "number": str
        }
    },
    "phoneNumber": {
        "id": str,
        "orgId": str,
        "assistantId": str,
        "number": str,
        "createdAt": str,
        "updatedAt": str,
        "stripeSubscriptionId": str,
        "stripeSubscriptionStatus": str,
        "stripeSubscriptionCurrentPeriodStart": str,
        "name": str,
        "provider": str
    },
    "customer": {
        "number": str
    },
    "metadata": dict
}

# Note: The outbound phone call schema is similar to the inbound one in the provided samples

# Initialize MemGPT RESTClient
memgpt_client = RESTClient(base_url=MEMGPT_BASE_URL, token=MEMGPT_TOKEN, debug=True)

# async def extract_request_data(request: Request) -> Tuple[Optional[str], Optional[str], Optional[str], str, str]:
#     incoming_request_data = await request.json()
#     logger.info(f'Full incoming request data: {json.dumps(incoming_request_data, indent=4)}')

#     server_url_secret = None
#     user_api_key = None
#     default_agent_id = None

#     try:
#         server_url_secret = incoming_request_data['call']['serverUrlSecret']
#         user_api_key, default_agent_id = server_url_secret.split(':')
#         logger.info(f'Extracted user API key: {user_api_key} and default agent ID: {default_agent_id}')
#     except (KeyError, ValueError) as e:
#         logger.warning(f"Failed to extract serverUrlSecret: {str(e)}")

#     try:
#         latest_message = incoming_request_data['messages'][-1]['content']
#     except (KeyError, IndexError, TypeError) as e:
#         logger.error("Failed to extract the latest message due to improper data structure.")
#         raise HTTPException(status_code=400, detail=f"Error in message data: {str(e)}")

#     try:
#         call_id = incoming_request_data['call']['callId']
#         truncated_messages = incoming_request_data['messages'][:0]
#         message_content = ''.join(msg['content'] for msg in truncated_messages)
#         unique_hash = hashlib.sha256(message_content.encode()).hexdigest()
#     except KeyError:
#         logger.warning("Failed to generate unique hash due to missing callId or messages.")
#         unique_hash = str(uuid.uuid4())  # Fallback to a random UUID

#     # Extract and log the incoming phone number
#     try:
#         phone_number = incoming_request_data['call']['from']
#         logger.info(f'Incoming phone number: {phone_number}')
#     except KeyError:
#         logger.warning("Incoming phone number not found in the request data.")

#     return server_url_secret, user_api_key, default_agent_id, latest_message, unique_hash


def normalize_phone_number(phone_number: str) -> str:
    """Remove all non-digit characters from the phone number."""
    return re.sub(r'\D', '', phone_number)

def mask_api_key(api_key: str) -> str:
    """Mask the API key for safe logging."""
    if api_key:
        return f"{api_key[:4]}...{api_key[-4:]}"
    return None

async def extract_request_data(request: Request):
    incoming_request_data = await request.json()
    logger.info(f'Full incoming request data: {json.dumps(incoming_request_data, indent=4)}')

    call_type = incoming_request_data['call']['type']
    user_data = None

    try:
        if call_type == WEB_CALL:
            # For web calls, we need to handle the serverUrlSecret differently
            # This might be passed in the metadata or through a different mechanism
            logger.warning("Web call detected. serverUrlSecret handling needs to be implemented.")
            return None, None, None, None, None
        elif call_type in [INBOUND_PHONE_CALL, OUTBOUND_PHONE_CALL]:
            phone_number = incoming_request_data['customer']['number']
            normalized_phone = normalize_phone_number(phone_number)
            
            conn = create_connection()
            try:
                user_data = get_user_data_by_field(conn, 'phone', normalized_phone)
                if not user_data:
                    # If not found, try with the original format
                    user_data = get_user_data_by_field(conn, 'phone', phone_number)
            finally:
                close_connection(conn)

        if not user_data:
            logger.warning(f"User data not found for call type: {call_type}, phone: {phone_number}")
            return None, None, None, None, None

        # Log the user API key (masked) and default agent ID
        masked_api_key = mask_api_key(user_data['memgpt_user_api_key'])
        logger.info(f"Found user data - API Key: {masked_api_key}, Default Agent ID: {user_data['default_agent_key']}")

        latest_message = incoming_request_data['messages'][-1]['content']
        
        # Generate a unique hash for the conversation
        call_id = incoming_request_data['call']['id']
        truncated_messages = incoming_request_data['messages'][:5]  # Use first 5 messages for hash
        message_content = ''.join(msg['content'] for msg in truncated_messages)
        unique_hash = hashlib.sha256(f"{call_id}{message_content}".encode()).hexdigest()

        return (
            user_data['memgpt_user_api_key'],
            user_data['default_agent_key'],
            user_data['vapi_assistant_id'],
            latest_message,
            unique_hash
        )
    except Exception as e:
        logger.error(f"Error in extract_request_data: {str(e)}")
        return None, None, None, None, None
        

async def stream_openai_response(messages: list) -> AsyncGenerator[str, None]:
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            OPENAI_API_BASE,
            json={
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "stream": True,
            },
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=None,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line + "\n\n"




# Global variables to store ongoing conversations and their last messages
ongoing_conversations: Dict[str, Dict] = {}

async def stream_memgpt_response(agent_id: str, message: str, call_id: str, updated_at: str) -> AsyncGenerator[str, None]:
    global ongoing_conversations
    logger.info(f"Starting stream_memgpt_response for call ID: {call_id}")
    
    current_time = datetime.now()

    # Check if this is an ongoing conversation
    if call_id in ongoing_conversations:
        conversation = ongoing_conversations[call_id]
        if message == conversation['last_message']:
            # This is a repeat of the last message, likely due to a reconnection
            logger.info(f"Repeat message detected for call ID: {call_id}")
            for chunk in conversation['last_response']:
                yield chunk
            return
        else:
            # This is a new message in an ongoing conversation
            logger.info(f"New message in ongoing conversation for call ID: {call_id}")
    else:
        # This is a new conversation
        logger.info(f"New conversation started for call ID: {call_id}")
        ongoing_conversations[call_id] = {'last_message': '', 'last_response': [], 'timestamp': current_time}

    try:
        logger.info(f"Sending user message to MemGPT for agent ID: {agent_id}")
        response = memgpt_client.user_message(agent_id, message)
        
        logger.info("Received response from MemGPT. Processing message.")
        full_content = ""
        stored_response = []

        for chunk in response.messages:
            logger.info(f"Processing chunk: {chunk}")
            
            if isinstance(chunk, dict) and 'function_call' in chunk:
                if chunk['function_call']['name'] == 'send_message':
                    try:
                        content = json.loads(chunk['function_call']['arguments'])['message']
                        full_content += content
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(f"Error processing chunk: {e}")

        if full_content:
            logger.info(f"Extracted full content: {full_content[:100]}...")  # Log first 100 chars
            response_chunk = f"data: {json.dumps({'choices': [{'delta': {'content': full_content}}]})}\n\n"
            stored_response.append(response_chunk)
            yield response_chunk

        done_chunk = "data: [DONE]\n\n"
        stored_response.append(done_chunk)
        yield done_chunk
        logger.info("Sent [DONE] signal")

        # Update the conversation record
        ongoing_conversations[call_id] = {
            'last_message': message,
            'last_response': stored_response,
            'timestamp': current_time
        }

        # Clean up old conversations (e.g., conversations inactive for more than 1 hour)
        ongoing_conversations = {k: v for k, v in ongoing_conversations.items() 
                                 if current_time - v['timestamp'] < timedelta(hours=1)}
    
    except Exception as e:
        logger.error(f"Error in stream_memgpt_response: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    logger.info(f"Exiting stream_memgpt_response for call ID: {call_id}")


@vapi_app.get("/vapi/test")
async def test_endpoint():
    return {"message": "Hello, Vapi world!"}

# @vapi_app.post("/vapi/memgpt/chat/completions")
# async def chat_completions(request: Request):
#     try:
#         _, _, _, latest_message, _ = await extract_request_data(request)
#         return StreamingResponse(
#             stream_memgpt_response(latest_message),
#             media_type="text/event-stream"
#         )
#     except Exception as e:
#         logger.error(f"Error in chat_completions: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

@vapi_app.post("/vapi/memgpt/chat/completions")
async def chat_completions(request: Request):
    logger.info("Entering chat_completions endpoint")
    try:
        incoming_request_data = await request.json()
        logger.info(f"Received request data: {json.dumps(incoming_request_data, indent=2)}")
        
        user_api_key, default_agent_id, vapi_assistant_id, latest_message, unique_hash = await extract_request_data(request)
        logger.info(f"Extracted request data - Agent ID: {default_agent_id}, Message: {latest_message[:50]}...")
        
        if not user_api_key or not default_agent_id:
            error_message = "Unable to identify user or retrieve necessary data"
            logger.error(error_message)
            raise HTTPException(status_code=400, detail=error_message)

        logger.info(f"Initializing MemGPT client for user with default agent ID: {default_agent_id}")
        
        # Update MemGPT client with user-specific data
        global memgpt_client
        memgpt_client = RESTClient(base_url=MEMGPT_BASE_URL, token=user_api_key, debug=True)

        call_id = incoming_request_data['call']['id']
        updated_at = incoming_request_data['call']['updatedAt']

        logger.info(f"Preparing to stream response for call ID: {call_id}, Updated At: {updated_at}")

        response = StreamingResponse(
            stream_memgpt_response(default_agent_id, latest_message, call_id, updated_at),
            media_type="text/event-stream"
        )
        logger.info("Created StreamingResponse object")
        
        return response

    except HTTPException as he:
        logger.error(f"HTTP exception in chat_completions: {str(he)}")
        raise
    except Exception as e:
        error_message = f"Unexpected error in chat_completions: {str(e)}"
        logger.error(error_message, exc_info=True)
        raise HTTPException(status_code=500, detail=error_message)
    finally:
        logger.info("Exiting chat_completions endpoint")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(vapi_app, host="0.0.0.0", port=9090)


# import os
# import logging
# import hashlib
# from fastapi import FastAPI, Request, HTTPException
# from fastapi.responses import StreamingResponse
# import httpx
# from typing import AsyncGenerator, Tuple, Optional
# import json
# import asyncio
# from memgpt.client.client import RESTClient
# import uuid

# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# vapi_app = FastAPI()

# # OpenAI Configuration
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OPENAI_API_BASE = "https://api.openai.com/v1/chat/completions"

# # MemGPT Configuration
# MEMGPT_BASE_URL = "http://localhost:8080"
# MEMGPT_AGENT_ID = "39efded6-74e6-420a-9aed-151720e97c2e"  # Replace with your actual agent ID
# MEMGPT_TOKEN = "sk-8cc1b14f04ea1d13061022ae19648d57340d37b864e29740"  # Replace with your actual token

# # Initialize MemGPT RESTClient
# memgpt_client = RESTClient(base_url=MEMGPT_BASE_URL, token=MEMGPT_TOKEN, debug=True)

# async def extract_request_data(request: Request) -> Tuple[Optional[str], Optional[str], Optional[str], str, str]:
#     incoming_request_data = await request.json()
#     logger.info(f'Full incoming request data: {incoming_request_data}')

#     server_url_secret = None
#     user_api_key = None
#     default_agent_id = None

#     try:
#         server_url_secret = incoming_request_data['call']['serverUrlSecret']
#         user_api_key, default_agent_id = server_url_secret.split(':')
#         logger.info(f'Extracted user API key: {user_api_key} and default agent ID: {default_agent_id}')
#     except (KeyError, ValueError) as e:
#         logger.warning(f"Failed to extract serverUrlSecret: {str(e)}")

#     try:
#         latest_message = incoming_request_data['messages'][-1]['content']
#     except (KeyError, IndexError, TypeError) as e:
#         logger.error("Failed to extract the latest message due to improper data structure.")
#         raise HTTPException(status_code=400, detail=f"Error in message data: {str(e)}")

#     try:
#         call_id = incoming_request_data['call']['callId']
#         truncated_messages = incoming_request_data['messages'][:0]
#         message_content = ''.join(msg['content'] for msg in truncated_messages)
#         unique_hash = hashlib.sha256(message_content.encode()).hexdigest()
#     except KeyError:
#         logger.warning("Failed to generate unique hash due to missing callId or messages.")
#         unique_hash = str(uuid.uuid4())  # Fallback to a random UUID

#     return server_url_secret, user_api_key, default_agent_id, latest_message, unique_hash

# async def stream_openai_response(messages: list) -> AsyncGenerator[str, None]:
#     async with httpx.AsyncClient() as client:
#         async with client.stream(
#             "POST",
#             OPENAI_API_BASE,
#             json={
#                 "model": "gpt-3.5-turbo",
#                 "messages": messages,
#                 "stream": True,
#             },
#             headers={
#                 "Authorization": f"Bearer {OPENAI_API_KEY}",
#                 "Content-Type": "application/json",
#             },
#             timeout=None,
#         ) as response:
#             async for line in response.aiter_lines():
#                 if line.startswith("data: "):
#                     yield line + "\n\n"

# async def stream_memgpt_response(message: str) -> AsyncGenerator[str, None]:
#     try:
#         response = memgpt_client.user_message(MEMGPT_AGENT_ID, message)
#         for chunk in response.messages:
#             if isinstance(chunk, dict) and 'function_call' in chunk:
#                 if chunk['function_call']['name'] == 'send_message':
#                     content = json.loads(chunk['function_call']['arguments'])['message']
#                     yield f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}\n\n"
#         yield "data: [DONE]\n\n"
#     except Exception as e:
#         logger.error(f"Error in stream_memgpt_response: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @vapi_app.get("/vapi/test")
# async def test_endpoint():
#     return {"message": "Hello, Vapi world!"}

# @vapi_app.post("/vapi/memgpt/chat/completions")
# async def chat_completions(request: Request):
#     try:
#         _, _, _, latest_message, _ = await extract_request_data(request)
#         return StreamingResponse(
#             stream_memgpt_response(latest_message),
#             media_type="text/event-stream"
#         )
#     except Exception as e:
#         logger.error(f"Error in chat_completions: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(vapi_app, host="0.0.0.0", port=9090)