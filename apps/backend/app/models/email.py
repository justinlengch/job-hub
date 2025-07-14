from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional

class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    INTERVIEW = "INTERVIEW"
    REJECTED = "REJECTED"
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    WITHDRAWN = "WITHDRAWN"

class EmailParseRequest(BaseModel):
    """Request model for the email parsing endpoint"""
    email_id: str = Field(..., description="Unique identifier of the email")
    subject: str = Field(..., description="Email subject")
    body_text: str = Field(..., description="Plain text body of the email")
    body_html: Optional[str] = Field(None, description="HTML body of the email")
    received_date: datetime = Field(..., description="Date the email was received")
    sender: str = Field(..., description="Email sender")
    user_id: str = Field(..., description="User ID from Supabase Auth")

class EmailParseResponse(BaseModel):
    """Response model containing extracted job application info"""
    company: str
    role: str
    status: ApplicationStatus
    job_posting_url: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    notes: Optional[str] = None
    confidence_score: float = Field(
        ..., 
        description="How confident the LLM is about the extraction (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
