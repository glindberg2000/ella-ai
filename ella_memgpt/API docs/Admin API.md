# Admin API

## Get All Users
- **Method**: GET
- **URL**: `http://localhost:8283/admin/users`
- **Description**: Get a list of all users in the database

### Parameters
- **Query Parameters**:
  - `cursor` (string, optional): Pagination cursor
  - `limit` (integer, optional): Number of results to return (default: 50)

### Response
- **200 OK**:
  ```json
  [
    {
      "id": ["user-123e4567-e89b-12d3-a456-426614174000"],
      "name": "string",
      "created_at": "2024-08-17T19:16:17.046Z"
    }
  ]
  ```
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/admin/users"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}

response = requests.get(url, headers=headers)
print(response.text)
```

## Create User
- **Method**: POST
- **URL**: `http://localhost:8283/admin/users`
- **Description**: Create a new user in the database

### Parameters
- **Body Parameters**:
  - `name` (string, required): The name of the user

### Response
- **200 OK**:
  ```json
  {
    "id": ["user-123e4567-e89b-12d3-a456-426614174000"],
    "name": "string",
    "created_at": "2024-08-17T19:16:17.046Z"
  }
  ```
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/admin/users"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {"name": "John Doe"}

response = requests.post(url, json=payload, headers=headers)
print(response.text)
```

## Delete User
- **Method**: DELETE
- **URL**: `http://localhost:8283/admin/users`
- **Description**: Delete a user from the database

### Parameters
- **Query Parameters**:
  - `user_id` (string, required): The user_id key to be deleted

### Response
- **200 OK**:
  ```json
  {
    "id": ["user-123e4567-e89b-12d3-a456-426614174000"],
    "name": "string",
    "created_at": "2024-08-17T19:16:17.046Z"
  }
  ```
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/admin/users"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
params = {"user_id": "user-123e4567-e89b-12d3-a456-426614174000"}

response = requests.delete(url, params=params, headers=headers)
print(response.text)
```

## Create New API Key
- **Method**: POST
- **URL**: `http://localhost:8283/admin/users/keys`
- **Description**: Create a new API key for a user

### Parameters
- **Body Parameters**:
  - `user_id` (string, required): The unique identifier of the user associated with the token
  - `name` (string, optional): Name of the token

### Response
- **200 OK**:
  ```json
  {
    "id": ["sk-123e4567-e89b-12d3-a456-426614174000"],
    "user_id": "string",
    "key": "string",
    "name": "string"
  }
  ```
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/admin/users/keys"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer key"
}
payload = {
    "user_id": "user-123e4567-e89b-12d3-a456-426614174000",
    "name": "My API Key"
}

response = requests.post(url, json=payload, headers=headers)
print(response.text)
```

## Get API Keys
- **Method**: GET
- **URL**: `http://localhost:8283/admin/users/keys`
- **Description**: Get a list of all API keys for a user

### Parameters
- **Query Parameters**:
  - `user_id` (string, required): The unique identifier of the user

### Response
- **200 OK**:
  ```json
  [
    {
      "id": ["sk-123e4567-e89b-12d3-a456-426614174000"],
      "user_id": "string",
      "key": "string",
      "name": "string"
    }
  ]
  ```
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/admin/users/keys"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
params = {"user_id": "user-123e4567-e89b-12d3-a456-426614174000"}

response = requests.get(url, params=params, headers=headers)
print(response.text)
```

## Delete API Key
- **Method**: DELETE
- **URL**: `http://localhost:8283/admin/users/keys`
- **Description**: Delete an API key

### Parameters
- **Query Parameters**:
  - `api_key` (string, required): The API key to be deleted

### Response
- **200 OK**:
  ```json
  {
    "id": ["sk-123e4567-e89b-12d3-a456-426614174000"],
    "user_id": "string",
    "key": "string",
    "name": "string"
  }
  ```
- **422 Unprocessable Entity**: Validation Error

### Example Code
```python
import requests

url = "http://localhost:8283/admin/users/keys"
headers = {
    "accept": "application/json",
    "authorization": "Bearer key"
}
params = {"api_key": "sk-123e4567-e89b-12d3-a456-426614174000"}

response = requests.delete(url, params=params, headers=headers)
print(response.text)
```
