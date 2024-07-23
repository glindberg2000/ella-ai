# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
ELLA_AI_ROOT = os.getenv('ELLA_AI_ROOT')
MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
DB_PATH = os.getenv('DB_PATH')
CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')

# Derived paths
GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

# Other configuration variables can be added here