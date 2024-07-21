from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from GoogleUtils import GoogleUtils  # Assuming you have this class
import asyncio

calendar_app = FastAPI()

async def check_calendar_reminders(user_id: str):
    utils = GoogleUtils(user_id)
    events = utils.fetch_upcoming_events(time_min=datetime.now().isoformat())
    for event in events:
        if utils.is_reminder_due(event):
            await utils.trigger_webhook(event)

@asynccontextmanager
async def calendar_app_lifespan(app: FastAPI):
    # Start the background task
    task = asyncio.create_task(run_periodic_check())
    yield
    # Cancel the task when the app is shutting down
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

async def run_periodic_check():
    while True:
        # Replace with actual user IDs or fetch from database
        user_ids = ["user1", "user2", "user3"]
        for user_id in user_ids:
            await check_calendar_reminders(user_id)
        await asyncio.sleep(300)  # Sleep for 5 minutes

calendar_app.router.lifespan_context = calendar_app_lifespan

@calendar_app.get("/check-now/{user_id}")
async def check_now(user_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(check_calendar_reminders, user_id)
    return {"message": "Calendar check initiated"}