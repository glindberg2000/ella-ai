import httpx
import asyncio

async def test_voice_input():
    url = 'http://localhost:8000/stream'
    data = {'text': 'Hi, 28.', 'id':'myidentifier'}
    headers = {'Content-Type': 'application/json'}

    # Increased verbosity in client handling
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=None)) as client:
        response = await client.post(url, json=data, headers=headers)
        print(f"raw response: {response.text}")
        try:
            # Check response status to ensure it's ready for streaming
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                async for line in response.aiter_lines():
                    if line.startswith('data:'):
                        print("Received:", line)
                        break  # Optionally continue to process more lines as needed
        except Exception as e:
            print(f"Error during SSE reception: {e}")



import httpx
import asyncio

# Asynchronous function to test streaming with a POST request
async def test_voice_input2():
    url = 'http://localhost:8000/stream'
    data = {'text': 'Hi, 37.', 'id':'myidentifier'}
    headers = {'Content-Type': 'application/json'}

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=None)) as client:
        # Send POST request with JSON data and set stream=True
        async with client.stream("POST", url, json=data, headers=headers) as response:
            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                # Read the streamed response line by line
                async for line in response.aiter_lines():
                    if line:
                        print("Received:", line)
            else:
                print("Failed to get a successful response")

if __name__ == "__main__":
    asyncio.run(test_voice_input2())









