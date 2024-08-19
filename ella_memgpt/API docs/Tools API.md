# Tools API

## Delete Tool
- **Method**: DELETE
- **URL**: `http://localhost:8283/admin/tools/{tool_name}`
- **Description**: Delete a tool by name

### Parameters
- **Path Parameters**:
  - `tool_name` (string, required): The name of the tool to delete

### Response
- **200 OK**: Successful Response
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/admin/tools/tool_name"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.delete(url, headers=headers)
print(response.text)
```

## Get Tool
- **Method**: GET
- **URL**: `http://localhost:8283/admin/tools/{tool_name}`
- **Description**: Get a tool by name

### Parameters
- **Path Parameters**:
  - `tool_name` (string, required): The name of the tool to retrieve

### Response
- **200 OK**:
  ```json
  {
    "description": "string",
    "source_type": "string",
    "module": "string",
    "user_id": "string",
    "id": ["tool-123e4567-e89b-12d3-a456-426614174000"],
    "name": "string",
    "tags": ["string"],
    "source_code": "string",
    "json_schema": {}
  }
  ```
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/admin/tools/tool_name"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.text)
```

## List All Tools
- **Method**: GET
- **URL**: `http://localhost:8283/admin/tools`
- **Description**: List all available tools

### Response
- **200 OK**:
  ```json
  {
    "tools": [
      {
        "description": "string",
        "source_type": "string",
        "module": "string",
        "user_id": "string",
        "id": ["tool-123e4567-e89b-12d3-a456-426614174000"],
        "name": "string",
        "tags": ["string"],
        "source_code": "string",
        "json_schema": {}
      }
    ]
  }
  ```

### Example Code
```python
import requests

url = "http://localhost:8283/admin/tools"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.text)
```

## Create Tool
- **Method**: POST
- **URL**: `http://localhost:8283/admin/tools`
- **Description**: Create a new tool

### Parameters
- **Body Parameters**:
  - `json_schema` (object, required): JSON schema of the tool
  - `source_code` (string, required): The source code of the function
  - `source_type` (string, optional): The type of the source code
  - `tags` (array of strings, optional): Metadata tags

### Response
- **200 OK**:
  ```json
  {
    "description": "string",
    "source_type": "string",
    "module": "string",
    "user_id": "string",
    "id": ["tool-123e4567-e89b-12d3-a456-426614174000"],
    "name": "string",
    "tags": ["string"],
    "source_code": "string",
    "json_schema": {}
  }
  ```
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/admin/tools"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}

data = {
    "json_schema": {},
    "source_code": "def example_function():\n    return 'Hello, World!'",
    "source_type": "python",
    "tags": ["example", "hello-world"]
}

response = requests.post(url, json=data, headers=headers)
print(response.text)
```

## Delete Tool
- **Method**: DELETE
- **URL**: `http://localhost:8283/api/tools/{tool_id}`
- **Description**: Delete a tool by ID

### Parameters 
- **Path Parameters**:
  - `tool_id` (string, required): The ID of the tool to delete

### Response**
- **200 OK**: Tool successfully deleted
- **404 Not Found**: Tool not found
- **422 Unprocessable Entity**: Validation Error

**### Example Code**
```python
import requests

url = "http://localhost:8283/api/tools/tool-123e4567-e89b-12d3-a456-426614174000"
headers = {
    "accept": "application/json",
    "authorization": "Bearer your_api_key_here"
}

response = requests.delete(url, headers=headers)
print(response.status_code)
```

## Get Tool

## Update Tool
- **Method**: POST
- **URL**: `http://localhost:8283/api/tools/{tool_id}`
- **Description**: Update an existing tool

### Parameters
- **Path Parameters**:
  - `tool_id` (string, required): 
- **Body Parameters**:
  - `description` (string, optional): The description of the tool
  - `source_type` (string, optional): The type of the source code
  - `module` (string, optional): The module of the function
  - `user_id` (string, optional): The unique identifier of the user associated with the function
  - `name` (string, optional): The name of the function
  - `tags` (array of strings, optional): Metadata tags
  - `source_code` (string, optional): The source code of the function
  - `json_schema` (object, optional): The JSON schema of the function
  - `id` (string, required): The unique identifier of the tool

