import logging
import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime
from app.models.llm.llm_email import LLMEmailOutput, EmailIntent
from app.models.api.application_event import ApplicationEventType
from app.services.supabase import get_supabase_client
from app.services.application_matcher import find_matching_application

logger = logging.getLogger(__name__)

class DatabaseOperationError(Exception):
    """Custom exception for database operations."""
    pass

async def process_email(
    parsed: LLMEmailOutput,
    raw_email_id: str,
    user_id: str,
    sender: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    received_at: Optional[datetime] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Main email processing workflow with deduplication, raw email insertion, and intent-based handling.
    
    Args:
        parsed: LLMEmailOutput containing the extracted job information
        raw_email_id: External email ID for deduplication
        user_id: The user ID to associate with the application
        sender: Email sender
        recipient: Email recipient
        subject: Email subject
        body_text: Plain text body of the email
        body_html: HTML body of the email
        received_at: Timestamp when email was received
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dict containing the processing results
        
    Raises:
        DatabaseOperationError: If all retry attempts fail
    """
    supabase = await get_supabase_client()
    
    # Step 1: Deduplicate on raw_email_id
    existing_email = await supabase.table("emails").select("email_id").eq("external_email_id", raw_email_id).execute()
    
    if existing_email.data:
        logger.info(f"Email {raw_email_id} already processed, skipping")
        return {"status": "duplicate", "email_id": existing_email.data[0]["email_id"]}
    
    # Step 2: Insert raw_email record for auditing
    email_data = {
        "user_id": user_id,
        "external_email_id": raw_email_id,
        "sender": sender,
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html,
        "received_at": received_at.isoformat() if received_at else datetime.now().isoformat(),
        "parsed_at": datetime.now().isoformat(),
    }
    
    email_response = await supabase.table("emails").insert(email_data).execute()
    
    if not email_response.data:
        raise DatabaseOperationError("Failed to insert raw email record")
    
    email_record = email_response.data[0]
    email_id = email_record["email_id"]
    
    # Step 3: Handle based on intent
    result = {"status": "processed", "email_id": email_id, "intent": parsed.intent.value}
    
    try:
        if parsed.intent == EmailIntent.NEW_APPLICATION:
            application_data = await handle_new_application(user_id, parsed, email_id, max_retries)
            result["application"] = application_data
            
        elif parsed.intent == EmailIntent.APPLICATION_EVENT:
            event_data = await handle_application_event(user_id, parsed, email_id, max_retries)
            result["event"] = event_data
            
        elif parsed.intent == EmailIntent.GENERAL:
            logger.info("General email processed, no further action needed")
            result["action"] = "none"
            
    except Exception as e:
        logger.error(f"Error processing email intent {parsed.intent}: {e}")
        result["error"] = str(e)
        raise
    
    return result

async def handle_new_application(
    user_id: str,
    parsed: LLMEmailOutput,
    email_id: str,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Handle NEW_APPLICATION intent: Insert into job_applications and link raw_email.
    """
    supabase = await get_supabase_client()
    
    for attempt in range(max_retries):
        try:
            # Prepare application data
            application_data = {
                "user_id": user_id,
                "company": parsed.company,
                "role": parsed.role,
                "status": parsed.status.value,
                "location": parsed.location,
                "salary_range": parsed.salary_range,
                "notes": parsed.notes,
                "applied_date": datetime.now().isoformat(),
                "last_updated_at": datetime.now().isoformat(),
                "last_email_received_at": datetime.now().isoformat()
            }
            
            # Insert job application
            app_response = await supabase.table("job_applications").insert(application_data).execute()
            
            if not app_response.data:
                raise DatabaseOperationError("Failed to insert job application")
            
            created_app = app_response.data[0]
            application_id = created_app["application_id"]
            
            # Link raw_email to application
            await supabase.table("emails").update({"application_id": application_id}).eq("email_id", email_id).execute()
            
            logger.info(f"Successfully created new application with ID: {application_id}")
            return created_app
            
        except Exception as e:
            logger.warning(f"Handle new application failed (attempt {attempt + 1}): {e}")
            
            if attempt == max_retries - 1:
                raise DatabaseOperationError(f"Failed to create new application after {max_retries} attempts: {str(e)}")
            
            await asyncio.sleep(2 ** attempt)
    
    raise DatabaseOperationError("Unexpected error in handle_new_application")

async def handle_application_event(
    user_id: str,
    parsed: LLMEmailOutput,
    email_id: str,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Handle APPLICATION_EVENT intent: Lookup application, insert event, update fields, and link raw_email.
    """
    supabase = await get_supabase_client()
    
    for attempt in range(max_retries):
        try:
            application_id = await find_matching_application(user_id, parsed.company, parsed.role, parsed.location)
            
            if not application_id:
                logger.warning(f"No matching application found for user {user_id}, company {parsed.company}, role {parsed.role}")
                return {"status": "no_match", "message": "No matching application found"}
            
            # Insert into application_events
            event_data = {
                "application_id": application_id,
                "user_id": user_id,
                "event_type": parsed.event_type.value if parsed.event_type else "APPLICATION_RECEIVED",
                "description": parsed.event_description or f"Event from email: {parsed.company} - {parsed.role}",
                "event_date": parsed.event_date.isoformat() if parsed.event_date else datetime.now().isoformat(),
                "email_id": email_id
            }
            
            event_response = await supabase.table("application_events").insert(event_data).execute()
            
            if not event_response.data:
                raise DatabaseOperationError("Failed to insert application event")
            
            created_event = event_response.data[0]
            
            # Update only changed fields on job_applications
            update_data = {
                "last_updated_at": datetime.now().isoformat(),
                "last_email_received_at": datetime.now().isoformat()
            }
            
            # Only update fields that have values and might have changed
            if parsed.status:
                update_data["status"] = parsed.status.value
            if parsed.location:
                update_data["location"] = parsed.location
            if parsed.salary_range:
                update_data["salary_range"] = parsed.salary_range
            if parsed.notes:
                update_data["notes"] = parsed.notes
            
            await supabase.table("job_applications").update(update_data).eq("application_id", application_id).execute()
            
            # Link raw_email to application
            await supabase.table("emails").update({"application_id": application_id}).eq("email_id", email_id).execute()
            
            logger.info(f"Successfully processed application event for application {application_id}")
            return {
                "application_id": application_id,
                "event": created_event,
                "updated_fields": list(update_data.keys())
            }
            
        except Exception as e:
            logger.warning(f"Handle application event failed (attempt {attempt + 1}): {e}")
            
            if attempt == max_retries - 1:
                raise DatabaseOperationError(f"Failed to process application event after {max_retries} attempts: {str(e)}")
            
            await asyncio.sleep(2 ** attempt)
    
    raise DatabaseOperationError("Unexpected error in handle_application_event")

async def update_email_as_parsed(email_id: str, application_id: Optional[str] = None) -> None:
    """
    Update email record to mark as parsed and optionally link to application.
    
    Args:
        email_id: Email ID to update
        application_id: Optional application ID to link
    """
    supabase = await get_supabase_client()
    
    update_data = {"parsed_at": datetime.now().isoformat()}
    
    if application_id:
        update_data["application_id"] = application_id
    
    await supabase.table("emails").update(update_data).eq("email_id", email_id).execute()

