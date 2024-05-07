from fastapi import FastAPI
from contextlib import asynccontextmanager
from vapi_service import vapi_app_lifespan, vapi_app
from twilio_service import twilio_app_lifespan, twilio_app

app = FastAPI()

# Lifespan context for the main application
@asynccontextmanager
async def main_lifespan(app: FastAPI):
    print("Main app startup tasks")
    async with vapi_app_lifespan(vapi_app):
        print("VAPI app lifespan context managed by main app")
        # Include the lifespan management for the Twilio service
        async with twilio_app_lifespan(twilio_app):
            print("Twilio app lifespan context managed by main app")
            yield
    print("Main app cleanup tasks")

app.router.lifespan_context = main_lifespan

# Mount the VAPI service
app.mount("/vapi", vapi_app)

# Mount the Twilio service
app.mount("/twilio", twilio_app)  # Assuming SMS-related paths should be under '/sms'
