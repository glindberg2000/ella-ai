import requests
from sseclient import SSEClient
import requests
from sseclient import SSEClient

def send_data(url, payload):
    """ Send data to the server and establish an SSE connection to receive responses. """
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=payload, headers=headers, stream=True)
    return response

def listen_for_events(response):
    """ Listen for Server-Sent Events and print them. """
    client = SSEClient(response)
    try:
        for event in client.events():
            print(f"Received Event: {event.data}")
    except KeyboardInterrupt:
        print("Stream closed.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    server_url = 'http://localhost:9000/memgpt-sse/chat/completions'
    user_data = {
        "call": {
            "serverUrlSecret": "sk-9de42a0a8262228362ae1c7fb57dabfb9229cdd65470218f:9471c498-e8fc-43cb-9c43-4fd1e9df4c37"
        },
        "messages": [
            {"content": "Hello, world again!"}
        ]
    }

    print("Sending data to server...")
    response = send_data(server_url, user_data)
    if response.ok:
        print("Listening for server-sent events...")
        listen_for_events(response)
    else:
        print(f"Failed to send data: {response.text}")

