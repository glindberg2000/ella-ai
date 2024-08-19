# Sources API

## Get Source
- **Method**: GET
- **URL**: `http://localhost:8283/api/sources/{source_id}`
- **Description**: Get details of a specific source.

### Parameters
#### Path Parameters
- `source_id` (string, required): The ID of the source to retrieve.

### Responses
#### 200 OK: Successful Response
```json
{
  "description": "string",
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
  "metadata_": {},
  "id": ["source-123e4567-e89b-12d3-a456-426614174000"],
  "name": "string",
  "created_at": "2024-08-17T19:16:17.046Z",
  "user_id": "string"
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

url = "http://localhost:8283/api/sources/source-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Update Source
- **Method**: POST
- **URL**: `http://localhost:8283/api/sources/{source_id}`
- **Description**: Update the name or documentation of an existing data source.

### Parameters
#### Path Parameters
- `source_id` (string, required): The ID of the source to update.

#### Body Parameters
- `description` (string, optional): The description of the source.
- `embedding_config` (object, optional): The embedding configuration used by the passage.
- `metadata_` (object, optional): Metadata associated with the source.
- `id` (string, required): The ID of the source.
- `name` (string, optional): The name of the source.

### Responses
#### 200 OK: Successful Response
```json
{
  "description": "string",
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
  "metadata_": {},
  "id": ["source-123e4567-e89b-12d3-a456-426614174000"],
  "name": "string",
  "created_at": "2024-08-17T19:16:17.046Z",
  "user_id": "string"
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

url = "http://localhost:8283/api/sources/source-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "description": "Updated source description",
    "name": "Updated Source Name"
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

## Delete Source
- **Method**: DELETE
- **URL**: `http://localhost:8283/api/sources/{source_id}`
- **Description**: Delete a data source.

### Parameters
#### Path Parameters
- `source_id` (string, required): The ID of the source to delete.

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

url = "http://localhost:8283/api/sources/source-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.delete(url, headers=headers)
print(response.status_code)
print(response.text)
```

## Get Source Id By Name
- **Method**: GET
- **URL**: `http://localhost:8283/api/sources/name/{source_name}`
- **Description**: Get a source ID by its name.

### Parameters
#### Path Parameters
- `source_name` (string, required): The name of the source.

### Responses
#### 200 OK: Successful Response
```
string
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

url = "http://localhost:8283/api/sources/name/My Source Name"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.text)
```

## List Sources
- **Method**: GET
- **URL**: `http://localhost:8283/api/sources`
- **Description**: List all data sources created by a user.

### Parameters
None

### Responses
#### 200 OK: Successful Response
```json
[
  {
    "description": "string",
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
    "metadata_": {},
    "id": ["source-123e4567-e89b-12d3-a456-426614174000"],
    "name": "string",
    "created_at": "2024-08-17T19:16:17.046Z",
    "user_id": "string"
  }
]
```

### Example Code
```python
import requests

url = "http://localhost:8283/api/sources"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Create Source
- **Method**: POST
- **URL**: `http://localhost:8283/api/sources`
- **Description**: Create a new data source.

### Parameters
#### Body Parameters
- `description` (string, optional): The description of the source.
- `embedding_config` (object, required): The embedding configuration used by the passage.
- `metadata_` (object, optional): Metadata associated with the source.
- `name` (string, required): The name of the source.

### Responses
#### 200 OK: Successful Response
```json
{
  "description": "string",
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
  "metadata_": {},
  "id": ["source-123e4567-e89b-12d3-a456-426614174000"],
  "name": "string",
  "created_at": "2024-08-17T19:16:17.046Z",
  "user_id": "string"
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

url = "http://localhost:8283/api/sources"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "name": "New Source",
    "description": "A new data source",
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

## Attach Source To Agent
- **Method**: POST
- **URL**: `http://localhost:8283/api/sources/{source_id}/attach`
- **Description**: Attach a data source to an existing agent.

### Parameters
#### Path Parameters
- `source_id` (string, required): The ID of the source to attach.

#### Query Parameters
- `agent_id` (string, required): The unique identifier of the agent to attach the source to.

### Responses
#### 200 OK: Successful Response
```json
{
  "description": "string",
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
  "metadata_": {},
  "id": ["source-123e4567-e89b-12d3-a456-426614174000"],
  "name": "string",
  "created_at": "2024-08-17T19:16:17.046Z",
  "user_id": "string"
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

url = "http://localhost:8283/api/sources/source-123e4567-e89b-12d3-a456-426614174000/attach"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
params = {
    "agent_id": "agent-123e4567-e89b-12d3-a456-426614174000"
}

response = requests.post(url, headers=headers, params=params)
print(response.status_code)
print(response.json())
```

