import asyncio
from logic_module import GoogleUtils
from db_manager import create_connection, get_all_active_users, close_connection
from notification_system import send_notification

async def check_calendar_reminders():
    conn = create_connection()
    try:
        active_users = get_all_active_users(conn)
        for user in active_users:
            utils = GoogleUtils(user['memgpt_user_id'])
            reminders = utils.check_upcoming_reminders()
            for reminder in reminders:
                await trigger_reminder(user['memgpt_user_id'], reminder)
    finally:
        close_connection(conn)

async def trigger_reminder(user_id, reminder):
    notification_data = {
        'user_id': user_id,
        'event_summary': reminder['summary'],
        'event_start': reminder['start'],
        'reminder_minutes': reminder['reminder_minutes']
    }
    await send_notification(notification_data)

async def run_reminder_service():
    while True:
        await check_calendar_reminders()
        await asyncio.sleep(300)  # Check every 5 minutes