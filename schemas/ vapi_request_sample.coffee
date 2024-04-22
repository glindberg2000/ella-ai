{
  "model": "gpt-3.5-turbo",
  "messages": [
    {
      "role": "system",
      "content": "You are an assistant."
    },
    {
      "role": "assistant",
      "content": "Hello. Can you hear me?"
    },
    {
      "role": "user",
      "content": "Yeah. I can hear you."
    }
  ],
  "temperature": 0,
  "functions": [
    {
      "name": "endCall",
      "parameters": {
        "type": "object",
        "properties": {}
      },
      "description": "Use this function to end the call."
    }
  ],
  "stream": true,
  "max_tokens": 500,
  "call": {
    "type": "webCall",
    "callId": "e5027f82-41b8-4b2c-9228-e5f0e88edbf3",
    "orgId": "e3436eb8-00c6-4f36-ba42-b97895803bfa",
    "transcriber": {
      "provider": "deepgram",
      "model": "nova-2-conversationalai",
      "keywords": [],
      "language": "en-US",
      "smartFormat": false
    },
    "model": {
      "provider": "custom-llm",
      "url": "https://chat.ella-ai-care.com/memgpt-sse",
      "urlRequestMetadataEnabled": true,
      "model": "gpt-3.5-turbo",
      "temperature": 0,
      "maxTokens": 500,
      "functions": [],
      "messages": [
        {
          "role": "system",
          "content": "You are an assistant."
        }
      ],
      "systemPrompt": ""
    },
    "voice": {
      "provider": "deepgram",
      "voiceId": "aura-asteria-en"
    },
    "serverUrl": "https://chat.ella-ai-care.com/api/vapi",
    "serverUrlSecret": "sk-9de42a0a8262228362ae1c7fb57dabfb9229cdd65470218f:9471c498-e8fc-43cb-9c43-4fd1e9df4c37",
    "firstMessage": "Hello, can you hear me?",
    "endCallMessage": "Talk to you later.",
    "endCallPhrases": ["Bye Bye"],
    "recordingEnabled": true,
    "endCallFunctionEnabled": true,
    "hipaaEnabled": false,
    "silenceTimeoutSeconds": 128,
    "clientMessages": ["transcript", "hang", "function-call", "speech-update", "metadata", "conversation-update"],
    "serverMessages": ["end-of-call-report", "status-update", "hang", "function-call"],
    "numWordsToInterruptAssistant": 8,
    "callUrl": "https://vapi.daily.co/zzisLurH3SGwX4juyrOL",
    "backgroundSound": "off"
  },
  "org": {
    "id": "e3436eb8-00c6-4f36-ba42-b97895803bfa",
    "name": "realcryptoplato@gmail.com's Org",
    "createdAt": "2024-03-25T19:56:17.428Z",
    "updatedAt": "2024-03-25T19:56:17.428Z",
    "bill": 9.8042,
    "withinBillingLimit": true,
    "activeCalls": "0",
    "withinConcurrencyLimit": true
  },
  "metadata": {}
}
