import logging
from memgpt import create_client
from memgpt.agent import Agent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def print_tool(self: Agent, message: str) -> str:
    """
    A simple tool that prints a message and returns it.
    """
    print(message)
    return message

def main():
    logging.info("Creating MemGPT client...")
    client = create_client()

    logging.info("Creating a new tool...")
    try:
        tool = client.create_tool(print_tool, update=False)
        logging.info(f"Created tool: {tool.name}")
    except Exception as e:
        logging.error(f"Failed to create tool: {str(e)}")

    logging.info("\nListing existing tools:")
    try:
        tools = client.list_tools()
        for i, t in enumerate(tools, 1):
            logging.info(f"{i}. {t.name} (ID: {t.id})")
    except Exception as e:
        logging.error(f"Failed to list tools: {str(e)}")

    # Option to delete test tools
    delete_option = input("\nWould you like to delete test tools? (yes/no): ").lower()
    if delete_option == 'yes':
        for tool in tools:
            if tool.name.startswith(('custom_tool_', 'print_tool')):
                try:
                    client.delete_tool(tool.name)
                    logging.info(f"Deleted tool: {tool.name}")
                except Exception as e:
                    logging.error(f"Failed to delete tool {tool.name}: {str(e)}")
        
        logging.info("\nUpdated tool list:")
        updated_tools = client.list_tools()
        for i, t in enumerate(updated_tools, 1):
            logging.info(f"{i}. {t.name} (ID: {t.id})")
    else:
        logging.info("No tools were deleted.")

if __name__ == "__main__":
    main()