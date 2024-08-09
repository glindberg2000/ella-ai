import os
import re
import logging
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
import httpx
from typing import AsyncGenerator, Dict, Optional, Tuple
import json
import asyncio
from memgpt.client.client import RESTClient
from ella_vapi.vapi_client import VAPIClient
import uuid
from ella_dbo.db_manager import (
    create_connection,
    close_connection,
    get_user_data_by_field
)
from datetime import datetime, timedelta
import time
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


VAPI_API_BASE_URL = os.getenv("VAPI_API_BASE_URL", "https://api.vapi.ai")
VAPI_API_KEY = os.getenv("VAPI_API_KEY")
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

# Initialize MemGPT RESTClient
memgpt_client = RESTClient(base_url=MEMGPT_BASE_URL, token=MEMGPT_TOKEN, debug=True)

# Initialize the VAPIClient
vapi_client = VAPIClient()

def normalize_phone_number(phone_number: str) -> str:
    """Remove all non-digit characters from the phone number."""
    return re.sub(r'\D', '', phone_number)

def mask_api_key(api_key: str) -> str:
    """Mask the API key for safe logging."""
    if api_key:
        return f"{api_key[:4]}...{api_key[-4:]}"
    return None

# In-memory cache for user data
user_cache: Dict[str, Dict] = {}
CACHE_EXPIRY = 3600  # Cache expiry in seconds (1 hour)


@vapi_app.post("/vapi/memgpt/chat/completions")
async def vapi_call_handler(request: Request, x_vapi_secret: Optional[str] = Header(None)):
    logging.info("Entering vapi_call_handler")
    incoming_request_data = await request.json()
    
    call_id = incoming_request_data['call']['id']
    call_type = incoming_request_data['call'].get('type')
    phone_number = incoming_request_data['customer']['number']

    logging.info(f"Call ID: {call_id}, Call Type: {call_type}, Phone: {phone_number}")

    if call_id in user_cache and user_cache[call_id]['expiry'] > time.time():
        cached_data = user_cache[call_id]
        memgpt_user_api_key = cached_data['memgpt_user_api_key']
        default_agent_key = cached_data['default_agent_key']
        logging.info(f"Using cached data for call {call_id}")
    else:
        logging.info(f"Cache miss. Looking up user data for phone number: {phone_number}")
        conn = create_connection()
        user_data = get_user_data_by_field(conn, 'phone', normalize_phone_number(phone_number))
        close_connection(conn)
        
        if not user_data:
            logging.error(f"User data not found for phone number: {phone_number}")
            raise HTTPException(status_code=404, detail="User not found")
        
        memgpt_user_api_key = user_data['memgpt_user_api_key']
        default_agent_key = user_data['default_agent_key']
        
        user_cache[call_id] = {
            'memgpt_user_api_key': memgpt_user_api_key,
            'default_agent_key': default_agent_key,
            'expiry': time.time() + CACHE_EXPIRY
        }
        logging.info(f"Cached user data for call {call_id}")

    try:
        return await process_call(incoming_request_data, memgpt_user_api_key, default_agent_key)
    except Exception as e:
        logging.error(f"Error processing call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing call: {str(e)}")
# Global variables to store ongoing conversations and their last messages
ongoing_conversations: Dict[str, Dict] = {}

async def process_call(request_data: dict, user_api_key: str, agent_id: str):
    logger.info(f"Processing call for Agent ID: {agent_id}")
    
    call_id = request_data['call']['id']
    latest_message = request_data['messages'][-1]['content']
    updated_at = request_data['call']['updatedAt']

    # Update MemGPT client with user-specific data
    global memgpt_client
    memgpt_client = RESTClient(base_url=MEMGPT_BASE_URL, token=user_api_key, debug=True)

    logger.info(f"Preparing to stream response for call ID: {call_id}, Updated At: {updated_at}")

    response = StreamingResponse(
        stream_memgpt_response(agent_id, latest_message, call_id, updated_at),
        media_type="text/event-stream"
    )
    logger.info("Created StreamingResponse object")
    
    return response

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

# Deprecated: Vapi doesn't seem to store metadata for Calls, only Asisstants or Accounts
# async def update_call_metadata(call_id: str, metadata: Dict):
#     try:
#         url = f"{vapi_client.base_url}/call/{call_id}"
#         payload = {
#             "metadata": metadata
#         }
#         headers = await vapi_client.get_headers()
        
#         logging.info(f"Updating call {call_id} metadata")
#         logging.debug(f"Request URL: {url}")
#         logging.debug(f"Request payload: {payload}")
        
#         async with httpx.AsyncClient() as client:
#             response = await client.patch(url, json=payload, headers=headers)
#             response.raise_for_status()
#             logging.info(f"Successfully updated call {call_id} metadata")
#             return response.json()
#     except httpx.HTTPStatusError as e:
#         error_detail = f"HTTP error occurred: {e.response.status_code} {e.response.reason_phrase}"
#         if e.response.text:
#             error_detail += f"\nResponse content: {e.response.text}"
#         logging.error(error_detail)
#         logging.error(f"Request URL: {url}")
#         logging.error(f"Request payload: {payload}")
#         raise HTTPException(status_code=500, detail=f"Failed to update call metadata: {error_detail}")
#     except Exception as e:
#         logging.error(f"Unexpected error updating call metadata: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
# async def update_call_server_url_secret(call_id: str, server_url_secret: str):
#     try:
#         url = f"{vapi_client.base_url}/call/{call_id}"
#         payload = {
#             "serverUrlSecret": server_url_secret
#         }
#         headers = await vapi_client.get_headers()
        
#         logging.info(f"Updating call {call_id} with serverUrlSecret")
#         logging.debug(f"Request URL: {url}")
#         logging.debug(f"Request payload: {payload}")
        
#         async with httpx.AsyncClient() as client:
#             response = await client.patch(url, json=payload, headers=headers)
#             response.raise_for_status()
#             logging.info(f"Successfully updated call {call_id}")
#             return response.json()
#     except httpx.HTTPStatusError as e:
#         error_detail = f"HTTP error occurred: {e.response.status_code} {e.response.reason_phrase}"
#         if e.response.text:
#             error_detail += f"\nResponse content: {e.response.text}"
#         logging.error(error_detail)
#         logging.error(f"Request URL: {url}")
#         logging.error(f"Request payload: {payload}")
#         raise HTTPException(status_code=500, detail=f"Failed to update call: {error_detail}")
#     except Exception as e:
#         logging.error(f"Unexpected error updating call serverUrlSecret: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@vapi_app.get("/vapi/test")
async def test_endpoint():
    return {"message": "Hello, Vapi world!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(vapi_app, host="0.0.0.0", port=9090)

