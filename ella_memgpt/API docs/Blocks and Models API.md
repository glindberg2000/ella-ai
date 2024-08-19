# Blocks API

## List Blocks
- **Method**: GET
- **URL**: `http://localhost:8283/api/blocks`
- **Description**: Retrieve a list of blocks based on specified criteria.

### Parameters

#### Query Parameters
- `label` (string, optional): Labels to include (e.g. human, persona)
- `templates_only` (boolean, optional, default=true): Whether to include only templates
- `name` (string, optional): Name of the block

### Responses

#### 200 OK: Successful Response
```json
[
  {
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

url = "http://localhost:8283/api/blocks"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
params = {
    "templates_only": True,
    "label": "human"
}

response = requests.get(url, headers=headers, params=params)
print(response.status_code)
print(response.json())
```

## Create Block
- **Method**: POST
- **URL**: `http://localhost:8283/api/blocks`
- **Description**: Create a new block with the specified parameters.

### Parameters

#### Body Parameters
- `value` (string, optional): Value of the block.
- `limit` (integer, optional, default=2000): Character limit of the block.
- `name` (string, optional): Name of the block.
- `template` (boolean, optional, default=true): Whether the block is a template.
- `label` (string, required): Label of the block.
- `description` (string, optional): Description of the block.
- `metadata_` (object, optional, default={}): Metadata of the block.
- `user_id` (string, optional): The unique identifier of the user associated with the block.

### Responses

#### 200 OK: Successful Response
```json
{
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

url = "http://localhost:8283/api/blocks"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "value": "This is a sample block",
    "label": "sample",
    "template": True,
    "description": "A sample block for demonstration"
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

## Update Block
- **Method**: POST
- **URL**: `http://localhost:8283/api/blocks/{block_id}`
- **Description**: Update an existing block with the specified parameters.

### Parameters

#### Path Parameters
- `block_id` (string, required): The ID of the block to update.

#### Body Parameters
- `value` (string, optional): Value of the block.
- `limit` (integer, optional, default=2000): Character limit of the block.
- `name` (string, optional): Name of the block.
- `template` (boolean, optional, default=false): Whether the block is a template.
- `label` (string, optional): Label of the block.
- `description` (string, optional): Description of the block.
- `metadata_` (object, optional, default={}): Metadata of the block.
- `user_id` (string, optional): The unique identifier of the user associated with the block.
- `id` (string, required): The unique identifier of the block.

### Responses

#### 200 OK: Successful Response
```json
{
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

url = "http://localhost:8283/api/blocks/block-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "value": "Updated block value",
    "description": "Updated description"
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.json())
```

## Delete Block
- **Method**: DELETE
- **URL**: `http://localhost:8283/api/blocks/{block_id}`
- **Description**: Delete a specific block.

### Parameters

#### Path Parameters
- `block_id` (string, required): The ID of the block to delete.

### Responses

#### 200 OK: Successful Response
```json
{
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

url = "http://localhost:8283/api/blocks/block-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.delete(url, headers=headers)
print(response.status_code)
print(response.json())
```

## Get Block
- **Method**: GET
- **URL**: `http://localhost:8283/api/blocks/{block_id}`
- **Description**: Retrieve a specific block by its ID.

### Parameters

#### Path Parameters
- `block_id` (string, required): The ID of the block to retrieve.

### Responses

#### 200 OK: Successful Response
```json
{
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

url = "http://localhost:8283/api/blocks/block-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```

# Models API

## List Models
- **Method**: GET
- **URL**: `http://localhost:8283/api/models`
- **Description**: Retrieve a list of available models and their configurations.

### Parameters
None

### Responses

#### 200 OK: Successful Response
```json
{
  "models": [
    {
      "model": "string",
      "model_endpoint_type": "string",
      "model_endpoint": "string",
      "model_wrapper": "string",
      "context_window": 0
    }
  ]
}
```

### Example Code
```python
import requests

url = "http://localhost:8283/api/models"
headers = {
    "accept": "application/json"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.json())
```