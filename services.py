from fastapi import FastAPI
from contextlib import asynccontextmanager
from vapi_server import vapi_app_lifespan, vapi_app  # Renamed imports for clarity

app = FastAPI()

# Lifespan context for the main application
@asynccontextmanager
async def main_lifespan(app: FastAPI):
    print("Main app startup tasks")
    # Trigger the vapi_app's lifespan context manually
    async with vapi_app_lifespan(vapi_app):
        print("VAPI app lifespan context managed by main app")
        yield
    print("Main app cleanup tasks")

app.router.lifespan_context = main_lifespan

app.mount("/vapi", vapi_app)  # More descriptive mounting path
