from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Event(BaseModel):
    id: Optional[str] = None
    summary: str
    description: Optional[str] = None
    start: Dict[str, Any]
    end: Dict[str, Any]
    location: Optional[str] = None
    reminders: Optional[Dict[str, Any]] = None
    recurrence: Optional[List[str]] = None
    local_timezone: Optional[str] = None

class ConflictInfo(BaseModel):
    message: str
    conflicts: List[Dict[str, Any]]
    available_slots: List[Dict[str, Any]]

class EventResponse(BaseModel):
    success: bool
    event: Optional[Event] = None
    conflict_info: Optional[ConflictInfo] = None

class ScheduleEventRequest(BaseModel):
    user_id: str
    event: Event

class UpdateEventData(BaseModel):
    summary: Optional[str] = None
    start: Optional[Dict[str, Any]] = None
    end: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    location: Optional[str] = None
    reminders: Optional[Dict[str, Any]] = None
    recurrence: Optional[List[str]] = None

class UpdateEventRequest(BaseModel):
    user_id: str
    event: UpdateEventData
    update_series: bool = False

class ReminderRequest(BaseModel):
    user_id: str
    event_id: str
    event_summary: str
    event_start: str
    event_end: str
    event_description: Optional[str] = None
    reminder_type: str
    minutes_before: int

class EmailRequest(BaseModel):
    user_id: str = Field(..., description="The unique identifier of the user to whom the email will be sent")
    subject: str = Field(..., description="The subject line of the email")
    body: str = Field(..., description="The main content of the email")
    message_id: Optional[str] = Field(None, description="An optional message ID for threading replies")