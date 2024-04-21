import requests

# URL of the FastAPI streaming endpoint
url = "http://localhost:8000/stream/"

# Open a streaming connection
# with requests.get(url, stream=True) as response:
#     # Ensure the response is successful
#     if response.status_code == 200:
#         # Read the streamed data in chunks
#         for chunk in response.iter_lines():
#             # Decode the bytes into a string
#             if chunk:
#                 print(chunk.decode('utf-8'))
#     else:
#         print("Failed to connect to the streaming endpoint")





# JSON payload with a counter start value
payload = {"counter_start": 5}

# Send a POST request with the JSON payload and stream the response
with requests.post(url, json=payload, stream=True) as response:
    if response.status_code == 200:
        # Read the streamed data in chunks
        for chunk in response.iter_lines():
            if chunk:
                print(chunk.decode('utf-8'))
    else:
        print("Failed to connect to the streaming endpoint")