## Detach Source From Agent
- **Method**: POST
- **URL**: `http://localhost:8283/api/sources/{source_id}/detach`
- **Description**: Detach a data source from an existing agent.

### Parameters
#### Path Parameters
- `source_id` (string, required): The ID of the source to detach.

#### Query Parameters
- `agent_id` (string, required): The unique identifier of the agent to detach the source from.

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

url = "http://localhost:8283/api/sources/source-123e4567-e89b-12d3-a456-426614174000/detach"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
params = {
    "agent_id": "agent-123e4567-e89b-12d3-a456-426614174000"
}

response = requests.post(url, headers=headers, params=params)
print(response.status_code)
print(response.text)
```

## Get Job
- **Method**: GET
- **URL**: `http://localhost:8283/api/sources/status/{job_id}`
- **Description**: Get the status of a job.

### Parameters
#### Path Parameters
- `job_id` (string, required): The ID of the job to check.

### Responses
#### 200 OK: Successful Response
```json
{
  "metadata_": {},
  "id": ["job-123e4567-e89b-12d3-a456-426614174000"],
  "status": "created",
  "created_at": "2024-08-17T19:16:17.046Z",
  "completed_at": "2024-08-17T19:16:17.046Z",
  "user_id": "string"
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

url = "http://localhost:8283/api/sources/status/job-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Upload File To Source
- **Method**: POST
- **URL**: `http://localhost:8283/api/sources/{source_id}/upload`
- **Description**: Upload a file to a data source.

### Parameters
#### Path Parameters
- `source_id` (string, required): The ID of the source to upload to.

#### Body Parameters
- `file` (file, required): The file to upload.

### Responses
#### 200 OK: Successful Response
```json
{
  "metadata_": {},
  "id": ["job-123e4567-e89b-12d3-a456-426614174000"],
  "status": "created",
  "created_at": "2024-08-17T19:16:17.046Z",
  "completed_at": "2024-08-17T19:16:17.046Z",
  "user_id": "string"
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

url = "http://localhost:8283/api/sources/source-123e4567-e89b-12d3-a456-426614174000/upload"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
files = {
    'file': ('filename.txt', open('path/to/file.txt', 'rb'), 'text/plain')
}

response = requests.post(url, headers=headers, files=files)
print(response.status_code)
print(response.json())
```

## List Passages
- **Method**: GET
- **URL**: `http://localhost:8283/api/sources/{source_id}/passages`
- **Description**: List all passages associated with a data source.

### Parameters
#### Path Parameters
- `source_id` (string, required): The ID of the source.

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

url = "http://localhost:8283/api/sources/source-123e4567-e89b-12d3-a456-426614174000/passages"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## List Documents
- **Method**: GET
- **URL**: `http://localhost:8283/api/sources/{source_id}/documents`
- **Description**: List all documents associated with a data source.

### Parameters
#### Path Parameters
- `source_id` (string, required): The ID of the source.

### Responses
#### 200 OK: Successful Response
```json
[
  {
    "id": ["doc-123e4567-e89b-12d3-a456-426614174000"],
    "text": "string",
    "source_id": "string",
    "user_id": "string",
    "metadata_": {}
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

url = "http://localhost:8283/api/sources/source-123e4567-e89b-12d3-a456-426614174000/documents"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

# Config API

## Get LLM Configs
- **Method**: GET
- **URL**: `http://localhost:8283/api/config/llm`
- **Description**: Retrieve the base LLM configuration for the server.

### Parameters
None

### Responses
#### 200 OK: Successful Response
```json
[
  {
    "model": "string",
    "model_endpoint_type": "string",
    "model_endpoint": "string",
    "model_wrapper": "string",
    "context_window": 0
  }
]
```

### Example Code
```python
import requests

url = "http://localhost:8283/api/config/llm"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Get Embedding Configs
- **Method**: GET
- **URL**: `http://localhost:8283/api/config/embedding`
- **Description**: Retrieve the base embedding configuration for the server.

### Parameters
None

### Responses
#### 200 OK: Successful Response
```json
[
  {
    "embedding_endpoint_type": "string",
    "embedding_endpoint": "string",
    "embedding_model": "string",
    "embedding_dim": 0,
    "embedding_chunk_size": 0,
    "azure_endpoint": "string",
    "azure_version": "string",
    "azure_deployment": "string"
  }
]
```

### Example Code
```python
import requests

url = "http://localhost:8283/api/config/embedding"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```