import json

import aiohttp
from memgpt.client.client import RESTClient
import logging
import uuid
from typing import Dict, List, Union, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ExtendedRESTClient(RESTClient):
    def __init__(self, base_url: str, token: str, debug: bool = False):
        super().__init__(base_url=base_url, token=token, debug=debug)
        self.token = token
        self.session = None
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        self.logger.debug(f"Token set in ExtendedRESTClient: {self.token}")

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
            self.logger.debug(f"Payload for agent {agent_id}: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                self.logger.debug(f"Response status: {response.status}")
                async for line in response.content:
                    decoded_line = line.decode("utf-8").strip()
                    if not decoded_line:  # Skip empty lines
                        continue
                    if self.debug:
                        self.logger.debug(f"Raw streamed data: {decoded_line}")
                    if decoded_line.startswith("data: "):
                        yield decoded_line + "\n\n"  # SSE requires an additional newline
                    else:
                        self.logger.warning("Streamed line doesn't start with 'data: '")

    async def get_session(self):
            if not self.session:
                self.session = aiohttp.ClientSession(headers=self.headers)
            return self.session

    async def aget_messages(self, agent_id: uuid.UUID, before: Optional[uuid.UUID] = None, after: Optional[uuid.UUID] = None, limit: Optional[int] = 1000):
        session = await self.get_session()
        params = {"before": before, "after": after, "limit": limit}
        async with session.get(f"{self.base_url}/api/agents/{agent_id}/messages-cursor", params=params) as response:
            return await response.json()

    async def asend_message(self, agent_id: uuid.UUID, message: str, role: str, stream: Optional[bool] = False):
        session = await self.get_session()
        data = {"message": message, "role": role, "stream": stream}
        async with session.post(f"{self.base_url}/api/agents/{agent_id}/messages", json=data) as response:
            return await response.json()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None