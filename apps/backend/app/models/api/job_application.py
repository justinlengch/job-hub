from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum

class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    ASSESSMENT = "ASSESSMENT"
    INTERVIEW = "INTERVIEW"
    REJECTED = "REJECTED"
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    WITHDRAWN = "WITHDRAWN"


class JobApplicationCreate(BaseModel):
    """
    Schema for creating a new JobApplication record in the DB
    """
    company: str = Field(..., description="Company name of the job application")
    role: str = Field(..., description="Role/title of the job application")
    job_posting_url: Optional[HttpUrl] = Field(None, description="URL of the job posting")
    location: Optional[str] = Field(None, description="Location of the job")
    salary_range: Optional[str] = Field(None, description="Salary range")
    notes: Optional[str] = Field(None, description="Additional notes")
    applied_date: Optional[datetime] = Field(
        None, description="Date the application was submitted"
    )
    status: ApplicationStatus = Field(
        ApplicationStatus.APPLIED,
        description="Current status of the job application"
    )


class JobApplicationRead(JobApplicationCreate):
    """
    Schema returned from the DB for a JobApplication
    """
    id: str = Field(..., description="Unique identifier of the job application")
    user_id: str = Field(..., description="Supabase Auth user ID who owns this application")
    created_at: datetime = Field(
        ..., description="Timestamp when the record was created"
    )
    last_updated_at: datetime = Field(
        ..., description="Timestamp when the record was last updated"
    )
    last_email_received_at: Optional[datetime] = Field(
        None, description="Timestamp when the last related email was received"
    )
