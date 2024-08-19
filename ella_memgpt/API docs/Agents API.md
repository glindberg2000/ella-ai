# Agents API

## Get All Agents
- **Method**: GET
- **URL**: `http://localhost:8283/api/admin/agents`
- **Description**: Get a list of all agents in the database.

### Parameters
None

### Responses

#### 200 OK: Successful Response
```json
[
  {
    "description": "string",
    "metadata_": {},
    "user_id": "string",
    "id": ["agent-123e4567-e89b-12d3-a456-426614174000"],
    "name": "string",
    "created_at": "2024-08-17T19:16:17.046Z",
    "message_ids": ["string"],
    "memory": {
      "memory": {
        "additionalProp": {
          "value": "string",
          "limit": 2000,
          "name": "string",
          "template": false,
          "label": "string",
          "description": "string",
          "metadata_": {},
          "user_id": "string",
          "id": ["block-123e4567-e89b-12d3-a456-426614174000"]
        }
      }
    },
    "tools": ["string"],
    "system": "string",
    "llm_config": {
      "model": "string",
      "model_endpoint_type": "string",
      "model_endpoint": "string",
      "model_wrapper": "string",
      "context_window": 0
    },
    "embedding_config": {
      "embedding_endpoint_type": "string",
      "embedding_endpoint": "string",
      "embedding_model": "string",
      "embedding_dim": 0,
      "embedding_chunk_size": 0,
      "azure_endpoint": "string",
      "azure_version": "string",
      "azure_deployment": "string"
    }
  }
]
```

### Example Code
```python
import requests

url = "http://localhost:8283/api/admin/agents"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## List Agents
- **Method**: GET
- **URL**: `http://localhost:8283/api/agents`
- **Description**: List all agents associated with a given user.

### Parameters
None

### Responses

#### 200 OK: Successful Response
```json
[
  {
    "description": "string",
    "metadata_": {},
    "user_id": "string",
    "id": ["agent-123e4567-e89b-12d3-a456-426614174000"],
    "name": "string",
    "created_at": "2024-08-17T19:16:17.046Z",
    "message_ids": ["string"],
    "memory": {
      "memory": {
        "additionalProp": {
          "value": "string",
          "limit": 2000,
          "name": "string",
          "template": false,
          "label": "string",
          "description": "string",
          "metadata_": {},
          "user_id": "string",
          "id": ["block-123e4567-e89b-12d3-a456-426614174000"]
        }
      }
    },
    "tools": ["string"],
    "system": "string",
    "llm_config": {
      "model": "string",
      "model_endpoint_type": "string",
      "model_endpoint": "string",
      "model_wrapper": "string",
      "context_window": 0
    },
    "embedding_config": {
      "embedding_endpoint_type": "string",
      "embedding_endpoint": "string",
      "embedding_model": "string",
      "embedding_dim": 0,
      "embedding_chunk_size": 0,
      "azure_endpoint": "string",
      "azure_version": "string",
      "azure_deployment": "string"
    }
  }
]
```

### Example Code
```python
import requests

url = "http://localhost:8283/api/agents"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Create Agent
- **Method**: POST
- **URL**: `http://localhost:8283/api/agents`
- **Description**: Create a new agent with the specified configuration.

### Parameters

#### Body Parameters
- `description` (string, optional): The description of the agent.
- `metadata_` (object, optional): The metadata of the agent.
- `user_id` (string, optional): The user id of the agent.
- `name` (string, required): The name of the agent.
- `message_ids` (array of strings, optional): The ids of the messages in the agent's in-context memory.
- `memory` (object, optional): The in-context memory of the agent.
- `tools` (array of strings, required): The tools used by the agent.
- `system` (string, required): The system prompt used by the agent.
- `llm_config` (object, required): The LLM configuration used by the agent.
- `embedding_config` (object, required): The embedding configuration used by the agent.

### Responses

