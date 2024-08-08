# services.py
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager, AsyncExitStack
import asyncio
import logging
import os
from dotenv import load_dotenv

# Import service modules
from vapi_service import vapi_app, vapi_app_lifespan
from gmail_service import gmail_app, gmail_app_lifespan, poll_gmail_notifications
from reminder_service import reminder_app, reminder_app_lifespan

# Optionally import Twilio service (commented out for now)
# from twilio_service import twilio_app, twilio_app_lifespan

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Main FastAPI app
app = FastAPI()

# Service configuration
ENABLED_SERVICES = {
    "vapi": True,
    "gmail": False,
    "reminder": False,
    "twilio": False  # Set to True when ready to enable
}

@asynccontextmanager
async def main_lifespan(app: FastAPI):
    """Lifespan context manager for the main app."""
    logger.info("Main app startup tasks")
    background_tasks = BackgroundTasks()
    
    context_managers = []
    tasks = {}

    # VAPI Service
    if ENABLED_SERVICES["vapi"]:
        context_managers.append(vapi_app_lifespan(vapi_app))
    
    # Gmail Service
    if ENABLED_SERVICES["gmail"]:
        context_managers.append(gmail_app_lifespan(gmail_app))
        tasks["gmail_task"] = asyncio.create_task(poll_gmail_notifications())
    
    # Reminder Service
    if ENABLED_SERVICES["reminder"]:
        context_managers.append(reminder_app_lifespan(reminder_app))
    
    # Twilio Service (commented out for now)
    # if ENABLED_SERVICES["twilio"]:
    #     context_managers.append(twilio_app_lifespan(twilio_app))

    async with AsyncExitStack() as stack:
        for cm in context_managers:
            await stack.enter_async_context(cm)
        
        for service, enabled in ENABLED_SERVICES.items():
            if enabled:
                logger.info(f"{service.upper()} app lifespan managed by main app")

        yield tasks

    logger.info("Main app cleanup tasks")
    for task in tasks.values():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

# Set the lifespan context for the main app
app.router.lifespan_context = main_lifespan

# Mount enabled services
if ENABLED_SERVICES["vapi"]:
    app.mount("/vapi", vapi_app)
if ENABLED_SERVICES["gmail"]:
    app.mount("/gmail", gmail_app)
if ENABLED_SERVICES["reminder"]:
    app.mount("/reminder", reminder_app)
# if ENABLED_SERVICES["twilio"]:
#     app.mount("/twilio", twilio_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("SERVICES_PORT", "9090")))