from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    ASSESSMENT = "ASSESSMENT"
    INTERVIEW = "INTERVIEW"
    REJECTED = "REJECTED"
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    WITHDRAWN = "WITHDRAWN"

class ApplicationEventType(str, Enum):
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    APPLICATION_VIEWED = "APPLICATION_VIEWED"
    APPLICATION_REVIEWED = "APPLICATION_REVIEWED"
    ASSESSMENT_RECEIVED = "ASSESSMENT_RECEIVED"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"
    REFERENCE_REQUESTED = "REFERENCE_REQUESTED"
    OFFER_RECEIVED = "OFFER_RECEIVED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    OFFER_DECLINED = "OFFER_DECLINED"
    APPLICATION_REJECTED = "APPLICATION_REJECTED"
    APPLICATION_WITHDRAWN = "APPLICATION_WITHDRAWN"

class JobApplication(BaseModel):
    id: Optional[str] = None
    user_id: str
    company: str
    role: str
    status: ApplicationStatus
    job_posting_url: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    last_email_received_at: Optional[datetime] = None

class ApplicationEvent(BaseModel):
    id: Optional[str] = None
    application_id: str
    event_type: ApplicationEventType
    event_date: datetime
    description: Optional[str] = None
    email_id: Optional[str] = None
    created_at: Optional[datetime] = None

class Email(BaseModel):
    id: Optional[str] = None
    application_id: Optional[str] = None
    user_id: str
    email_id: str
    subject: str
    sender: str
    body_text: str
    body_html: Optional[str] = None
    received_date: datetime
    parsed: bool = False
    parsing_confidence: Optional[float] = None
    created_at: Optional[datetime] = None