#### 200 OK: Successful Response
```json
{
  "description": "string",
  "metadata_": {},
  "user_id": "string",
  "id": ["agent-123e4567-e89b-12d3-a456-426614174000"],
  "name": "string",
  "created_at": "2024-08-17T19:16:17.046Z",
  "message_ids": ["string"],
  "memory": {
    "memory": {
      "additionalProp": {
        "value": "string",
        "limit": 2000,
        "name": "string",
        "template": false,
        "label": "string",
        "description": "string",
        "metadata_": {},
        "user_id": "string",
        "id": ["block-123e4567-e89b-12d3-a456-426614174000"]
      }
    }
  },
  "tools": ["string"],
  "system": "string",
  "llm_config": {
    "model": "string",
    "model_endpoint_type": "string",
    "model_endpoint": "string",
    "model_wrapper": "string",
    "context_window": 0
  },
  "embedding_config": {
    "embedding_endpoint_type": "string",
    "embedding_endpoint": "string",
    "embedding_model": "string",
    "embedding_dim": 0,
    "embedding_chunk_size": 0,
    "azure_endpoint": "string",
    "azure_version": "string",
    "azure_deployment": "string"
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

url = "http://localhost:8283/api/agents"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "name": "New Agent",
    "description": "A test agent",
    "tools": ["tool1", "tool2"],
    "system": "You are a helpful assistant.",
    "llm_config": {
        "model": "gpt-3.5-turbo",
        "model_endpoint_type": "openai",
        "model_endpoint": "https://api.openai.com/v1",
        "context_window": 4000
    },
    "embedding_config": {
        "embedding_endpoint_type": "openai",
        "embedding_model": "text-embedding-ada-002",
        "embedding_dim": 1536
    }
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

## Update Agent
- **Method**: POST
- **URL**: `http://localhost:8283/api/agents/{agent_id}`
- **Description**: Update an existing agent.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent to update.

#### Body Parameters
- `description` (string, optional): The description of the agent.
- `metadata_` (object, optional): The metadata of the agent.
- `user_id` (string, optional): The user id of the agent.
- `id` (string, required): The id of the agent.
- `name` (string, optional): The name of the agent.
- `tools` (array of strings, optional): The tools used by the agent.
- `system` (string, optional): The system prompt used by the agent.
- `llm_config` (object, optional): The LLM configuration used by the agent.
- `embedding_config` (object, optional): The embedding configuration used by the agent.
- `message_ids` (array of strings, optional): The ids of the messages in the agent's in-context memory.
- `memory` (object, optional): The in-context memory of the agent.

### Responses

#### 200 OK: Successful Response
```json
{
  "description": "string",
  "metadata_": {},
  "user_id": "string",
  "id": ["agent-123e4567-e89b-12d3-a456-426614174000"],
  "name": "string",
  "created_at": "2024-08-17T19:16:17.046Z",
  "message_ids": ["string"],
  "memory": {
    "memory": {
      "additionalProp": {
        "value": "string",
        "limit": 2000,
        "name": "string",
        "template": false,
        "label": "string",
        "description": "string",
        "metadata_": {},
        "user_id": "string",
        "id": ["block-123e4567-e89b-12d3-a456-426614174000"]
      }
    }
  },
  "tools": ["string"],
  "system": "string",
  "llm_config": {
    "model": "string",
    "model_endpoint_type": "string",
    "model_endpoint": "string",
    "model_wrapper": "string",
    "context_window": 0
  },
  "embedding_config": {
    "embedding_endpoint_type": "string",
    "embedding_endpoint": "string",
    "embedding_model": "string",
    "embedding_dim": 0,
    "embedding_chunk_size": 0,
    "azure_endpoint": "string",
    "azure_version": "string",
    "azure_deployment": "string"
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "name": "Updated Agent Name",
    "description": "Updated description",
    "tools": ["new_tool1", "new_tool2"],
    "system": "Updated system prompt"
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

## Get Agent State
- **Method**: GET
- **URL**: `http://localhost:8283/api/agents/{agent_id}`
- **Description**: Get the state of the agent.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

### Responses

#### 200 OK: Successful Response
```json
{
  "description": "string",
  "metadata_": {},
  "user_id": "string",
  "id": ["agent-123e4567-e89b-12d3-a456-426614174000"],
  "name": "string",
  "created_at": "2024-08-17T19:16:17.046Z",
  "message_ids": ["string"],
  "memory": {
    "memory": {
      "additionalProp": {
        "value": "string",
        "limit": 2000,
        "name": "string",
        "template": false,
        "label": "string",
        "description": "string",
        "metadata_": {},
        "user_id": "string",
        "id": ["block-123e4567-e89b-12d3-a456-426614174000"]
      }
    }
  },
  "tools": ["string"],
  "system": "string",
  "llm_config": {
    "model": "string",
    "model_endpoint_type": "string",
    "model_endpoint": "string",
    "model_wrapper": "string",
    "context_window": 0
  },
  "embedding_config": {
    "embedding_endpoint_type": "string",
    "embedding_endpoint": "string",
    "embedding_model": "string",
    "embedding_dim": 0,
    "embedding_chunk_size": 0,
    "azure_endpoint": "string",
    "azure_version": "string",
    "azure_deployment": "string"
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Delete Agent
- **Method**: DELETE
- **URL**: `http://localhost:8283/api/agents/{agent_id}`
- **Description**: Delete an agent.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent to delete.

### Responses

