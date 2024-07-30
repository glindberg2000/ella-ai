#!/usr/bin/env python3

import os
import sys
import logging
from dotenv import load_dotenv
from googleapiclient.errors import HttpError

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def cleanup_test_calendars(token_path: str, credentials_path: str):
    try:
        from google_utils import GoogleCalendarUtils

        # Initialize GoogleCalendarUtils
        calendar_utils = GoogleCalendarUtils(token_path, credentials_path)

        # Fetch all calendars
        calendar_list = calendar_utils.service.calendarList().list().execute()

        # Identify and delete test calendars
        for calendar in calendar_list.get('items', []):
            if calendar['summary'].startswith('User-') and calendar['summary'].endswith('-Calendar'):
                try:
                    calendar_utils.service.calendars().delete(calendarId=calendar['id']).execute()
                    logger.info(f"Deleted test calendar: {calendar['summary']}")
                except HttpError as e:
                    if e.resp.status == 404:
                        logger.warning(f"Calendar not found: {calendar['summary']}")
                    else:
                        logger.error(f"Error deleting calendar {calendar['summary']}: {str(e)}")

        logger.info("Cleanup of test calendars completed")
    except Exception as e:
        logger.error(f"Error during cleanup of test calendars: {str(e)}", exc_info=True)

def main():
    try:
        load_dotenv()
        MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH')
        CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH')
        
        if not MEMGPT_TOOLS_PATH or not CREDENTIALS_PATH:
            logger.error("Error: MEMGPT_TOOLS_PATH or CREDENTIALS_PATH not set in environment variables")
            return

        logger.debug(f"MEMGPT_TOOLS_PATH: {MEMGPT_TOOLS_PATH}")
        logger.debug(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

        if MEMGPT_TOOLS_PATH not in sys.path:
            sys.path.append(MEMGPT_TOOLS_PATH)

        GCAL_TOKEN_PATH = os.path.join(CREDENTIALS_PATH, 'gcal_token.json')
        GOOGLE_CREDENTIALS_PATH = os.path.join(CREDENTIALS_PATH, 'google_api_credentials.json')

        # Run the cleanup
        cleanup_test_calendars(GCAL_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH)

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()