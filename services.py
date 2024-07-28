from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
import asyncio
# Import other existing apps
from vapi_service import vapi_app_lifespan, vapi_app
from twilio_service import twilio_app_lifespan, twilio_app
from gmail_service import gmail_app_lifespan, gmail_app, poll_gmail_notifications

app = FastAPI()

@asynccontextmanager
async def main_lifespan(app: FastAPI):
    """
    Lifespan context manager for the main app.
    """
    print("Main app startup tasks")
    background_tasks = BackgroundTasks()
    
    async with vapi_app_lifespan(vapi_app):
        print("VAPI app lifespan context managed by main app")
        async with twilio_app_lifespan(twilio_app):
            print("Twilio app lifespan context managed by main app")
            async with gmail_app_lifespan(gmail_app) as gmail_context:
                print("Gmail app lifespan context managed by main app")
                gmail_task = asyncio.create_task(poll_gmail_notifications())
                yield {"gmail_task": gmail_task}
    
    print("Main app cleanup tasks")
    if 'gmail_task' in locals():
        gmail_task.cancel()
        try:
            await gmail_task
        except asyncio.CancelledError:
            pass

app.router.lifespan_context = main_lifespan


# Mount the services
app.mount("/vapi", vapi_app)
app.mount("/twilio", twilio_app)
app.mount("/gmail", gmail_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9090)
