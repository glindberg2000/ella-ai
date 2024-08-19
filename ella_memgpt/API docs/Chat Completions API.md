# Chat Completions API

## Create Chat Completion
- **Method**: POST
- **URL**: `http://localhost:8283/v1/chat/completions`
- **Description**: Send a message to a MemGPT agent via a /chat/completions request. The bearer token will be used to identify the user. The 'user' field in the request should be set to the agent ID.

### Parameters

#### Body Parameters
- `model` (string, required): The model to use for the completion.
- `messages` (array, required): An array of message objects. Each object can be one of the following types:
  - `SYSTEMMESSAGE`
  - `USERMESSAGE`
  - `ASSISTANTMESSAGE`
  - `TOOLMESSAGE`
    - `content` (string, required)
    - `role` (string, default: "tool")
    - `tool_call_id` (string, required)
- `frequency_penalty` (number, optional, default: 0): Frequency penalty parameter.
- `logit_bias` (object, optional): Logit bias configuration.
- `logprobs` (boolean, optional, default: false): Whether to return log probabilities.
- `top_logprobs` (integer, optional): Number of top log probabilities to return.
- `max_tokens` (integer, optional): Maximum number of tokens to generate.
- `n` (integer, optional, default: 1): Number of completions to generate.
- `presence_penalty` (number, optional, default: 0): Presence penalty parameter.
- `response_format` (object, optional):
  - `type` (string, default: "text"): Response format type.
- `seed` (integer, optional): Random seed for generation.
- `stop` (string or array of strings, optional): Stop sequences for generation.
- `stream` (boolean, optional, default: false): Whether to stream the response.
- `temperature` (number, optional, default: 1): Sampling temperature.
- `top_p` (number, optional, default: 1): Top-p sampling parameter.
- `user` (string, optional): User identifier.
- `tools` (array, optional): Array of available tools.
- `tool_choice` (string or object, optional, default: "none"):
  - If object:
    - `type` (string, default: "function"): Type of tool choice.
    - `function` (object, required):
      - `name` (string, required): Name of the function to call.
- `functions` (array, optional): Array of available functions.
- `function_call` (string or object, optional):
  - If object:
    - `name` (string, required): Name of the function to call.

### Responses

#### 200 OK: Successful Response
```json
{
  "id": "string",
  "choices": [
    {
      "finish_reason": "string",
      "index": 0,
      "message": {
        "content": "string",
        "tool_calls": [
          {
            "id": "string",
            "type": "function",
            "function": {
              "arguments": "string",
              "name": "string"
            }
          }
        ],
        "role": "string",
        "function_call": {
          "arguments": "string",
          "name": "string"
        }
      },
      "logprobs": {
        "additionalProp": [
          {
            "token": "string",
            "logprob": 0,
            "bytes": [0],
            "top_logprobs": [
              {
                "token": "string",
                "logprob": 0,
                "bytes": [0]
              }
            ]
          }
        ]
      }
    }
  ],
  "created": "2024-08-17T19:16:17.046Z",
  "model": "string",
  "system_fingerprint": "string",
  "object": "chat.completion",
  "usage": {
    "completion_tokens": 0,
    "prompt_tokens": 0,
    "total_tokens": 0
  }
}
```

#### 422 Unprocessable Entity: Validation Error
```json
{
  "detail": [
    {
      "loc": ["string", 0],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

### Example Code
```python
import requests

url = "http://localhost:8283/v1/chat/completions"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "model": "gpt-3.5-turbo",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```