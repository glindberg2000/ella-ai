import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
from dotenv import load_dotenv
import pytz



# Load environment variables
load_dotenv()

# Add the current directory and parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import modules
from utils import UserDataManager, EventManagementUtils
from ella_dbo.models import Event, ConflictInfo, EventResponse, ScheduleEventRequest, UpdateEventData, UpdateEventRequest, ReminderRequest, EmailRequest
from memgpt_email_router import email_router

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI()

# Simple API key authentication
API_KEY = os.getenv("API_KEY")  # Load API_KEY from environment variables

def get_api_key(api_key: str = Header(..., alias="X-API-Key")):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

# Example endpoints go here

# Simple API key authentication
API_KEY = "your-secret-api-key"  # In a real application, store this securely


def get_api_key(api_key: str = Header(..., alias="X-API-Key")):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

app = FastAPI()

@app.post("/schedule_event", response_model=EventResponse)
async def schedule_event(request: ScheduleEventRequest, api_key: str = Depends(get_api_key)):
    logger.debug(f"Received request to schedule event: {request}")
    try:
        logger.info(f"Scheduling event for user {request.user_id}: {request.event.summary}")
        
        # Fetch user data
        user_data = UserDataManager.get_user_data(request.user_id)
        if not user_data:
            logger.error(f"User not found: {request.user_id}")
            raise HTTPException(status_code=404, detail=f"User not found: {request.user_id}")

        logger.debug(f"User data retrieved: {user_data}")

        # Prepare event data
        event_data = request.event.model_dump(exclude_unset=True)
        
        # Ensure timezone is a string and set it if not provided
        user_timezone = user_data.get('local_timezone', 'UTC')
        if user_timezone not in pytz.all_timezones:
            logger.warning(f"Invalid user timezone: {user_timezone}. Defaulting to UTC.")
            user_timezone = 'UTC'

        for time_field in ['start', 'end']:
            if 'dateTime' in event_data[time_field]:
                if 'timeZone' not in event_data[time_field]:
                    event_data[time_field]['timeZone'] = user_timezone
                event_data[time_field]['timeZone'] = str(event_data[time_field]['timeZone'])

        logger.debug(f"Prepared event data: {event_data}")
        
        # Schedule the event
        result = await EventManagementUtils.schedule_event(request.user_id, event_data, user_data)
        logger.debug(f"Schedule event result: {result}")
        
        if result["success"]:
            logger.info(f"Event scheduled successfully: {result['event']['id']}")
            return EventResponse(success=True, event=Event(**result["event"]))
        else:
            logger.warning(f"Failed to schedule event: {result['message']}")
            if 'conflicts' in result:
                return EventResponse(
                    success=False,
                    conflict_info=ConflictInfo(
                        message=result['message'],
                        conflicts=result['conflicts'],
                        available_slots=result['available_slots']
                    )
                )
            else:
                raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        logger.error(f"Unexpected error scheduling event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/events", response_model=List[Event])
