import os
from dotenv import load_dotenv, set_key
import sys

def setup_env():
    # Determine the project root
    project_root = os.path.abspath(os.path.dirname(__file__))

    # Path to .env file
    env_path = os.path.join(project_root, '.env')

    # Load existing .env file or create if it doesn't exist
    load_dotenv(env_path)

    # Update or set environment variables
    set_key(env_path, "ELLA_AI_ROOT", project_root)
    set_key(env_path, "MEMGPT_TOOLS_PATH", os.path.join(project_root, "ella_memgpt","tools"))
    set_key(env_path, "VAPI_TOOLS_PATH", os.path.join(project_root, "ella_vapi"))
    set_key(env_path, "DB_PATH", os.path.join(project_root, "ella_dbo"))
    set_key(env_path, "CREDENTIALS_PATH", os.path.join(project_root, "ella_memgpt","credentials"))

    print(f"Environment file updated at {env_path}")

    # Patch constants.py in memgpt package
    patch_memgpt_constants()

def patch_memgpt_constants():
    try:
        # Find the memgpt package path
        import memgpt
        memgpt_path = os.path.dirname(memgpt.__file__)

        # Path to constants.py
        constants_path = os.path.join(memgpt_path, "constants.py")

        # Read the constants.py file
        with open(constants_path, "r") as file:
            lines = file.readlines()

        # Modify the constants
        with open(constants_path, "w") as file:
            for line in lines:
                if "CORE_MEMORY_PERSONA_CHAR_LIMIT" in line:
                    line = "CORE_MEMORY_PERSONA_CHAR_LIMIT = 4000  # 200% of default\n"
                elif "CORE_MEMORY_HUMAN_CHAR_LIMIT" in line:
                    line = "CORE_MEMORY_HUMAN_CHAR_LIMIT = 4000  # 200% of default\n"
                elif "FUNCTION_RETURN_CHAR_LIMIT" in line:
                    line = "FUNCTION_RETURN_CHAR_LIMIT = 6000  # 200% of default\n"
                file.write(line)

        print(f"Patched constants.py at {constants_path}")

    except Exception as e:
        print(f"Failed to patch memgpt/constants.py: {e}")

if __name__ == "__main__":
    setup_env()