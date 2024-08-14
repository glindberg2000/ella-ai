import asyncio
import logging
from dotenv import load_dotenv
from gmail_service import poll_gmail_notifications

# Load environment variables from .env file
load_dotenv()

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Gmail polling test")
    await poll_gmail_notifications()

if __name__ == "__main__":
    asyncio.run(main())
