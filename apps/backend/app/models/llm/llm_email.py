from enum import Enum
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime

from ..api.job_application import ApplicationStatus
from ..api.application_event import ApplicationEventType

class EmailIntent(str, Enum):
    """
    Enum for email intent classification.
    """
    NEW_APPLICATION = "NEW_APPLICATION"
    APPLICATION_EVENT = "APPLICATION_EVENT"
    GENERAL = "GENERAL"

class LLMEmailInput(BaseModel):
    """
    Schema for data sent _into_ the LLM for parsing emails
    """
    subject: str = Field(..., description="Email subject line")
    body_text: str = Field(..., description="Plain-text body of the email")
    body_html: Optional[str] = Field(None, description="HTML body of the email")


class LLMEmailOutput(BaseModel):
    """
    Schema for data returned _from_ the LLM after parsing
    """
    company: str = Field(..., description="Extracted company name")
    role: str = Field(..., description="Extracted job title or role")
    status: ApplicationStatus = Field(
        ..., description="One of the defined application statuses"
    )
    location: Optional[str] = Field(
        None, description="Job location, if available"
    )
    salary_range: Optional[str] = Field(
        None, description="Salary range, if available"
    )
    notes: Optional[str] = Field(
        None, description="Any additional notes"
    )
    intent: EmailIntent = Field(
        ..., description="Intent classification of the email by llm"
    )
    event_type: Optional[ApplicationEventType] = Field(
        None, description="Type of application event if intent is APPLICATION_EVENT"
    )
    event_description: Optional[str] = Field(
        None, description="Description of the event if applicable"
    )
    event_date: Optional[datetime] = Field(
        None, description="Date when the event occurred"
    )
