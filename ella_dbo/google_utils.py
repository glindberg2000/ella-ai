try:
    from db_manager import (
        create_connection,
        get_user_data_by_field,
        upsert_user,
        close_connection
    )
    print("Successfully imported from db_manager located in ella_ai/ella_dbo from google_utils")
except ImportError as e:
    print("Error: Unable to import db_manager from google utils. Check your path and module structure.")
    raise e





import logging
 #Configure logging at the start of your application
logging.basicConfig(
    level=logging.INFO,  # Adjust the logging level as needed
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Setup logger
logger = logging.getLogger(__name__)

def get_or_create_user_calendar(service, user_id: str) -> str:
    calendar_summary = f"User-{user_id}-Calendar"
    calendars = service.calendarList().list().execute()
    for calendar in calendars["items"]:
        if calendar["summary"] == calendar_summary:
            logger.info(f"Calendar {calendar_summary} already exists.")
            return calendar["id"]
    new_calendar = {"summary": calendar_summary, "timeZone": "America/Los_Angeles"}
    created_calendar = service.calendars().insert(body=new_calendar).execute()

    # Upsert the updated user data into the database
    conn=create_connection()
    upsert_user(
        conn,
        "memgpt_user_id",
        user_id,
        calendar_id=created_calendar["id"]
    )
    close_connection(conn)
    logger.info(f"Successfully created calendar {created_calendar['id']}")
    return created_calendar["id"]

# def set_calendar_permissions(service, calendar_id, user_email):
#     acl_rule = {'scope': {'type': 'user', 'value': user_email}, 'role': 'writer'}
#     service.acl().insert(calendarId=calendar_id, body=acl_rule).execute()
#     logger.info(f"Successfully shared calendar {calendar_id} with user {user_email}")

# def get_user_email(user_id: str) -> Optional[str]:
#     conn = create_connection()
#     try:
#         user_data = get_user_data_by_field(conn, 'memgpt_user_id', user_id)
#         email = user_data.get('email', None)
#         return email
#     finally:
#         close_connection(conn)

# def create_calendar_event(service, calendar_id, title, start, end, description):
#     event = {
#         "summary": title,
#         "start": {"dateTime": start, "timeZone": "America/Los_Angeles"},
#         "end": {"dateTime": end, "timeZone": "America/Los_Angeles"}
#     }
#     if description:
#         event["description"] = description
#     created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
#     return created_event.get('htmlLink')

# def get_user_calendar(service, user_id: str) -> str:
#     calendar_summary = f"User-{user_id}-Calendar"
#     calendars = service.calendarList().list().execute()
#     for calendar in calendars["items"]:
#         if calendar["summary"] == calendar_summary:
#             return calendar["id"]
#     raise ValueError(f"Calendar for user '{user_id}' not found!")