from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from ..models.llm.llm_email import LLMEmailInput, LLMEmailOutput
from ..models.api.email import EmailParseRequest, EmailParseResponse
from ..services.ai.llm import extract_job_info
from ..services.db_operations import insert_job_application_with_retry, update_email_as_parsed
from ..services.supabase import get_supabase_client
from ..core.auth import get_current_user

# TODO: Task 4 - Email Processing Logic
# - Update /parse-email endpoint to handle the complete flow
# - Implement decision tree based on intent and confidence score
# - Add logic for creating new applications vs updating existing ones
# - Integrate application event creation when appropriate

# TODO: Task 5 - Database Operations
# - Add proper database queries for application matching
# - Implement application creation with all required fields
# - Add application event insertion logic
# - Update email table to mark as parsed with confidence score

router = APIRouter(tags=["email"])

@router.post("/test-parse-email")
async def test_parse_email_no_auth(request: EmailParseRequest):
    """
    Test endpoint for email parsing without authentication.
    Only for development/testing purposes.
    """
    try:
        # Create LLM input from the request
        email_input = LLMEmailInput(
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html
        )
        
        # Extract job info using LLM
        job_info = await extract_job_info(email_input)
        
        # Return the parsed data without saving to database
        return {
            "success": True,
            "parsed_data": {
                "company": job_info.company,
                "role": job_info.role,
                "status": job_info.status.value if hasattr(job_info.status, 'value') else str(job_info.status),
                "location": job_info.location,
                "salary_range": job_info.salary_range,
                "notes": job_info.notes
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/parse-email", response_model=EmailParseResponse)
async def parse_email(request: EmailParseRequest, current_user_id: str = Depends(get_current_user)):
    """
    Parse an email to extract job application information using LLM.
    Then store the extracted data in Supabase with retry logic.
    User authentication is required via Bearer token.
    """
    try:
        # Create LLM input from the request
        email_input = LLMEmailInput(
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html
        )
        
        # Extract job info using LLM
        job_info = await extract_job_info(email_input)
        
        # Insert into database with retry logic
        created_app = await insert_job_application_with_retry(
            user_id=current_user_id,
            job_info=job_info,
            email_id=request.email_id,
            email_subject=request.subject,
            email_received_at=request.received_date
        )
        
        # Update email as parsed if email_id is provided
        if request.email_id:
            await update_email_as_parsed(
                email_id=request.email_id,
                application_id=created_app.get("id")
            )
        
        # Convert LLMEmailOutput to EmailParseResponse
        return EmailParseResponse(
            application_id=created_app.get("id"),
            company=job_info.company,
            role=job_info.role,
            status=job_info.status,
            location=job_info.location,
            salary_range=job_info.salary_range,
            notes=job_info.notes
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing email: {str(e)}"
        )
