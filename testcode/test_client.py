import requests
import json
import os
from dotenv import load_dotenv
import logging
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

MEMGPT_BASE_URL = "http://localhost:8080"
MEMGPT_API_KEY = os.getenv('TEST_MEMGPT_USER_API_KEY')
MEMGPT_AGENT_ID = os.getenv('TEST_MEMGPT_AGENT_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Ensure all required environment variables are set
if not all([MEMGPT_API_KEY, MEMGPT_AGENT_ID, OPENAI_API_KEY]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

memgpt_headers = {
    "Authorization": f"Bearer {MEMGPT_API_KEY}",
    "Content-Type": "application/json"
}

# Set up OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def send_message(message, model="gpt-4o-mini", stream=True, api="openai"):
    if api == "memgpt":
        return send_memgpt_message(message, model, stream)
    else:
        return send_openai_message(message, model, stream)

def send_memgpt_message(message, model, stream):
    url = f"{MEMGPT_BASE_URL}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": stream,
        "user": MEMGPT_AGENT_ID
    }

    logging.debug(f"Sending MemGPT request with payload: {payload}")

    try:
        response = requests.post(url, headers=memgpt_headers, json=payload, stream=stream)
        logging.debug(f"Received response with status code: {response.status_code}")
        logging.debug(f"Response headers: {response.headers}")
        
        if response.status_code != 200:
            logging.error(f"Error response: {response.text}")
            return f"Error: {response.status_code} - {response.text}"
        
        if stream:
            return handle_memgpt_stream_response(response)
        else:
            return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred: {e}")
        return f"Error: {str(e)}"

def handle_memgpt_stream_response(response):
    full_response = ""
    for line in response.iter_lines():
        if line:
            try:
                line = line.decode('utf-8')
                logging.debug(f"Received line: {line}")
                if line.startswith('data: '):
                    line = line[6:]  # Remove 'data: ' prefix
                if line == '[DONE]':
                    break
                chunk = json.loads(line)
                if 'choices' in chunk and chunk['choices']:
                    delta = chunk['choices'][0].get('delta', {})
                    if 'content' in delta:
                        content = delta['content']
                        print(content, end='', flush=True)
                        full_response += content
            except json.JSONDecodeError:
                logging.warning(f"Failed to decode: {line}")
    print()  # New line after the complete response
    return full_response if full_response else "No response content available."

def send_openai_message(message, model, stream):
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message}],
            stream=stream
        )
        
        if stream:
            return handle_openai_stream_response(response)
        else:
            return response.choices[0].message.content
    except Exception as e:
        logging.error(f"An error occurred with OpenAI API: {e}")
        return f"Error: {str(e)}"

def handle_openai_stream_response(response):
    full_response = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            print(content, end='', flush=True)
            full_response += content
    print()  # New line after the complete response
    return full_response

def main():
    print("Welcome to the Updated Multi-API OpenAI-compatible Streaming Client!")
    print("Choose an API to use:")
    print("1. MemGPT")
    print("2. OpenAI")
    
    while True:
        api_choice = input("Enter your choice (1 or 2): ")
        if api_choice in ['1', '2']:
            break
        print("Invalid choice. Please enter 1 or 2.")
    
    api = "memgpt" if api_choice == '1' else "openai"
    model = "gpt-4o-mini" if api == "memgpt" else "gpt-3.5-turbo"
    
    print(f"Using {api.upper()} API. Type 'exit' to quit the chat.")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        
        print("Assistant: ", end='', flush=True)
        response = send_message(user_input, model=model, api=api)
        if not response or response == "No response content available.":
            print(response)

if __name__ == "__main__":
    main()