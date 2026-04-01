from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ApplicationEventType(str, Enum):
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    APPLICATION_RECEIVED = "APPLICATION_RECEIVED"
    APPLICATION_VIEWED = "APPLICATION_VIEWED"
    APPLICATION_REVIEWED = "APPLICATION_REVIEWED"
    ASSESSMENT_RECEIVED = "ASSESSMENT_RECEIVED"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"
    FINAL_ROUND = "FINAL_ROUND"
    REFERENCE_REQUESTED = "REFERENCE_REQUESTED"
    OFFER_RECEIVED = "OFFER_RECEIVED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    OFFER_DECLINED = "OFFER_DECLINED"
    APPLICATION_REJECTED = "APPLICATION_REJECTED"
    APPLICATION_WITHDRAWN = "APPLICATION_WITHDRAWN"


class ApplicationEventCreate(BaseModel):
    """
    Schema for creating a new ApplicationEvent record in the DB
    """

    application_id: str = Field(..., description="ID of the related job application")
    event_type: ApplicationEventType = Field(
        ..., description="Type of the application event"
    )
    event_date: datetime = Field(..., description="Date/time when the event occurred")
    description: Optional[str] = Field(
        None, description="Optional description of the event"
    )
    location: Optional[str] = Field(
        None, description="Location related to the event, if any"
    )
    contact_person: Optional[str] = Field(
        None, description="Contact person for the event"
    )
    notes: Optional[str] = Field(None, description="Additional notes about the event")
    email_id: Optional[str] = Field(None, description="ID of the related email, if any")
    source_type: Optional[str] = Field(
        None, description="Source system that produced the event"
    )
    source_id: Optional[str] = Field(
        None, description="ID of the related source record, if any"
    )
    is_inferred: bool = Field(
        False, description="Whether the event was inferred rather than observed"
    )
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score for the event"
    )


class ApplicationEventRead(ApplicationEventCreate):
    """
    Schema returned from the DB for an ApplicationEvent
    """

    id: str = Field(..., description="Unique identifier of the application event")
    user_id: str = Field(..., description="Supabase Auth user ID who owns this event")
    created_at: datetime = Field(
        ..., description="Timestamp when the record was created"
    )
