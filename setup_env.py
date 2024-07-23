# setup_env.py
import os
from dotenv import load_dotenv, set_key

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
    set_key(env_path, "DB_PATH", os.path.join(project_root, "ella_dbo"))
    set_key(env_path, "CREDENTIALS_PATH", os.path.join(project_root, "ella_memgpt","credentials"))

    print(f"Environment file updated at {env_path}")

if __name__ == "__main__":
    setup_env()