#### 200 OK: Successful Response
Empty response body

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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.delete(url, headers=headers)
print(response.status_code)
print(response.text)
```

## Get Agent In Context Messages
- **Method**: GET
- **URL**: `http://localhost:8283/api/agents/{agent_id}/memory/messages`
- **Description**: Retrieve the messages in the context of a specific agent.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

### Responses

#### 200 OK: Successful Response
```json
[
  {
    "id": ["message-123e4567-e89b-12d3-a456-426614174000"],
    "role": "assistant",
    "text": "string",
    "user_id": "string",
    "agent_id": "string",
    "model": "string",
    "name": "string",
    "created_at": "2024-08-17T19:16:17.046Z",
    "tool_calls": [
      {
        "id": "string",
        "type": "function",
        "function": {
          "name": "string",
          "arguments": "string"
        }
      }
    ],
    "tool_call_id": "string"
  }
]
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/memory/messages"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Get Agent Memory
- **Method**: GET
- **URL**: `http://localhost:8283/api/agents/{agent_id}/memory`
- **Description**: Retrieve the memory state of a specific agent.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

### Responses

#### 200 OK: Successful Response
```json
{
  "memory": {
    "additionalProp": {
      "value": "string",
      "limit": 2000,
      "name": "string",
      "template": false,
      "label": "string",
      "description": "string",
      "metadata_": {},
      "user_id": "string",
      "id": ["block-123e4567-e89b-12d3-a456-426614174000"]
    }
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/memory"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Update Agent Memory
- **Method**: POST
- **URL**: `http://localhost:8283/api/agents/{agent_id}/memory`
- **Description**: Update the core memory of a specific agent.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

#### Body Parameters
- Memory update object (structure not specified in the provided information)

### Responses

#### 200 OK: Successful Response
```json
{
  "memory": {
    "additionalProp": {
      "value": "string",
      "limit": 2000,
      "name": "string",
      "template": false,
      "label": "string",
      "description": "string",
      "metadata_": {},
      "user_id": "string",
      "id": ["block-123e4567-e89b-12d3-a456-426614174000"]
    }
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/memory"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "memory": {
        "human": {
            "value": "Updated human memory",
            "limit": 2000
        },
        "persona": {
            "value": "Updated persona memory",
            "limit": 2000
        }
    }
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

## Get Agent Recall Memory Summary
- **Method**: GET
- **URL**: `http://localhost:8283/api/agents/{agent_id}/memory/recall`
- **Description**: Retrieve the summary of the recall memory of a specific agent.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

### Responses

#### 200 OK: Successful Response
```json
{
  "size": 0
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/memory/recall"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Get Agent Archival Memory Summary
- **Method**: GET
- **URL**: `http://localhost:8283/api/agents/{agent_id}/memory/archival`
- **Description**: Retrieve the summary of the archival memory of a specific agent.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

### Responses

#### 200 OK: Successful Response
```json
{
  "size": 0
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/memory/archival"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Get Agent Archival Memory
- **Method**: GET
- **URL**: `http://localhost:8283/api/agents/{agent_id}/archival`
- **Description**: Retrieve the memories in an agent's archival memory store (paginated query).

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

#### Query Parameters
- `after` (string, optional): Unique ID of the memory to start the query range at.
- `before` (string, optional): Unique ID of the memory to end the query range at.
- `limit` (integer, optional): How many results to include in the response.

### Responses

#### 200 OK: Successful Response
```json
[
  {
    "user_id": "string",
    "agent_id": "string",
    "source_id": "string",
    "doc_id": "string",
    "metadata_": {},
    "id": ["passage-123e4567-e89b-12d3-a456-426614174000"],
    "text": "string",
    "embedding": [0],
    "embedding_config": {
      "embedding_endpoint_type": "string",
      "embedding_endpoint": "string",
      "embedding_model": "string",
      "embedding_dim": 0,
      "embedding_chunk_size": 0,
      "azure_endpoint": "string",
      "azure_version": "string",
      "azure_deployment": "string"
    },
    "created_at": "2024-08-17T19:16:17.046Z"
  }
]
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/archival"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
params = {
    "limit": 10
}

response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.json())
```

## Insert Agent Archival Memory
- **Method**: POST
- **URL**: `http://localhost:8283/api/agents/{agent_id}/archival/{memory}`
- **Description**: Insert a memory into an agent's archival memory store.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.
- `memory` (string, required): The memory to insert.

### Responses

