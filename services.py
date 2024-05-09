from fastapi import FastAPI
from contextlib import asynccontextmanager

# Import other existing apps
from vapi_service import vapi_app_lifespan, vapi_app
from twilio_service import twilio_app_lifespan, twilio_app
# Import Gmail service and its lifespan
from gmail_service import gmail_app_lifespan, gmail_app

app = FastAPI()

# Lifespan context for the main application
@asynccontextmanager
async def main_lifespan(app: FastAPI):
    print("Main app startup tasks")
    async with vapi_app_lifespan(vapi_app):
        print("VAPI app lifespan context managed by main app")
        async with twilio_app_lifespan(twilio_app):
            print("Twilio app lifespan context managed by main app")
            async with gmail_app_lifespan(gmail_app):
                print("Gmail app lifespan context managed by main app")
                yield
    print("Main app cleanup tasks")

# Set the lifespan context for the main app
app.router.lifespan_context = main_lifespan

# Mount the VAPI service
app.mount("/vapi", vapi_app)

# Mount the Twilio service
app.mount("/twilio", twilio_app)

# Mount the Gmail service
app.mount("/gmail", gmail_app)
