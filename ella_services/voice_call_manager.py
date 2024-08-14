# voice_call_manager.py
import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Custom path handling
MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
VAPI_TOOLS_PATH = os.getenv('VAPI_TOOLS_PATH')
CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')

if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH or not VAPI_TOOLS_PATH:
    logger.error("Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH or VAPI_TOOLS_PATH not set in environment variables")
    raise EnvironmentError("Required environment variables are not set")

logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
logger.debug(f"VAPI_TOOLS_PATH: {VAPI_TOOLS_PATH}")
logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

if MEMGPT_TOOLS_PATH not in sys.path:
    sys.path.append(MEMGPT_TOOLS_PATH)
if VAPI_TOOLS_PATH not in sys.path:
    sys.path.append(VAPI_TOOLS_PATH)

# Now we can import our custom modules
from google_utils import UserDataManager
from vapi_client import VAPIClient

class VoiceCallManager:
    def __init__(self):
        self.client = VAPIClient()

    async def send_voice_call(self, user_id: str, body: str) -> str:
        try:
            user_data = UserDataManager.get_user_data(user_id)
            recipient_phone = user_data.get('phone')
            if not recipient_phone:
                return "Error: No valid recipient phone number available."

            assistant_id = user_data.get('vapi_assistant_id') or os.getenv('VAPI_DEFAULT_ASSISTANT_ID')
            if not assistant_id:
                return "Error: No assistant ID found and no default set in environment variables."

            assistant_overrides = {
                "firstMessage": body,
                "recordingEnabled": True,
                "maxDurationSeconds": 600,  # 10 minutes max call duration
                "endCallPhrases": ["end the call", "goodbye", "hang up"]
            }

            result = await self.client.start_call(
                name="Assistant Outbound Call",
                assistant_id=assistant_id,
                customer_number=recipient_phone,
                assistant_overrides=assistant_overrides
            )

            if 'id' in result:
                logger.info(f"Voice call successfully initiated. Call ID: {result['id']}")
                return f"Voice call successfully initiated. Call ID: {result['id']}"
            else:
                logger.error(f"Failed to initiate voice call: {result}")
                return f"Error: Voice call failed to initiate. Details: {result}"

        except Exception as e:
            logger.error(f"Error in send_voice_call: {str(e)}", exc_info=True)
            return f"Error initiating voice call: {str(e)}"

    async def close(self):
        await self.client.close()