#### 200 OK: Successful Response
```json
[
  {
    "user_id": "string",
    "agent_id": "string",
    "source_id": "string",
    "doc_id": "string",
    "metadata_": {},
    "id": ["passage-123e4567-e89b-12d3-a456-426614174000"],
    "text": "string",
    "embedding": [0],
    "embedding_config": {
      "embedding_endpoint_type": "string",
      "embedding_endpoint": "string",
      "embedding_model": "string",
      "embedding_dim": 0,
      "embedding_chunk_size": 0,
      "azure_endpoint": "string",
      "azure_version": "string",
      "azure_deployment": "string"
    },
    "created_at": "2024-08-17T19:16:17.046Z"
  }
]
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/archival/New%20memory%20to%20insert"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.post(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Delete Agent Archival Memory
- **Method**: DELETE
- **URL**: `http://localhost:8283/api/agents/{agent_id}/archival/{memory_id}`
- **Description**: Delete a memory from an agent's archival memory store.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.
- `memory_id` (string, required): The ID of the memory to delete.

### Responses

#### 200 OK: Successful Response
Empty response body

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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/archival/memory-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.delete(url, headers=headers)
print(response.status_code)
print(response.text)
```

## Get Agent Messages In Context
- **Method**: GET
- **URL**: `http://localhost:8283/api/agents/{agent_id}/messages/context/`
- **Description**: Retrieve the in-context messages of a specific agent. Paginated, provide start and count to iterate.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

#### Query Parameters
- `start` (integer, required): Message index to start on (reverse chronological).
- `count` (integer, required): How many messages to retrieve.

### Responses

#### 200 OK: Successful Response
```json
[
  {
    "id": ["message-123e4567-e89b-12d3-a456-426614174000"],
    "role": "assistant",
    "text": "string",
    "user_id": "string",
    "agent_id": "string",
    "model": "string",
    "name": "string",
    "created_at": "2024-08-17T19:16:17.046Z",
    "tool_calls": [
      {
        "id": "string",
        "type": "function",
        "function": {
          "name": "string",
          "arguments": "string"
        }
      }
    ],
    "tool_call_id": "string"
  }
]
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/messages/context/"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
params = {
    "start": 0,
    "count": 10
}

response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.json())
```

## Get Agent Messages
- **Method**: GET
- **URL**: `http://localhost:8283/api/agents/{agent_id}/messages`
- **Description**: Retrieve message history for an agent.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

#### Query Parameters
- `before` (string, optional): Message before which to retrieve the returned messages.
- `limit` (integer, optional, default=10): Maximum number of messages to retrieve.

### Responses

#### 200 OK: Successful Response
```json
[
## Get Agent Messages (continued)
  {
    "id": ["message-123e4567-e89b-12d3-a456-426614174000"],
    "role": "assistant",
    "text": "string",
    "user_id": "string",
    "agent_id": "string",
    "model": "string",
    "name": "string",
    "created_at": "2024-08-17T19:16:17.046Z",
    "tool_calls": [
      {
        "id": "string",
        "type": "function",
        "function": {
          "name": "string",
          "arguments": "string"
        }
      }
    ],
    "tool_call_id": "string"
  }
]
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/messages"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
params = {
    "limit": 20
}

response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.json())
```

## Send Message
- **Method**: POST
- **URL**: `http://localhost:8283/api/agents/{agent_id}/messages`
- **Description**: Process a user message and return the agent's response. This endpoint accepts a message from a user and processes it through the agent. It can optionally stream the response if 'stream' is set to True.

### Parameters

#### Path Parameters
- `agent_id` (string, required): The ID of the agent.

#### Body Parameters
- `messages` (array of objects, required): The messages to be sent to the agent.
  - `role` (string, required): The role of the participant.
  - `text` (string, required): The text of the message.
  - `name` (string, optional): The name of the participant.
- `run_async` (boolean, optional, default=false): Whether to asynchronously send the messages to the agent.
- `stream_steps` (boolean, optional, default=false): Flag to determine if the response should be streamed. Set to True for streaming agent steps.
- `stream_tokens` (boolean, optional, default=false): Flag to determine if individual tokens should be streamed. Set to True for token streaming (requires stream_steps = True).

### Responses

#### 200 OK: Successful Response
```json
{
  "messages": [
    {
      "id": ["message-123e4567-e89b-12d3-a456-426614174000"],
      "role": "assistant",
      "text": "string",
      "user_id": "string",
      "agent_id": "string",
      "model": "string",
      "name": "string",
      "created_at": "2024-08-17T19:16:17.046Z",
      "tool_calls": [
        {
          "id": "string",
          "type": "function",
          "function": {
            "name": "string",
            "arguments": "string"
          }
        }
      ],
      "tool_call_id": "string"
    }
  ],
  "usage": {
    "completion_tokens": 0,
    "prompt_tokens": 0,
    "total_tokens": 0,
    "step_count": 0
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

url = "http://localhost:8283/api/agents/agent-123e4567-e89b-12d3-a456-426614174000/messages"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "messages": [
        {
            "role": "user",
            "text": "Hello, can you help me with a task?"
        }
    ],
    "run_async": False,
    "stream_steps": False,
    "stream_tokens": False
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```