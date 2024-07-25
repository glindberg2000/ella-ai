# gmail_test.py

import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')

if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
    logger.error("Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables")
    sys.exit(1)

logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

if MEMGPT_TOOLS_PATH not in sys.path:
    sys.path.append(MEMGPT_TOOLS_PATH)

GMAIL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gmail_token.json')
GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

logger.debug(f"GMAIL_TOKEN_PATH: {GMAIL_TOKEN_PATH}")
logger.debug(f"GOOGLE_CREDENTIALS_PATH: {GOOGLE_CREDENTIALS_PATH}")

# Now import the Gmail service functions
from gmail_service import poll_gmail_notifications

async def test_gmail_service():
    logger.info("Starting Gmail service test...")
    try:
        # Run the polling function for a short time (e.g., 60 seconds)
        polling_task = asyncio.create_task(poll_gmail_notifications())
        await asyncio.sleep(60)
        polling_task.cancel()
        
        try:
            await polling_task
        except asyncio.CancelledError:
            logger.info("Gmail polling task cancelled successfully.")
        
        logger.info("Gmail service test completed successfully.")
    except Exception as e:
        logger.error(f"Error during Gmail service test: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_gmail_service())