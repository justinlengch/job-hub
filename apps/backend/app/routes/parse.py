from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.email_parsing_service import email_parsing_service
from app.models.llm.llm_email import LLMEmailInput, LLMEmailOutput
from app.models.api.email import EmailParseRequest, EmailParseResponse
from app.services.ai.llm_service import extract_job_info
from app.core.auth import get_current_user

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
                "notes": job_info.notes,
                "intent": job_info.intent.value if hasattr(job_info.intent, 'value') else str(job_info.intent)
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
    Then process the email through the complete workflow with deduplication, 
    database operations, and intent-based handling.
    User authentication is required via Bearer token.
    """
    try:
        email_input = LLMEmailInput(
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html
        )
        
        job_info = await extract_job_info(email_input)
        
        # Process email through the complete workflow
        processing_result = await email_parsing_service.process_email(
            parsed=job_info,
            raw_email_id=request.email_id,
            user_id=current_user_id,
            sender=request.sender,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            received_at=request.received_date
        )
        
        # Handle response based on processing result
        if processing_result.get("status") == "duplicate":
            return EmailParseResponse(
                application_id=None,
                company=job_info.company,
                role=job_info.role,
                status=job_info.status,
                location=job_info.location,
                salary_range=job_info.salary_range,
                notes=f"Duplicate email (already processed). {job_info.notes or ''}"
            )
        
        # Extract application data from the result
        application_data = processing_result.get("application")
        application_id = None
        
        if application_data:
            application_id = application_data.get("application_id")
        elif processing_result.get("event"):
            # For events, we might not have application data in the response
            application_id = processing_result.get("event", {}).get("application_id")
        
        # Convert LLMEmailOutput to EmailParseResponse
        return EmailParseResponse(
            application_id=application_id,
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
