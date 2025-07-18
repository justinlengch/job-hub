import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from models.llm.llm_email import LLMEmailOutput, EmailIntent
from models.api.application_event import ApplicationEventType
from services.supabase import get_supabase_client

logger = logging.getLogger(__name__)

class DatabaseOperationError(Exception):
    """Custom exception for database operations."""
    pass

async def insert_job_application_with_retry(
    user_id: str,
    job_info: LLMEmailOutput,
    email_id: Optional[str] = None,
    email_subject: Optional[str] = None,
    email_received_at: Optional[datetime] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Insert job application data into Supabase with retry logic and rollback.
    
    Args:
        user_id: The user ID to associate with the application
        job_info: LLMEmailOutput containing the extracted job information
        email_id: Optional email ID for tracking
        email_subject: Optional email subject for reference
        email_received_at: Optional timestamp when email was received
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dict containing the created application data
        
    Raises:
        DatabaseOperationError: If all retry attempts fail
    """
    
    supabase = get_supabase_client()
    
    for attempt in range(max_retries):
        try:
            # Prepare application data
            application_data = {
                "user_id": user_id,
                "company": job_info.company,
                "role": job_info.role,
                "status": job_info.status.value,
                "location": job_info.location,
                "salary_range": job_info.salary_range,
                "notes": job_info.notes
            }
            
            # Add email-related fields if provided
            if email_id:
                application_data["email_id"] = email_id
            if email_subject:
                application_data["email_subject"] = email_subject
            if email_received_at:
                application_data["email_received_at"] = email_received_at.isoformat()
            
            # Insert job application
            app_response = supabase.table("job_applications").insert(application_data).execute()
            
            if not app_response.data:
                raise DatabaseOperationError("Failed to insert job application")
            
            created_app = app_response.data[0]
            application_id = created_app["id"]
            
            # If this is an application event, also create the event record
            if (job_info.intent == EmailIntent.APPLICATION_EVENT and 
                job_info.event_type and 
                job_info.event_description):
                
                event_data = {
                    "application_id": application_id,
                    "event_type": job_info.event_type.value,
                    "description": job_info.event_description,
                    "event_date": job_info.event_date.isoformat() if job_info.event_date else datetime.now().isoformat(),
                    "created_at": datetime.now().isoformat()
                }
                
                event_response = supabase.table("application_events").insert(event_data).execute()
                
                if not event_response.data:
                    # Rollback the application insert if event creation fails
                    try:
                        supabase.table("job_applications").delete().eq("id", application_id).execute()
                    except Exception as rollback_error:
                        logger.error(f"Failed to rollback application insert: {rollback_error}")
                    
                    raise DatabaseOperationError("Failed to create application event")
                
                logger.info(f"Created application event for application {application_id}")
            
            logger.info(f"Successfully inserted job application with ID: {application_id}")
            return created_app
            
        except Exception as e:
            logger.warning(f"Database operation failed (attempt {attempt + 1}): {e}")
            
            if attempt == max_retries - 1:
                raise DatabaseOperationError(f"Failed to insert job application after {max_retries} attempts: {str(e)}")
            
            # Exponential backoff
            await asyncio.sleep(2 ** attempt)
    
    raise DatabaseOperationError("Unexpected error in database operation")

async def update_email_as_parsed(
    email_id: str,
    application_id: Optional[str] = None,
    max_retries: int = 3
) -> bool:
    """
    Update email record to mark it as parsed with confidence score.
    
    Args:
        email_id: The email ID to update
        confidence_score: The confidence score from the LLM
        application_id: Optional application ID if one was created
        max_retries: Maximum number of retry attempts
        
    Returns:
        True if successful, False otherwise
    """
    
    supabase = get_supabase_client()
    
    for attempt in range(max_retries):
        try:
            update_data = {
                "parsed": True,
                "parsed_at": datetime.now().isoformat()
            }
            
            if application_id:
                update_data["application_id"] = application_id
            
            response = supabase.table("emails").update(update_data).eq("id", email_id).execute()
            
            if response.data:
                logger.info(f"Successfully updated email {email_id} as parsed")
                return True
            else:
                logger.warning(f"No email found with ID {email_id}")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to update email (attempt {attempt + 1}): {e}")
            
            if attempt == max_retries - 1:
                logger.error(f"Failed to update email after {max_retries} attempts: {str(e)}")
                return False
            
            await asyncio.sleep(2 ** attempt)
    
    return False
