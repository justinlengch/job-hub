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


class ApplicationOrigin(str, Enum):
    EMAIL = "EMAIL"
    LINKEDIN_EASY_APPLY = "LINKEDIN_EASY_APPLY"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


class ApplicationDatePrecision(str, Enum):
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    INFERRED = "INFERRED"


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
    canonical_source: Optional[str] = Field(
        None, description="Canonical source system for the application"
    )
    application_origin: ApplicationOrigin = Field(
        ApplicationOrigin.MANUAL,
        description="Where the canonical application originated",
    )
    application_inferred: bool = Field(
        False, description="Whether the application was inferred from later signals"
    )
    inferred_reason: Optional[str] = Field(
        None, description="Reason the application was inferred"
    )
    applied_date_precision: ApplicationDatePrecision = Field(
        ApplicationDatePrecision.EXACT,
        description="Precision of the applied_date field",
    )
    match_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence used for canonical matching"
    )
    needs_review: bool = Field(
        False, description="Whether the application needs manual review"
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
