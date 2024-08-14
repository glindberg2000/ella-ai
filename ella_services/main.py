# main.py

import os
import sys
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging
import json

# Add the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from utils import EventManagementUtils, UserDataManager

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

# Pydantic models
class Event(BaseModel):
    id: Optional[str] = None
    summary: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    location: Optional[str] = None
    reminders: Optional[str] = None
    recurrence: Optional[str] = None

class ScheduleEventRequest(BaseModel):
    user_id: str
    event: Event

class ConflictInfo(BaseModel):
    message: str
    conflicts: List[dict]
    available_slots: List[dict]

class EventResponse(BaseModel):
    success: bool
    event: Optional[Event] = None
    conflict_info: Optional[ConflictInfo] = None

class UpdateEventData(BaseModel):
    summary: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    reminders: Optional[str] = None
    recurrence: Optional[str] = None

class UpdateEventRequest(BaseModel):
    user_id: str
    event: UpdateEventData
    update_series: bool = False

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
        event_data = request.event.dict(exclude_unset=True)
        event_data['start'] = event_data.pop('start_time')
        event_data['end'] = event_data.pop('end_time')
        if 'id' in event_data:
            del event_data['id']  # Remove id if it's present

        # Handle reminders
        if 'reminders' in event_data:
            try:
                reminders = json.loads(event_data['reminders'])
                event_data['reminders'] = json.dumps(reminders)  # Ensure it's a properly formatted JSON string
            except json.JSONDecodeError:
                logger.warning(f"Invalid reminders format: {event_data['reminders']}")
                del event_data['reminders']  # Remove invalid reminders

        # Schedule the event
        result = await EventManagementUtils.schedule_event(request.user_id, event_data, user_data)
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error scheduling event: {str(e)}", exc_info=True)
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
    
@app.get("/")
async def root():
    return {"message": "EventManagementService is running"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting EventManagementService")
    uvicorn.run(app, host="0.0.0.0", port=9999)