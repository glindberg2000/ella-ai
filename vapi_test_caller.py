#vapi_test_caller.py
# test_voice_call_manager.py
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Custom path handling
MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
VAPI_TOOLS_PATH = os.getenv('VAPI_TOOLS_PATH')
CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')

if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH or not VAPI_TOOLS_PATH:
    raise EnvironmentError("MEMGPT_TOOLS_PATH or CREDENTIALS_PATH or VAPI_TOOLS_PATH not set in environment variables")

if MEMGPT_TOOLS_PATH not in sys.path:
    sys.path.append(MEMGPT_TOOLS_PATH)
if VAPI_TOOLS_PATH not in sys.path:
    sys.path.append(VAPI_TOOLS_PATH)

from ella_memgpt.tools.voice_call_manager import VoiceCallManager

async def test_voice_call():
    voice_manager = VoiceCallManager()

    # Test user details (you should replace these with actual test data)
    test_user_id = "0c892f2e-fbf0-4fde-b1b1-8c44329652c4"
    test_message = "Hello, this is a test call from the Voice Call Manager. How are you today?"

    print(f"Initiating test call for user ID: {test_user_id}")
    result = await voice_manager.send_voice_call(test_user_id, test_message)
    
    print("Call initiation result:", result)

    if "Call ID:" in result:
        print("The call is now in progress. You should receive it shortly on your phone.")
        print("The call will automatically end after 10 minutes or when you use an end call phrase.")
    else:
        print("Failed to initiate the call. Please check the error details.")

    await voice_manager.close()

if __name__ == "__main__":
    asyncio.run(test_voice_call())

# import os
# from dotenv import load_dotenv
# from ella_vapi.vapi_client import VAPIClient
# import asyncio

# # Load environment variables
# load_dotenv()

# async def test_call():
#     client = VAPIClient()
    
#     # Call details
#     assistant_id = "-"
#     customer_number = "+"
    
#     # Example assistant overrides (you can adjust these as needed)
#     assistant_overrides = {
#         "firstMessage": "Hello, this is a test call from Vapi. How are you today?",
#         "recordingEnabled": True,
#         "maxDurationSeconds": 300,  # 5 minutes max call duration
#         "endCallPhrases": ["end the call", "goodbye", "hang up"]
#     }
    
#     print(f"Initiating test call to {customer_number}")
#     result = await client.start_call(
#         name="Vapi API Test Call",
#         assistant_id=assistant_id,
#         customer_number=customer_number,
#         assistant_overrides=assistant_overrides
#     )
    
#     print("Call initiation result:", result)
    
#     if 'id' in result:
#         print(f"Call successfully initiated. Call ID: {result['id']}")
#         print("The call is now in progress. You should receive it shortly on your phone.")
#         print("The call will automatically end after 5 minutes or when you use an end call phrase.")
#     else:
#         print("Failed to initiate the call. Please check the error details.")
    
#     await client.close()

# if __name__ == "__main__":
#     asyncio.run(test_call())