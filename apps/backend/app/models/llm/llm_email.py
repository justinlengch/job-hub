from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

from models.api.job_application import ApplicationStatus

class EmailLLMInput(BaseModel):
    """
    Schema for data sent _into_ the LLM for parsing emails
    """
    subject: str = Field(..., description="Email subject line")
    body_text: str = Field(..., description="Plain-text body of the email")
    body_html: Optional[str] = Field(None, description="HTML body of the email")


class EmailLLMOutput(BaseModel):
    """
    Schema for data returned _from_ the LLM after parsing
    """
    company: str = Field(..., description="Extracted company name")
    role: str = Field(..., description="Extracted job title or role")
    status: ApplicationStatus = Field(
        ..., description="One of the defined application statuses"
    )
    job_posting_url: Optional[HttpUrl] = Field(
        None, description="URL to the job posting, if available"
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
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="LLM's confidence score (0.0–1.0)"
    )
    application_id: Optional[str] = Field(
        None, description="Matched JobApplication ID, if found"
    )
