import google.generativeai as genai
from typing import Optional
import json
import logging
from ..config import settings
from ..models.email import EmailParseResponse, ApplicationStatus

genai.configure(api_key=settings.GEMINI_API_KEY)

async def extract_job_info(
    subject: str, 
    body: str, 
    html: Optional[str] = None
) -> EmailParseResponse:
    """
    Extract job application information from an email using OpenAI's GPT model.
    
    Args:
        subject: Email subject line
        body: Plain text email body
        html: Optional HTML email body
        
    Returns:
        EmailParseResponse with extracted job information
    """

    prompt = f"""
    Analyze this job application related email and extract the following information:
    
    EMAIL SUBJECT: {subject}
   
    EMAIL BODY:
    {body}
    
    Extract these details in JSON format:
    1. company: The company name
    2. role: The job title or role
    3. status: The status of the application (one of: "APPLIED", "INTERVIEW", "REJECTED", "OFFERED", "ACCEPTED", "WITHDRAWN")
    4. job_posting_url: URL to the job posting (if available)
    5. location: Job location (if available)
    6. salary_range: Salary information (if available)
    7. notes: Any additional important information
    8. confidence_score: How confident you are in your extraction (0.0-1.0)
    
    Respond ONLY with valid JSON object.
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
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
            
            result = EmailParseResponse(
                company=parsed_data.get("company", "Unknown Company"),
                role=parsed_data.get("role", "Unknown Role"),
                status=parsed_data.get("status", "APPLIED"),
                job_posting_url=parsed_data.get("job_posting_url"),
                location=parsed_data.get("location"),
                salary_range=parsed_data.get("salary_range"),
                notes=parsed_data.get("notes"),
                confidence_score=float(parsed_data.get("confidence_score", 0.7))
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from LLM response: {e}")
            logging.error(f"Raw response: {content}")
            
            return EmailParseResponse(
                company="Unknown Company",
                role="Unknown Role",
                status=ApplicationStatus.APPLIED,
                notes=f"Error parsing email. Please review manually.",
                confidence_score=0.0
            )
            
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {str(e)}")
        raise
