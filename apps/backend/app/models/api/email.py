from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional

from .job_application import ApplicationStatus


class EmailCreate(BaseModel):
    """
    Schema for creating a new Email record in the DB
    """
    subject: str = Field(..., description="Email subject")
    sender: str = Field(..., description="Email sender address")
    body_text: str = Field(..., description="Plain-text body of the email")
    body_html: Optional[str] = Field(None, description="HTML body of the email, if any")
    received_date: datetime = Field(..., description="Timestamp when the email was received")
    application_id: Optional[str] = Field(
        None, description="Linked JobApplication ID (filled post-LLM parsing)"
    )


class EmailRead(EmailCreate):
    """
    Schema for returning an Email record to the client
    """
    id: str = Field(..., description="Unique DB-generated email record ID")
    user_id: str = Field(..., description="ID of the owning user")
    parsed: bool = Field(
        ..., description="Whether the email has been processed by the LLM"
    )
    parsing_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="LLM parsing confidence score (0.0–1.0)",
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the DB record was created"
    )


class EmailParseRequest(BaseModel):
    """
    Request payload for the /parse-email endpoint
    """
    email_id: str = Field(..., description="Unique identifier of the email")
    subject: str = Field(..., description="Email subject line")
    body_text: str = Field(..., description="Plain-text body of the email")
    body_html: Optional[str] = Field(None, description="HTML body, if provided")
    received_date: datetime = Field(..., description="When the email was received")
    sender: str = Field(..., description="Email sender address")


class EmailParseResponse(BaseModel):
    """
    Response schema for the /parse-email endpoint
    """
    # TODO: Task 6 - Response Models
    # - Update EmailParseResponse to include action_taken field
    # - Add fields for application_id, confidence_score, and reason
    # - Ensure response model matches the decision outcomes
    
    application_id: Optional[str] = Field(
        None, description="Matched JobApplication ID, if any"
    )
    company: str = Field(..., description="Extracted company name")
    role: str = Field(..., description="Extracted job title or role")
    status: ApplicationStatus = Field(
        ..., description="One of the defined application statuses"
    )
    job_posting_url: Optional[HttpUrl] = Field(
        None, description="URL to the job posting, if found"
    )
    location: Optional[str] = Field(None, description="Extracted job location")
    salary_range: Optional[str] = Field(None, description="Extracted salary range info")
    notes: Optional[str] = Field(None, description="Additional extracted notes")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="LLM parsing confidence (0.0–1.0)",
    )