async def fetch_events(
    user_id: str,
    max_results: int = 10,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    api_key: str = Depends(get_api_key)
):
    try:
        user_data = UserDataManager.get_user_data(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

        result = await EventManagementUtils.fetch_events(
            user_id,
            max_results=max_results,
            time_min=time_min,
            time_max=time_max,
            local_timezone=user_data.get('local_timezone')
        )

        if result["success"]:
            return [Event(**event) for event in result["events"]]
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        logger.error(f"Unexpected error fetching events: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    user_id: str,
    delete_series: bool = False,
    api_key: str = Depends(get_api_key)
):
    try:
        user_data = UserDataManager.get_user_data(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

        result = await EventManagementUtils.delete_event(
            user_id,
            event_id,
            delete_series=delete_series
        )

        if "Error" in result or "Failed" in result:
            raise HTTPException(status_code=400, detail=result)
        else:
            return {"success": True, "message": result}
    except Exception as e:
        logger.error(f"Unexpected error deleting event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.put("/events/{event_id}")
async def update_event(
    event_id: str,
    request: UpdateEventRequest,
    api_key: str = Depends(get_api_key)
):
    try:
        user_data = UserDataManager.get_user_data(request.user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail=f"User not found: {request.user_id}")

        result = await EventManagementUtils.update_event(
            request.user_id,
            event_id,
            title=request.event.summary,
            start=request.event.start,
            end=request.event.end,
            description=request.event.description,
            location=request.event.location,
            reminders=request.event.reminders,
            recurrence=request.event.recurrence,
            update_series=request.update_series,
            local_timezone=user_data.get('local_timezone')
        )

        result_dict = json.loads(result)
        if result_dict["success"]:
            return EventResponse(success=True, event=Event(**result_dict["event"]))
        else:
            return EventResponse(
                success=False,
                conflict_info=ConflictInfo(
                    message=result_dict["message"],
                    conflicts=result_dict.get("conflicts", []),
                    available_slots=result_dict.get("available_slots", [])
                )
            )
    except Exception as e:
        logger.error(f"Unexpected error updating event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
@app.post("/send_email")
async def send_email(request: EmailRequest):
    logger.info(f"Received request to send email for user: {request.user_id}")
    try:
        # Fetch user data
        user_data = UserDataManager.get_user_data(request.user_id)
        if not user_data:
            logger.error(f"User not found: {request.user_id}")
            raise HTTPException(status_code=404, detail=f"User not found: {request.user_id}")

        # Get user's email from user data
        to_email = user_data.get('email')
        if not to_email:
            logger.error(f"Email not found for user: {request.user_id}")
            raise HTTPException(status_code=400, detail="User email not found")

        # Send the email using the enhanced direct send method
        result = await email_router.send_direct_email(
            to_email=to_email,
            subject=request.subject,
            body=request.body,
            message_id=request.message_id
        )
        
        if result["status"] == "success":
            logger.info(f"Email sent successfully to: {to_email}")
            return {"success": True, "message": "Email sent successfully", "message_id": result["message_id"]}
        else:
            logger.error(f"Failed to send email: {result['message']}")
            raise HTTPException(status_code=500, detail=result["message"])
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}", exc_info=True)
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "request_data": request.dict()
        }
        raise HTTPException(status_code=500, detail=error_details)
    
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Received request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Returning response: Status {response.status_code}")
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": str(exc)})

@app.post("/send_reminder")
async def send_reminder(reminder: ReminderRequest):
    logger.info(f"Received reminder request: {reminder}")
    try:
        user_data = UserDataManager.get_user_data(reminder.user_id)
        if not user_data:
            logger.error(f"User not found: {reminder.user_id}")
            raise HTTPException(status_code=404, detail=f"User not found: {reminder.user_id}")

        to_email = user_data.get('email')
        memgpt_user_api_key = user_data.get('memgpt_api_key')
        agent_key = user_data.get('agent_key')

        if not to_email:
            logger.error(f"Email not found for user: {reminder.user_id}")
            raise HTTPException(status_code=400, detail="User email not found")

        context = {
            "event_summary": reminder.event_summary,
            "event_start": reminder.event_start,
            "event_end": reminder.event_end,
            "event_description": reminder.event_description,
            "minutes_before": reminder.minutes_before
        }

        result = await email_router.generate_and_send_email(
            to_email=to_email,
            subject=f"Reminder: {reminder.event_summary}",
            context=context,
            memgpt_user_api_key=memgpt_user_api_key,
            agent_key=agent_key,
            is_reply=False
        )

        if result['status'] == 'success':
            return {
                "success": True,
                "message": "Reminder sent successfully",
                "message_id": result.get('message_id'),
                "recipient": to_email
            }
        else:
            raise HTTPException(status_code=500, detail=result['message'])
    except Exception as e:
        logger.error(f"Error in send_reminder endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/debug/user/{user_id}")
async def debug_user_data(user_id: str, api_key: str = Depends(get_api_key)):
    user_data = UserDataManager.get_user_data(user_id)
    if user_data:
        return {"user_found": True, "user_data": user_data}
    else:
        return {"user_found": False}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)},
    )
  
# Assuming you have a function to get user details
async def get_user_details(user_id: str):
    # Implement your logic to fetch user details
    # This is a placeholder implementation

    try:
        load_dotenv()
        
        MEMGPT_TOOLS_PATH = os.getenv('MEMGPT_TOOLS_PATH', '/default/path/to/memgpt/tools')
        CREDENTIALS_PATH = os.getenv('CREDENTIALS_PATH', '/default/path/to/credentials')

        TEST_MEMGPT_USER_ID = os.getenv('TEST_MEMGPT_USER_ID', 'f0236456-a4cc-4cb2-a772-1de0e968126a')
        TEST_MEMGPT_USER_API_KEY = os.getenv('TEST_MEMGPT_USER_API_KEY', 'sk-1d4f74fa77b9d958714772f836b25e01a0f5f2a3d8f35b60')
        TEST_MEMGPT_AGENT_KEY = os.getenv('TEST_MEMGPT_AGENT_KEY', '1dcc1e2c-1ec6-42fb-931b-62e7ab3ee06c')
        TEST_MEMGPT_EMAIL = os.getenv('TEST_MEMGPT_EMAIL', 'doloresabernathy3030@gmail.com')
        return {
            "email": TEST_MEMGPT_EMAIL,
            "memgpt_api_key": TEST_MEMGPT_USER_API_KEY,
            "agent_key": TEST_MEMGPT_AGENT_KEY
        }
        
    except Exception as e:
        print(f"Error loading environment variables: {e}")



@app.get("/")
async def root():
    return {"status": "ok", "message": "EventManagementService is running"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting EventManagementService")
    uvicorn.run(app, host="0.0.0.0", port=9999)