# Enabling API control on Google Calendar requires a few steps:
# https://developers.google.com/calendar/api/quickstart/python
# including:
#   pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

import os
import os.path
import traceback
from typing import Optional
import datetime
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add the ella_dbo path to sys.path
import sys
ella_dbo_path = os.path.expanduser("~/dev/ella-ai/ella_dbo")
sys.path.insert(0, ella_dbo_path)
# Attempt to import the db_manager functions
try:
    from db_manager import (
        create_connection,
        get_user_data_by_field,
        upsert_user,
        close_connection
    )
    print("Successfully imported from db_manager located in ~/dev/ella-ai/ella_dbo.")
except ImportError as e:
    print("Error: Unable to import db_manager. Check your path and module structure.")
    raise e

from helpers import GoogleUtils   

# Configure logging at the start of your application
logging.basicConfig(
    level=logging.INFO,  # Adjust the logging level as needed
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Setup logger
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
# SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = os.path.expanduser("~/.memgpt/gcal_token.json")
CREDENTIALS_PATH = os.path.expanduser("~/.memgpt/google_api_credentials.json")


def schedule_event(
    self,
    user_id: str,
    title: str,
    start: str,
    end: str,
    description: Optional[str] = None
) -> str:
    """
    Schedule an event and grant calendar access to a user.

    Args:
        user_id (str): The user ID used to retrieve the email for sharing.
        title (str): Event name.
        start (str): Event start time in ISO 8601 format.
        end (str): Event end time in ISO 8601 format.
        description (Optional[str]): Description of the event.

    Returns:
        str: Status of the event scheduling request.
    """

    
    def safe_fetch_event_count(user_id):
        results = fetch_upcoming_events(user_id)
        if results and isinstance(results, list):
            # Check if the first item is a dictionary, which indicates event data
            if isinstance(results[0], dict):
                return len(results)  # Return the number of events
            else:
                print("Error in fetching events:", results[0])
        return 0  # Return 0 if there are no events or an error occurs

    utils = GoogleUtils(user_id)

    # Share the calendar if an email address is available
    user_email = utils.get_user_email()
    if user_email:
        utils.set_calendar_permissions()
    else:
        logger.info("No email address available at this time; the calendar will not be shared yet.")

    event_link = utils.create_calendar_event(title, start, end, description)

    #event_count = safe_fetch_event_count(user_id)

    conn = create_connection()
    upsert_user(
        conn,
        "memgpt_user_id",
        user_id,
        event_count=1
    )
    close_connection(conn)


    return f"Event created: {event_link}"

# def fetch_upcoming_events(
#     self,
#     user_id: str,
#     max_results: int = 100,
#     time_min: Optional[str] = None,
# ) -> list:
#     """
#     Fetch upcoming events from a user-specific Google Calendar.

#     Args:
#         user_id (str): A unique identifier associated with each user's calendar.
#         max_results (int): Maximum number of events to retrieve.
#         time_min (Optional[str]): Minimum time filter for events in ISO 8601 format.

#     Returns:
#         list: A list of event summaries, start times, and IDs, or an error message if something goes wrong.
#     """

  
#     utils = GoogleUtils(user_id)

#     creds = None
#     if os.path.exists(TOKEN_PATH):
#         creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
#             creds = flow.run_local_server(port=0)
#         with open(TOKEN_PATH, "w") as token:
#             token.write(creds.to_json())

#     try:
#         service = build("calendar", "v3", credentials=creds)
#         calendar_id = utils.get_or_create_user_calendar(service)

#         # Set default to the current time if not specified
#         if not time_min:
#             # Use timezone-aware datetime object
#             time_min = datetime.datetime.now(datetime.timezone.utc).isoformat()

#         # Fetch events starting from `time_min`
#         events_result = service.events().list(
#             calendarId=calendar_id,
#             timeMin=time_min,
#             maxResults=max_results,
#             singleEvents=True,
#             orderBy="startTime",
#         ).execute()

#         events = events_result.get("items", [])
#         formatted_events = [
#             {
#                 "id": event["id"],
#                 "summary": event.get("summary", "No Title"),
#                 "start": event["start"].get("dateTime", event["start"].get("date")),
#                 "end": event["end"].get("dateTime", event["end"].get("date")),
#                 "description": event.get("description", "No Description"),
#                 "attendees": [attendee["email"] for attendee in event.get("attendees", [])],
#                 "location": event.get("location", "No Location")
#             }
#             for event in events
#         ]

#         return formatted_events

#     except ValueError as error:
#         return [f"An error occurred while trying to fetch events: {str(error)}"]

#     except HttpError as error:
#         traceback.print_exc()
#         return [f"An error occurred while trying to fetch events: {str(error)}"]

def fetch_upcoming_events(
    self,
    user_id: str,
    max_results: int = 100,
    time_min: Optional[str] = None,
) -> list:
    """
    Fetch upcoming events from a user-specific Google Calendar.

    Args:
        user_id (str): A unique identifier associated with each user's calendar.
        max_results (int): Maximum number of events to retrieve. Default is 100.
        time_min (Optional[str]): Minimum time filter for events in ISO 8601 format. 
                                  If not provided, defaults to the current time.

    Returns:
        list: A list of dictionaries containing event details (id, summary, start, end, 
              description, attendees, location), or a list with an error message if 
              something goes wrong.

    Raises:
        ValueError: If there's an issue with the input parameters or calendar setup.
        HttpError: If there's an error in the API request to Google Calendar.
    """
    utils = GoogleUtils(user_id)
    
    try:
        # Set default to the current time if not specified
        if not time_min:
            time_min = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Fetch events starting from `time_min`
        events_result = utils.service.events().list(
            calendarId=utils.calendar_id,
            timeMin=time_min,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        
        events = events_result.get("items", [])
        formatted_events = [
            {
                "id": event["id"],
                "summary": event.get("summary", "No Title"),
                "start": event["start"].get("dateTime", event["start"].get("date")),
                "end": event["end"].get("dateTime", event["end"].get("date")),
                "description": event.get("description", "No Description"),
                "attendees": [attendee["email"] for attendee in event.get("attendees", [])],
                "location": event.get("location", "No Location")
            }
            for event in events
        ]
        return formatted_events
    except ValueError as error:
        return [f"An error occurred while trying to fetch events: {str(error)}"]
    except HttpError as error:
        traceback.print_exc()
        return [f"An error occurred while trying to fetch events: {str(error)}"]
    
def update_event(
    self,
    user_id: str,
    event_id: str,
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """
    Update an existing event on a user-specific Google Calendar.

    Args:
        user_id (str): A unique identifier associated with each user's calendar.
        event_id (str): The unique event identifier obtained during the 'read' operation.
        title (Optional[str]): New event name (if provided).
        start (Optional[str]): New start time in ISO 8601 format.
        end (Optional[str]): New end time in ISO 8601 format.
        description (Optional[str]): New expanded description of the event.

    Returns:
        str: The status of the update request.
    """

    def get_user_calendar(service, user_id: str) -> str:
        calendar_summary = f"User-{user_id}-Calendar"
        calendars = service.calendarList().list().execute()
        for calendar in calendars["items"]:
            if calendar["summary"] == calendar_summary:
                return calendar["id"]
        raise ValueError(f"Calendar for user '{user_id}' not found!")

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        calendar_id = get_user_calendar(service, user_id)

        # Log for debugging
        logger.info(f"Using Calendar ID: {calendar_id}")
        logger.info(f"Updating Event ID: {event_id}")

        # Log all events to help with identifying issues
        events_result = service.events().list(calendarId=calendar_id, maxResults=20).execute()
        all_events = events_result.get("items", [])
        logger.info(f"Total Events in Calendar: {len(all_events)}")

        # Find the specified event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        if title:
            event["summary"] = title
        if start:
            event["start"]["dateTime"] = start
        if end:
            event["end"]["dateTime"] = end
        if description:
            event["description"] = description

        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        logger.info(f"Event updated successfully: {updated_event.get('htmlLink')}")
        return f"Event updated: {updated_event.get('htmlLink')}"

    except ValueError as error:
        logger.error(f"Value error occurred: {error}")
        return f"An error occurred while trying to update the event: {str(error)}"

    except HttpError as error:
        logger.error(f"HTTP error occurred: {error}")
        traceback.print_exc()
        return f"An error occurred while trying to update the event: {str(error)}"

def delete_event(self, user_id: str, event_id: str) -> str:
    """
    Delete an event from a user-specific Google Calendar.

    Args:
        user_id (str): A unique identifier associated with each user's calendar.
        event_id (str): The unique event identifier obtained during the 'read' operation.

    Returns:
        str: The status of the deletion request.
    """

    def get_user_calendar(service, user_id: str) -> str:
        calendar_summary = f"User-{user_id}-Calendar"

        calendars = service.calendarList().list().execute()
        for calendar in calendars["items"]:
            if calendar["summary"] == calendar_summary:
                return calendar["id"]

        raise ValueError(f"Calendar for user '{user_id}' not found!")

    def safe_fetch_event_count(user_id):
        results = fetch_upcoming_events(user_id)
        if results and isinstance(results, list):
            # Check if the first item is a dictionary, which indicates event data
            if isinstance(results[0], dict):
                return len(results)  # Return the number of events
            else:
                print("Error in fetching events:", results[0])
        return 0  # Return 0 if there are no events or an error occurs

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        calendar_id = get_user_calendar(service, user_id)

        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

        #event_count = safe_fetch_event_count(user_id)

        conn = create_connection()
        upsert_user(
            conn,
            "memgpt_user_id",
            user_id,
            event_count=event_count
        )
        close_connection(conn)
        return "Event successfully deleted."

    except ValueError as error:
        return f"An error occurred while trying to delete the event: {str(error)}"

    except HttpError as error:
        traceback.print_exc()
        return f"An error occurred while trying to delete the event: {str(error)}"

def add_attendees_to_event(
    self,
    user_id: str,
    event_id: str,
    attendees_str: str
) -> str:
    """
    Share an existing event by adding attendees.

    Args:
        user_id (str): A unique identifier associated with each user's calendar.
        event_id (str): The unique event identifier obtained during the 'read' operation.
        attendees_str (str): A comma-separated list of email addresses of attendees to invite.

    Returns:
        str: The status of the request.
    """

    def get_user_calendar(service, user_id: str) -> str:
        """Retrieve the calendar ID of the specific user's calendar."""
        calendar_summary = f"User-{user_id}-Calendar"
        calendars = service.calendarList().list().execute()
        for calendar in calendars["items"]:
            if calendar["summary"] == calendar_summary:
                return calendar["id"]
        raise ValueError(f"Calendar for user '{user_id}' not found!")

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        calendar_id = get_user_calendar(service, user_id)

        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

        # Convert the comma-separated string into a list of dictionaries
        attendees = [{"email": email.strip()} for email in attendees_str.split(",") if email.strip()]
        event["attendees"] = attendees

        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        return f"Event updated and shared: {updated_event.get('htmlLink')}"

    except ValueError as error:
        return f"An error occurred while trying to share the event: {str(error)}"

    except HttpError as error:
        traceback.print_exc()
        return f"An error occurred while trying to share the event: {str(error)}"

def share_calendar_with_user(self, user_id: str, email: str) -> str:
    """
    Share a user-specific calendar with another user by adding them to the calendar's ACL.

    Args:
        user_id (str): A unique identifier associated with each user's calendar.
        email (str): The email address of the user to share the calendar with.

    Returns:
        str: The status of the request.
    """

    def get_user_calendar(service, user_id: str) -> str:
        calendar_summary = f"User-{user_id}-Calendar"
        calendars = service.calendarList().list().execute()
        for calendar in calendars["items"]:
            if calendar["summary"] == calendar_summary:
                return calendar["id"]
        raise ValueError(f"Calendar for user '{user_id}' not found!")

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        calendar_id = get_user_calendar(service, user_id)

        acl_rule = {
            "scope": {"type": "user", "value": email},
            "role": "reader",
        }

        service.acl().insert(calendarId=calendar_id, body=acl_rule).execute()
        return f"Calendar shared with {email}."

    except ValueError as error:
        return f"An error occurred while trying to share the calendar: {str(error)}"

    except HttpError as error:
        traceback.print_exc()
        return f"An error occurred while trying to share the calendar: {str(error)}"
