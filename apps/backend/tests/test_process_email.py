"""
Test script for the process_email workflow
"""
import pytest
from datetime import datetime
from app.models.llm.llm_email import LLMEmailOutput, EmailIntent
from app.models.api.job_application import ApplicationStatus
from app.models.api.application_event import ApplicationEventType
from app.services.db_operations import process_email

@pytest.mark.asyncio
async def test_new_application():
    """Test the NEW_APPLICATION workflow"""
    print("Testing NEW_APPLICATION workflow...")
    
    parsed_data = LLMEmailOutput(
        company="Test Company",
        role="Software Engineer",
        status=ApplicationStatus.APPLIED,
        event_type=ApplicationEventType.APPLICATION_SUBMITTED,
        event_description="Application received from email",
        event_date=datetime.now(),
        location="Remote",
        salary_range="$80k - $120k",
        notes="Test application from email",
        intent=EmailIntent.NEW_APPLICATION
    )
    
    result = await process_email(
        parsed=parsed_data,
        raw_email_id="test_email_new_app_123",
        user_id="test_user_123",
        sender="hr@testcompany.com",
        subject="Application Received - Software Engineer",
        body_text="Thank you for your application...",
        received_at=datetime.now()
    )
    
    # verify that a new application was created
    assert result["status"] == "processed"
    assert result.get("intent") == "NEW_APPLICATION"
    assert "application" in result

@pytest.mark.asyncio
async def test_application_event():
    """Test the APPLICATION_EVENT workflow"""
    print("Testing APPLICATION_EVENT workflow...")
    
    parsed_data = LLMEmailOutput(
        company="Test Company",
        role="Software Engineer",
        status=ApplicationStatus.INTERVIEW,
        location="Remote",
        intent=EmailIntent.APPLICATION_EVENT,
        event_type=ApplicationEventType.INTERVIEW_SCHEDULED,
        event_description="Interview scheduled for next week",
        event_date=datetime.now(),
        salary_range=None,
        notes= "Interview scheduled from email"
    )
    
    result = await process_email(
        parsed=parsed_data,
        raw_email_id="test_email_event_456",
        user_id="test_user_123",
        sender="hr@testcompany.com",
        subject="Interview Scheduled - Software Engineer",
        body_text="Your interview has been scheduled...",
        received_at=datetime.now()
    )
    
    # verify that an application event was processed
    assert result["status"] == "processed"
    assert result.get("intent") == "APPLICATION_EVENT"
    assert "event" in result

@pytest.mark.asyncio
async def test_duplicate_email():
    """Test the deduplication workflow"""
    print("Testing duplicate email workflow...")
    
    parsed_data = LLMEmailOutput(
        company="Test Company",
        role="Software Engineer",
        status=ApplicationStatus.APPLIED,
        intent=EmailIntent.NEW_APPLICATION,
        location="Remote",
        salary_range="$80k - $120k",
        notes="Test application from email",
        event_type=None,
        event_description=None,
        event_date=None
    )
    
    # First, try to process the same email ID again
    result = await process_email(
        parsed=parsed_data,
        raw_email_id="test_email_new_app_123",  # Same as first test
        user_id="test_user_123",
        sender="hr@testcompany.com",
        subject="Duplicate Application Email",
        body_text="This should be detected as duplicate...",
        received_at=datetime.now()
    )
    
    # verify that duplicate email is detected
    assert result["status"] == "duplicate"
    assert "email_id" in result

@pytest.mark.asyncio
async def test_general_email():
    """Test the GENERAL workflow"""
    print("Testing GENERAL email workflow...")
    
    parsed_data = LLMEmailOutput(
        company="Test Company",
        role="Software Engineer",
        status=ApplicationStatus.APPLIED,
        intent=EmailIntent.GENERAL,
        location=None,
        salary_range=None,
        notes="This is a general email, not related to job applications",
        event_type=None,
        event_description=None,
        event_date=None
    )
    
    result = await process_email(
        parsed=parsed_data,
        raw_email_id="test_email_general_789",
        user_id="test_user_123",
        sender="newsletter@testcompany.com",
        subject="Company Newsletter",
        body_text="Monthly company updates...",
        received_at=datetime.now()
    )
    
    # verify that general emails are stored but no action taken
    assert result["status"] == "processed"
    assert result.get("intent") == "GENERAL"
    assert result.get("action") == "none"

