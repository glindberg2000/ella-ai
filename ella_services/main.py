# main.py

import os
import sys
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import json
from memgpt_email_router import email_router
from utils import UserDataManager
from dotenv import load_dotenv


# Add the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils import EventManagementUtils, UserDataManager
from ella_dbo.models import Event, ConflictInfo, EventResponse, ScheduleEventRequest, UpdateEventData, UpdateEventRequest, ReminderRequest, EmailRequest
# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

        # Prepare event data
        event_data = request.event.model_dump(exclude_unset=True)
        logger.debug(f"Prepared event data: {event_data}")
        
        # Schedule the event
        result = await EventManagementUtils.schedule_event(request.user_id, event_data, user_data)
        logger.debug(f"Schedule event result: {result}")
        
        if result["success"]:
            logger.info(f"Event scheduled successfully: {result['event']['id']}")
            # Add local_timezone to the result if it's not present
            if 'local_timezone' not in result['event']:
                result['event']['local_timezone'] = user_data.get('local_timezone', 'UTC')
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
        # Fetch user data using UserDataManager
        user_data = UserDataManager.get_user_data(reminder.user_id)
        if not user_data:
            logger.error(f"User not found: {reminder.user_id}")
            raise HTTPException(status_code=404, detail=f"User not found: {reminder.user_id}")

        # Get user's email and other details from user data
        to_email = user_data.get('email')
        memgpt_user_api_key = user_data.get('memgpt_api_key')
        agent_key = user_data.get('agent_key')

        if not to_email or not memgpt_user_api_key or not agent_key:
            logger.error(f"Incomplete user data for user: {reminder.user_id}")
            raise HTTPException(status_code=400, detail="Incomplete user data")

        subject = f"Reminder: {reminder.event_summary}"
        context = {
            "event_summary": reminder.event_summary,
            "event_start": reminder.event_start,
            "event_end": reminder.event_end,
            "event_description": reminder.event_description,
            "minutes_before": reminder.minutes_before
        }

        logger.info(f"Calling email_router.send_reminder with context: {context}")
        result = await email_router.send_reminder(
            to_email=to_email,
            subject=subject,
            reminder_content=context,
            memgpt_user_api_key=memgpt_user_api_key,
            agent_key=agent_key
        )
        logger.info(f"Result from email_router.send_reminder: {result}")

        if result['status'] == 'success':
            logger.info(f"Reminder sent successfully to {result['to_email']}. Message ID: {result.get('message_id')}")
            return {
                "success": True,
                "message": "Reminder sent successfully",
                "message_id": result.get('message_id'),
                "recipient": result['to_email']
            }
        else:
            error_message = f"Failed to send reminder to {result.get('to_email', 'unknown recipient')}: {result['message']}"
            logger.error(error_message)
            raise HTTPException(status_code=500, detail=error_message)
    except Exception as e:
        error_message = f"Error in send_reminder endpoint: {str(e)}"
        logger.error(error_message, exc_info=True)
        raise HTTPException(status_code=500, detail=error_message)

@app.get("/debug/user/{user_id}")
async def debug_user_data(user_id: str, api_key: str = Depends(get_api_key)):
    user_data = UserDataManager.get_user_data(user_id)
    if user_data:
        return {"user_found": True, "user_data": user_data}
    else:
        return {"user_found": False}
    
# @app.post("/schedule_event", response_model=EventResponse)
# async def schedule_event(request: ScheduleEventRequest, api_key: str = Depends(get_api_key)):
#     logger.debug(f"Received request to schedule event: {request}")
#     try:
#         logger.info(f"Scheduling event for user {request.user_id}: {request.event.summary}")
        
#         # Fetch user data
#         user_data = UserDataManager.get_user_data(request.user_id)
#         if not user_data:
#             logger.error(f"User not found: {request.user_id}")
#             raise HTTPException(status_code=404, detail=f"User not found: {request.user_id}")

#         # Prepare event data
#         event_data = request.event.dict(exclude_unset=True)
#         event_data['start'] = event_data.pop('start_time')
#         event_data['end'] = event_data.pop('end_time')
#         if 'id' in event_data:
#             del event_data['id']  # Remove id if it's present

#         # Handle reminders
#         if 'reminders' in event_data:
#             try:
#                 reminders = json.loads(event_data['reminders'])
#                 event_data['reminders'] = json.dumps(reminders)  # Ensure it's a properly formatted JSON string
#             except json.JSONDecodeError:
#                 logger.warning(f"Invalid reminders format: {event_data['reminders']}")
#                 del event_data['reminders']  # Remove invalid reminders

#         # Schedule the event
#         result = await EventManagementUtils.schedule_event(request.user_id, event_data, user_data)
        
#         if result["success"]:
#            logger.info(f"Event scheduled successfully: {result['event']['id']}")
#            event_data = result["event"]
#            # Transform the data to match the Event model
#            event_data['start'] = event_data.pop('start', {})
#            event_data['end'] = event_data.pop('end', {})
#            return EventResponse(success=True, event=Event(**event_data))
#         else:
#             logger.warning(f"Failed to schedule event: {result['message']}")
#             if 'conflicts' in result:
#                 return EventResponse(
#                     success=False,
#                     conflict_info=ConflictInfo(
#                         message=result['message'],
#                         conflicts=result['conflicts'],
#                         available_slots=result['available_slots']
#                     )
#                 )
#             else:
#                 raise HTTPException(status_code=400, detail=result["message"])
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Unexpected error scheduling event: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

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
            start=request.event.start_time,
            end=request.event.end_time,
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

@app.get("/events")
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
            return result  # Return the entire result dictionary
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        logger.error(f"Unexpected error fetching events: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
       
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)},
    )

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