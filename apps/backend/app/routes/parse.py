from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from ..models.email import EmailParseRequest, EmailParseResponse
from ..services.llm import extract_job_info
from ..services.supabase import get_supabase_client

router = APIRouter(tags=["email"])

@router.post("/parse-email", response_model=EmailParseResponse)
async def parse_email(request: EmailParseRequest):
    """
    Parse an email to extract job application information using LLM.
    Then store the extracted data in Supabase.
    """
    try:
        job_info = await extract_job_info(
            subject=request.subject,
            body=request.body_text,
            html=request.body_html
        )
        
        supabase = get_supabase_client()
        
        response = supabase.table("job_applications").insert({
            "user_id": request.user_id,
            "company": job_info.company,
            "role": job_info.role,
            "status": job_info.status.value,
            "job_posting_url": job_info.job_posting_url,
            "notes": job_info.notes,
            "email_id": request.email_id,
            "email_subject": request.subject,
            "email_received_at": request.received_date.isoformat()
        }).execute()
        
        return job_info
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing email: {str(e)}"
        )
