import json

import aiohttp
from memgpt.client.client import RESTClient

# from client import RESTClient


class ExtendedRESTClient(RESTClient):

    def __init__(self, base_url: str, token: str, debug: bool = False):
        super().__init__(base_url=base_url, token=token, debug=debug)
        self.token = token
        print(f"Token set in ExtendedRESTClient: {self.token}")  # Debugging line

    # Keeps the 'data:' for SSE compliance
    async def send_message_to_agent_streamed(self, agent_id, message):
        url = f"{self.base_url}/api/agents/{agent_id}/messages"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        payload = {
            "agent_id": agent_id,
            "message": message,
            "stream": True,
            "role": "user",
        }
        if self.debug:
            print(f"PAYLOAD: {payload}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                async for line in response.content:
                    decoded_line = line.decode("utf-8").strip()
                    if not decoded_line:  # Skip empty lines
                        continue
                    if self.debug:
                        print(f"Raw streamed data: {decoded_line}")
                    # Directly yield lines that start with 'data: '
                    if decoded_line.startswith("data: "):
                        yield decoded_line + "\n\n"  # SSE requires an additional newline
                    else:
                        if self.debug:
                            print("Streamed line doesn't start with 'data: '")
