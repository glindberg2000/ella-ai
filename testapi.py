from dotenv import load_dotenv
import os
import requests
import pprint
import json


# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CUSTOM_API_KEY = "dummykey" #os.getenv('CUSTOM_API_KEY')
CUSTOM_API_URL = "https://chat.ella-ai-care.com/api/dummy-model/chat/completions" #os.getenv('CUSTOM_API_URL')
# The URL of your endpoint
#openaipassurl = "https://chat.ella-ai-care.com/api/openai/chat/completions"
openaipassurl = "https://chat.ella-ai-care.com/openai-sse/chat/completions"

#openaipassurl = "http://localhost:5000/api/custom-llm/openai-sse/chat/completions"




mock_vapi_request = {
    "model": "gpt-3.5-turbo",
    "messages": [
        {
            "role": "system",
            "content": "This is a test Api call. have a test conversation with the user."
        },
        {
            "role": "assistant",
            "content": "Hello. This is VAPI Test."
        },
        {
            "role": "user",
            "content": "This is a test."
        }
    ],
    "temperature": 0.7,
    "stream": True,
    "max_tokens": 250,
    "call": {
        "type": "webCall",
        "callId": "c4f10969-e2aa-4e9e-b405-8f608db9df26",
        "orgId": "e3436eb8-00c6-4f36-ba42-b97895803bfa",
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "keywords": [],
            "language": "en"
        },
        "model": {
            "provider": "custom-llm",
            "url": "https://chat.ella-ai-care.com/api/dummy-model",
            "urlRequestMetadataEnabled": True,
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "maxTokens": 250,
            "functions": [],
            "messages": [
                {
                    "role": "system",
                    "content": "This is a test Api call. have a test conversation with the user."
                }
            ],
            "systemPrompt": ""
        },
        "voice": {
            "provider": "playht",
            "voiceId": "s3://voice-cloning-zero-shot/801a663f-efd0-4254-98d0-5c175514c3e8/jennifer/manifest.json"
        },
        "credentials": [],
        "serverUrl": "",
        "serverUrlSecret": "",
        "firstMessage": "Hello this is VAPI test",
        "endCallMessage": "",
        "endCallPhrases": [],
        "recordingEnabled": True,
        "endCallFunctionEnabled": False,
        "fillersEnabled": False,
        "hipaaEnabled": False,
        "liveTranscriptsEnabled": False,
        "silenceTimeoutSeconds": 30,
        "responseDelaySeconds": 0.5,
        "llmRequestDelaySeconds": 0.1,
        "clientMessages": [
            "transcript",
            "hang",
            "function-call",
            "speech-update",
            "metadata",
            "conversation-update"
        ],
        "serverMessages": [
            "end-of-call-report",
            "status-update",
            "hang",
            "function-call"
        ],
        "interruptionsEnabled": True,
        "numWordsToInterruptAssistant": 2,
        "callUrl": "https://vapi.daily.co/6NVEvg17PFRY9n9Q61sU",
        "maxDurationSeconds": 1800,
        "customerJoinTimeoutSeconds": 15,
        "backgroundSound": "off",
        "metadata": {},
        "miscellaneous": {
            "call": {
                "id": "c4f10969-e2aa-4e9e-b405-8f608db9df26",
                "orgId": "e3436eb8-00c6-4f36-ba42-b97895803bfa",
                "createdAt": "2024-04-06T22:33:58.606Z",
                "updatedAt": "2024-04-06T22:33:58.606Z",
                "type": "webCall",
                "webCallUrl": "https://vapi.daily.co/6NVEvg17PFRY9n9Q61sU",
                "status": "queued",
                "assistantId": "7d444afe-1c8b-4708-8f45-5b6592e60b47"
            },
            "org": {
                "id": "e3436eb8-00c6-4f36-ba42-b97895803bfa",
                "name": "realcryptoplato@gmail.com's Org",
                "createdAt": "2024-03-25T19:56:17.428Z",
                "updatedAt": "2024-03-25T19:56:17.428Z",
                "stripeCustomerId": None,
                "stripeSubscriptionId": None,
                "stripeSubscriptionItemId": None,
                "billingLimit": 10,
                "stripeSubscriptionCurrentPeriodStart": None,
                "stripeSubscriptionStatus": None,
                "serverUrl": None,
                "concurrencyLimit": 10,
                "serverUrlSecret": None,
                "zapierHookUrl": None,
                "hipaaEnabled": None,
                "toltReferral": None,
                "bill": 1.0151,
                "withinBillingLimit": True,
                "activeCalls": "0",
                "withinConcurrencyLimit": True
            }
        },
        "sampleRate": 48000,
        "voicemailMessage": "",
        "voicemailDetectionEnabled": True,
        "orgName": "realcryptoplato@gmail.com's Org",
        "id": "c4f10969-e2aa-4e9e-b405-8f608db9df26",
        "createdAt": "2024-04-06T22:33:58.606Z",
        "updatedAt": "2024-04-06T22:33:58.606Z",
        "webCallUrl": "https://vapi.daily.co/6NVEvg17PFRY9n9Q61sU",
        "status": "queued",
        "assistantId": "7d444afe-1c8b-4708-8f45-5b6592e60b47"
    },
    "metadata": {}
}