### Response
- **200 OK**:
  ```json
  {
    "description": "string",
    "source_type": "string",
    "module": "string",
    "user_id": "string",
    "id": ["tool-123e4567-e89b-12d3-a456-426614174000"],
    "name": "string",
    "tags": ["string"],
    "source_code": "string",
    "json_schema": {}
  }
  ```
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/api/tools/tool_id"

payload = {
    "source_code": None,
    "json_schema": { "newKey": "New Value" },
    "source_type": "python",
    "description": "schedule event",
    "module": "my_module",
    "id": "my_id"
}
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}

response = requests.post(url, json=payload, headers=headers)

print(response.text)
```

## Get Tool ID
- **Method**: GET
- **URL**: `http://localhost:8283/api/tools/name/{tool_name}`
- **Description**: Get a tool's ID by its name

### Parameters
- **Path Parameters**:
  - `tool_name` (string, required): The name of the tool

### Response
- **200 OK**: string (the tool ID)
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/api/tools/name/tool_name"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.text)
```



## List All Tools

**Method:** `GET`  
**URL:** `http://memgpt.localhost/api/tools`  
**Description:** Get a list of all tools available to agents created by a user.

### Parameters
None

### Responses

- **200 OK:** Successful Response
    ```json
    [
      {
        "description": "string",
        "source_type": "string",
        "module": "string",
        "user_id": "string",
        "id": ["tool-123e4567-e89b-12d3-a456-426614174000"],
        "name": "string",
        "tags": ["string"],
        "source_code": "string",
        "json_schema": {}
      }
    ]
    ```

- **description** (`string`, optional): The description of the tool.
- **source_type** (`string`, optional): The type of the source code.
- **module** (`string`, optional): The module of the function.
- **user_id** (`string`, optional): The unique identifier of the user associated with the function.
- **id** (`array of strings`, required): The human-friendly ID of the Tool.
- **name** (`string`, required): The name of the function.
- **tags** (`array of strings`, required): Metadata tags.
- **source_code** (`string`, required): The source code of the function.
- **json_schema** (`object`, optional): The JSON schema of the function.

### Example Code

```python
import requests

url = "http://memgpt.localhost/api/tools"
headers = {
    "accept": "application/json",
    "authorization": "Bearer sk-081fc96c2faa1bb008b6dd2a8454ea1e9a60a3010001e26e"
}

response = requests.get(url, headers=headers)
print(response.text)
```

## Create Tool

**Method:** `POST`  
**URL:** `http://memgpt.localhost/api/tools`  
**Description:** Create a new tool.

### Body Parameters

- **description** (`string`, optional): The description of the tool.
- **source_type** (`string`, optional): The type of the source code.
- **module** (`string`, optional): The module of the function.
- **user_id** (`string`, optional): The unique identifier of the user associated with the function.
- **name** (`string`, required): The name of the function.
- **tags** (`array of strings`, required): Metadata tags.
- **source_code** (`string`, required): The source code of the function.
- **json_schema** (`object`, optional): The JSON schema of the function.

### Responses

- **200 OK:** Successful Response
    ```json
    {
      "description": "string",
      "source_type": "string",
      "module": "string",
      "user_id": "string",
      "id": [
        "tool-123e4567-e89b-12d3-a456-426614174000"
      ],
      "name": "string",
      "tags": [
        "string"
      ],
      "source_code": "string",
      "json_schema": {}
    }
    ```

- **422 Validation Error:**
    ```json
    {
      "detail": [
        {
          "loc": [
            "string",
            0
          ],
          "msg": "string",
          "type": "string"
        }
      ]
    }
    ```

### Example Code

```python
import requests

url = "http://memgpt.localhost/api/tools"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer sk-sample"
}

response = requests.post(url, headers=headers)

print(response.text)