# agent_creation.py

import logging
import os
from memgpt.memory import ChatMemory
from ella_memgpt.tools.custom_tools import CUSTOM_TOOLS
from memgpt.constants import DEFAULT_HUMAN, DEFAULT_PERSONA
default_preset = os.getenv('DEFAULT_PRESET', 'ella_3')

def read_file_contents(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {str(e)}")
        return None

def create_custom_tools(user_api):
    created_tools = []
    for tool in CUSTOM_TOOLS:
        try:
            created_tool = user_api.create_tool(tool, name=tool.__name__, update=False)
            created_tools.append(created_tool.name)
            logging.info(f"Created custom tool: {created_tool.name}")
        except Exception as e:
            logging.error(f"Failed to create custom tool {tool.__name__}: {str(e)}")
    return created_tools

def handle_default_agent(memgpt_user_id, user_api):
    logging.info(f"Checking for default agent for user {memgpt_user_id}")
    try:
        agent_info = user_api.list_agents()
        
        if not agent_info.num_agents:
            logging.info(f"No agents found for user {memgpt_user_id}, creating default agent")
            
            # Read the contents of the persona and human templates
            base_dir = os.path.expanduser("~/.memgpt")
            human_content = read_file_contents(os.path.join(base_dir, "humans", "plato.txt"))
            persona_content = read_file_contents(os.path.join(base_dir, "personas", "ella_persona.txt"))
            
            if human_content is None or persona_content is None:
                logging.error("Failed to read human or persona files.")
                raise FileNotFoundError("Required template files are missing.")
            
            # Create a ChatMemory instance with the contents of the templates
            memory = ChatMemory(
                human=human_content or DEFAULT_HUMAN,
                persona=persona_content or DEFAULT_PERSONA
            )
            
            # Create custom tools
            custom_tools = create_custom_tools(user_api)
            
            # Now create the agent with the tools
            agent_state = user_api.create_agent(
                name="Default Agent",
                preset=default_preset,
                memory=memory,
                metadata={"human": human_content, "persona": persona_content},
                tools=custom_tools  # Add the tools to the agent at creation time
            )
            default_agent_key = agent_state.id
            logging.info(f"Created default agent {default_agent_key} for user {memgpt_user_id} with custom tools")
            
            # Verify tool creation
            all_tools = user_api.list_tools()
            created_tool_names = set(custom_tools)
            verified_tools = [t.name for t in all_tools if t.name in created_tool_names]
            if verified_tools:
                logging.info(f"Successfully verified creation of tools: {', '.join(verified_tools)}")
            else:
                logging.warning(f"Custom tool creation verification failed")
            
        else:
            default_agent_key = agent_info.agents[0].id
            logging.info(f"Existing agent found for user {memgpt_user_id}. Using agent: {default_agent_key}")
        
        return default_agent_key
    
    except Exception as e:
        logging.error(f"An error occurred while handling agent data for user {memgpt_user_id}: {e}")
        raise