def send_to_openai(prompt):
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json',
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post('https://api.openai.com/v1/chat/completions', json=data, headers=headers)
    return response.json()

def send_to_custom_api(prompt):
    headers = {
        'Authorization': f'Bearer {CUSTOM_API_KEY}',  # Adjust as needed
        'Content-Type': 'application/json',
    }
    data = {
        # Adjust the payload structure as per your custom API's requirements
        "messages": [
            {"role": "system", "content": "You are an assistant."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(openaipassurl, json=data, headers=headers)
    print(response)
    return response.json()

def send_to_custom_streamingapi(prompt, CUSTOM_API_KEY, openaipassurl):
    headers = {
        'Authorization': f'Bearer {CUSTOM_API_KEY}',
        'Content-Type': 'application/json',
    }
    data = {
        "model": "gpt-4",  # Specify the model you want to use here
        "messages": [
            {"role": "system", "content": "You are an assistant."},
            {"role": "user", "content": prompt}
        ],
        "stream": True,  # This forces streaming to be on
    }
    response = requests.post(openaipassurl, json=data, headers=headers)  # Ensure `stream=True` is set in the request as well
    
    # For a streaming response, you might want to process the lines as they arrive.
    # Here's an example of how you could print each line of the response.
    # Note: This is just an example; the actual implementation will depend on the API's streaming format.
    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))

    # Streaming responses don't typically use `.json()` since they're not a single JSON response.
    # You'll process them as shown above instead.

# Mock request data simulating a VAPI request
mock_vapi_request = {
    "messages": [
        {"role": "system", "content": "You are an assistant."},
        {"role": "user", "content": "Tell me a joke."}
    ],
    "temperature": 0.5,
    "max_tokens": 150,
    "stream": True
}

# Example usage
prompt = "How are you feeling?"
# print("Sending to OpenAI...")
# openai_response = send_to_openai(prompt)
# print(openai_response)

# print("\nSending to Custom API...")
# custom_api_response = send_to_custom_streamingapi(prompt,OPENAI_API_KEY,openaipassurl)
# print(custom_api_response)

import httpx
import asyncio

async def stream_response_openai():

    # OpenAI chat completions URL
    openaiurl = "https://api.openai.com/v1/chat/completions"
    memgpturl = "https://chat.ella-ai-care.com/api/memgpt/chat/completions"

    flaskpuburl = "https://chat.ella-ai-care.com/api/custom-llm/openai-sse/chat/completions"

    flaskurl = "http://localhost:5000/api/custom-llm/openai-sse/chat/completions"

    dummyurl  = "http://localhost:9000/api/dummy/chat/completions"
    fasttest = "http://localhost:9000/api/openai-sse/chat/completions"
    fastdummy = "http://localhost:9000/api/streaming-endpoint"
    fastopenai = "http://localhost:9000/stream-openai"
    faststreamtest = "http://localhost:9000/openai-sse/chat/completions"
    memgptstreamtest = "http://localhost:9000/memgpt-sse/chat/completions"

    url = memgptstreamtest
    # Payload following OpenAI's API requirements
    payload = {
        "model": "gpt-3.5-turbo",
        "stream": True,  # Enable streaming for SSE response
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "what other ideas do you have about that?"}
        ]
    }

    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json',
    }

    # Increase the timeout (e.g., to 30 seconds)
    timeout = httpx.Timeout(10, connect=10)
    # Enable streaming for the HTTPX client
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        response = await client.post(url, json=payload)  # Send POST request
        print(response)
        async for line in response.aiter_lines():
            # Process each line received in the response
            print (line)
            # if line.startswith("data:"):
            #     print("Received streamed data from:", url, line[len("data: "):])

# Running the test client for OpenAI
print('running test....')
asyncio.run(stream_response_openai())





