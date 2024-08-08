import asyncio
import aiohttp
import json
import ssl

async def test_memgpt_chat():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        url = "https://chat.ella-ai-care.com:443/vapi/memgpt/chat/completions"
        headers = {"Content-Type": "application/json"}
        data = {
            "message": "Tell me a short joke."
        }

        async with session.post(url, headers=headers, json=data, ssl=ssl_context) as response:
            if response.status == 200:
                print("Streaming response from MemGPT:")
                async for line in response.content:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("data: "):
                        try:
                            json_data = json.loads(decoded_line[6:])
                            if 'choices' in json_data and json_data['choices']:
                                delta = json_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    print(delta['content'], end='', flush=True)
                        except json.JSONDecodeError:
                            if decoded_line != "data: [DONE]":
                                print(f"Error decoding JSON: {decoded_line}")
                print("\nStream ended.")
            else:
                print(f"Error: {response.status}")
                print(await response.text())

if __name__ == "__main__":
    asyncio.run(test_memgpt_chat())