import logging
import os
import asyncio
from ella_memgpt.extendedRESTclient import ExtendedRESTClient
from memgpt.client.admin import Admin as AdminRESTClient
from memgpt.agent import Agent
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = os.getenv("MEMGPT_API_URL", "http://localhost:8080")
master_api_key = os.getenv("MEMGPT_SERVER_PASS", "ilovememgpt1")

BASE_TOOLS = [
    "archival_memory_insert", "archival_memory_search", "conversation_search",
    "conversation_search_date", "pause_heartbeats", "send_message",
    "core_memory_append", "core_memory_replace"
]

def custom_tool(self: Agent, param: str) -> str:
    """
    A custom tool that echoes the input parameter.

    Args:
        param (str): The input parameter.

    Returns:
        str: The echoed input parameter.
    """
    return f"Custom tool echoed: {param}"

def display_tool_info(tool):
    logging.info(f"Tool Name: {tool.name}")
    logging.info(f"Tool ID: {tool.id}")
    logging.info(f"Description: {tool.json_schema.get('description', 'No description provided')}")
    logging.info(f"Parameters: {json.dumps(tool.json_schema.get('parameters', {}), indent=2)}")
    logging.info(f"User ID: {tool.user_id or 'Not specified'}")

async def test_tool_with_agent(user_client, agent_id, message):
    logging.info("\nTesting custom tool with agent:")
    try:
        async for response in user_client.send_message_to_agent_streamed(agent_id, message):
            if isinstance(response, str) and response.startswith("data: "):
                data_content = response[6:]
                response = json.loads(data_content)
            
            if "function_call" in response:
                logging.info(f"Agent called function: {response['function_call']}")
            elif "function_return" in response:
                logging.info(f"Function return: {response['function_return']}")
            elif "assistant_message" in response:
                logging.info(f"Assistant response: {response['assistant_message']}")
    except Exception as e:
        logging.error(f"Error testing echo_tool with agent: {str(e)}")

async def main():
    # Create Admin client
    admin_api = AdminRESTClient(BASE_URL, master_api_key)

    # Create a new user
    memgpt_user = admin_api.create_user()
    memgpt_user_id = str(memgpt_user.user_id)
    memgpt_user_api_key = memgpt_user.api_key
    logging.info(f"New memgpt user created: {memgpt_user_id}")

    # Create user client
    user_client = ExtendedRESTClient(BASE_URL, memgpt_user_api_key)

    # Create a default agent for the user
    agent = user_client.create_agent(name="DefaultAgent")
    logging.info(f"Created default agent with ID: {agent.id}")

    logging.info("Creating a new custom tool...")
    try:
        tool = user_client.create_tool(custom_tool, name="echo_tool", update=False)
        logging.info("Custom tool created successfully. Details:")
        display_tool_info(tool)
    except Exception as e:
        logging.error(f"Failed to create custom tool: {str(e)}")

    logging.info("\nListing custom tools:")
    try:
        tools = user_client.list_tools()
        custom_tools = [t for t in tools if t.name not in BASE_TOOLS]
        for i, t in enumerate(custom_tools, 1):
            logging.info(f"\nCustom Tool {i}:")
            display_tool_info(t)
    except Exception as e:
        logging.error(f"Failed to list tools: {str(e)}")

    # Attempt to use the custom tool with the agent
    await test_tool_with_agent(user_client, agent.id, "Use the echo_tool with the parameter 'Hello, World!'")

    delete_option = input("\nWould you like to delete custom tools and the test agent? (yes/no): ").lower()
    if delete_option == 'yes':
        for tool in custom_tools:
            try:
                user_client.delete_tool(tool.id)
                logging.info(f"Deleted custom tool: {tool.name}")
            except Exception as e:
                logging.error(f"Failed to delete tool {tool.name}: {str(e)}")
        
        try:
            user_client.delete_agent(agent.id)
            logging.info(f"Deleted test agent: {agent.id}")
        except Exception as e:
            logging.error(f"Failed to delete agent {agent.id}: {str(e)}")
        
        logging.info("\nUpdated custom tool list:")
        updated_tools = [t for t in user_client.list_tools() if t.name not in BASE_TOOLS]
        for i, t in enumerate(updated_tools, 1):
            logging.info(f"{i}. {t.name} (ID: {t.id})")
    else:
        logging.info("No custom tools or test agent were deleted.")

if __name__ == "__main__":
    asyncio.run(main())