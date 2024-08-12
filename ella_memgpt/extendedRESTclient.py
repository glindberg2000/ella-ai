import json
import aiohttp
from memgpt.client.client import RESTClient
import logging
import uuid
from typing import Dict, List, Union, Optional, Tuple, Any


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

    def validate_token(self, token: str):
        """Validate the provided token."""
        if not token or len(token) < 10:  # Basic check for non-empty tokens
            raise ValueError("Invalid or missing token.")

    async def send_message_to_agent_streamed(self, agent_id, message):
        self.validate_token(self.token)  # Ensure the token is valid
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

    # Rest of your class methods...

    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None


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

    def inject_special_prompts(self, message: str) -> str:
        """
        Injects special prompts or instructions into the message before sending.
        
        Args:
            message (str): The original message content.
        
        Returns:
            str: The modified message with special prompts.
        """
        special_prompt = "[Special Instruction]: "
        return f"{special_prompt}{message}"

    async def update_agent_memory(self, agent_id: str, memgpt_user_id: str, new_memory_contents: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the agent's core memory with the specified details.

        Args:
            agent_id (str): The agent's ID.
            memgpt_user_id (str): The user ID.
            new_memory_contents (Dict[str, Any]): New memory contents to be updated.

        Returns:
            Dict[str, Any]: The updated agent memory.
        """
        try:
            # Fetch the existing memory
            agent_memory = self.get_agent_memory(agent_id)
            self.logger.info(f"Existing Agent Memory: {agent_memory}")

            # Merge new memory contents
            if new_memory_contents:
                updated_memory = self.update_agent_core_memory(agent_id, new_memory_contents)
                self.logger.info(f"Updated Agent Core Memory: {updated_memory}")
                return updated_memory
            else:
                self.logger.info("No changes required for agent memory.")
                return agent_memory
        except Exception as e:
            self.logger.error(f"Error updating agent memory: {str(e)}")
            raise e

    async def manage_agent_state(self, agent_id: str, user_id: str) -> None:
        try:
            self.validate_token(self.token)  # Validate the token

            # Fetch the agent state (or any other necessary information)
            agent_state = self.get_agent(agent_id=agent_id)
            self.logger.info(f"Managing state for agent {agent_id} and user {user_id}")

            # Perform necessary updates or checks on the state
            special_instructions = f"User ID: {user_id}"
            self.logger.debug(f"Injecting special instructions: {special_instructions}")

            # Update agent memory if necessary
            new_memory_contents = {
                "instructions": special_instructions
            }
            await self.update_agent_memory(agent_id, user_id, new_memory_contents)

        except Exception as e:
            self.logger.error(f"Error managing agent state: {str(e)}")
            raise e  # Re-raise the exception to handle it in the caller

# import json

# import aiohttp
# from memgpt.client.client import RESTClient
# import logging
# import uuid
# from typing import Dict, List, Union, Optional, Tuple

# # Configure logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# class ExtendedRESTClient(RESTClient):
#     def __init__(self, base_url: str, token: str, debug: bool = False):
#         super().__init__(base_url=base_url, token=token, debug=debug)
#         self.token = token
#         self.session = None
#         self.logger = logging.getLogger(__name__)
#         if debug:
#             self.logger.setLevel(logging.DEBUG)
#         self.logger.debug(f"Token set in ExtendedRESTClient: {self.token}")

#     async def send_message_to_agent_streamed(self, agent_id, message):
#         url = f"{self.base_url}/api/agents/{agent_id}/messages"
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {self.token}",
#         }
#         payload = {
#             "agent_id": agent_id,
#             "message": message,
#             "stream": True,
#             "role": "user",
#         }
#         if self.debug:
#             self.logger.debug(f"Payload for agent {agent_id}: {payload}")
        
#         async with aiohttp.ClientSession() as session:
#             async with session.post(url, json=payload, headers=headers) as response:
#                 self.logger.debug(f"Response status: {response.status}")
#                 async for line in response.content:
#                     decoded_line = line.decode("utf-8").strip()
#                     if not decoded_line:  # Skip empty lines
#                         continue
#                     if self.debug:
#                         self.logger.debug(f"Raw streamed data: {decoded_line}")
#                     if decoded_line.startswith("data: "):
#                         yield decoded_line + "\n\n"  # SSE requires an additional newline
#                     else:
#                         self.logger.warning("Streamed line doesn't start with 'data: '")

#     async def get_session(self):
#             if not self.session:
#                 self.session = aiohttp.ClientSession(headers=self.headers)
#             return self.session

#     async def aget_messages(self, agent_id: uuid.UUID, before: Optional[uuid.UUID] = None, after: Optional[uuid.UUID] = None, limit: Optional[int] = 1000):
#         session = await self.get_session()
#         params = {"before": before, "after": after, "limit": limit}
#         async with session.get(f"{self.base_url}/api/agents/{agent_id}/messages-cursor", params=params) as response:
#             return await response.json()

#     async def asend_message(self, agent_id: uuid.UUID, message: str, role: str, stream: Optional[bool] = False):
#         session = await self.get_session()
#         data = {"message": message, "role": role, "stream": stream}
#         async with session.post(f"{self.base_url}/api/agents/{agent_id}/messages", json=data) as response:
#             return await response.json()

#     async def close(self):
#         if self.session:
#             await self.session.close()
#             self.session = None