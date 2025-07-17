import google.generativeai as genai
from typing import Optional
import json
import logging
from ..config import settings
from ..models.llm.llm_email import LLMEmailInput, LLMEmailOutput
from ..models.api.job_application import ApplicationStatus

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)


async def extract_job_info(email_input: LLMEmailInput) -> LLMEmailOutput:
    """
    Extract job application information from an email using Google's Gemini model.
    
    Args:
        email_input: LLMEmailInput containing email subject, body, and optional HTML
        
    Returns:
        LLMEmailOutput with extracted job information
    """
    
    prompt = f"""
    Analyze this job application related email and extract the following information:
    
    EMAIL SUBJECT: {email_input.subject}
   
    EMAIL BODY:
    {email_input.body_text}
    
    {f"EMAIL HTML: {email_input.body_html}" if email_input.body_html else ""}
    
    Extract these details in JSON format:
    1. company: The company name
    2. role: The job title or role
    3. status: The status of the application (one of: "APPLIED", "ASSESSMENT", "INTERVIEW", "REJECTED", "OFFERED", "ACCEPTED", "WITHDRAWN")
    4. job_posting_url: URL to the job posting (if available)
    5. location: Job location (if available)
    6. salary_range: Salary information (if available)
    7. notes: Any additional important information
    8. confidence_score: How confident you are in your extraction (0.0-1.0)
    9. application_id: Leave as null (will be filled later if matching existing application)
    
    Respond ONLY with valid JSON object.
    """
    
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        system_prompt = "You are a helpful assistant that extracts job application information from emails."
        
        chat = model.start_chat(history=[
            {"role": "user", "parts": [system_prompt]},
            {"role": "model", "parts": ["I'll help extract job application information from emails."]}
        ])
        
        response = await chat.send_message_async(prompt)
        content = response.text
        
        try:
            # Try to find JSON in the response if it's not pure JSON
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                content = content[json_start:json_end]
            
            parsed_data = json.loads(content)
            
            result = LLMEmailOutput(
                company=parsed_data.get("company", "Unknown Company"),
                role=parsed_data.get("role", "Unknown Role"),
                status=parsed_data.get("status", "APPLIED"),
                job_posting_url=parsed_data.get("job_posting_url"),
                location=parsed_data.get("location"),
                salary_range=parsed_data.get("salary_range"),
                notes=parsed_data.get("notes"),
                confidence_score=float(parsed_data.get("confidence_score", 0.7)),
                application_id=parsed_data.get("application_id")
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from LLM response: {e}")
            logging.error(f"Raw response: {content}")
            
            return LLMEmailOutput(
                company="Unknown Company",
                role="Unknown Role",
                status=ApplicationStatus.APPLIED,
                job_posting_url=None,
                location=None,
                salary_range=None,
                notes=f"Error parsing email. Please review manually.",
                confidence_score=0.0,
                application_id=None
            )
            
    except Exception as e:
        logging.error(f"Error calling Gemini API: {str(e)}")
        raise


# Legacy function for backward compatibility
async def extract_job_info_legacy(
    subject: str, 
    body: str, 
    html: Optional[str] = None
) -> LLMEmailOutput:
    """
    Legacy wrapper function that converts old-style parameters to LLMEmailInput.
    This maintains backward compatibility with existing code.
    """
    email_input = LLMEmailInput(
        subject=subject,
        body_text=body,
        body_html=html
    )
    return await extract_job_info(email_input)
