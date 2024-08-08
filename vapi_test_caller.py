import os
from dotenv import load_dotenv
from ella_vapi.vapi_client import VAPIClient
import asyncio

# Load environment variables
load_dotenv()

async def test_call():
    client = VAPIClient()
    
    # Call details
    assistant_id = "ce5de399-9f8c-4e82-a594-ab5f733026ae"
    customer_number = "+14156402234"
    
    # Example assistant overrides (you can adjust these as needed)
    assistant_overrides = {
        "firstMessage": "Hello, this is a test call from Vapi. How are you today?",
        "recordingEnabled": True,
        "maxDurationSeconds": 300,  # 5 minutes max call duration
        "endCallPhrases": ["end the call", "goodbye", "hang up"]
    }
    
    print(f"Initiating test call to {customer_number}")
    result = await client.start_call(
        name="Vapi API Test Call",
        assistant_id=assistant_id,
        customer_number=customer_number,
        assistant_overrides=assistant_overrides
    )
    
    print("Call initiation result:", result)
    
    if 'id' in result:
        print(f"Call successfully initiated. Call ID: {result['id']}")
        print("The call is now in progress. You should receive it shortly on your phone.")
        print("The call will automatically end after 5 minutes or when you use an end call phrase.")
    else:
        print("Failed to initiate the call. Please check the error details.")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_call())