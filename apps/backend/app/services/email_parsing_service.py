from datetime import datetime
from typing import Any, Dict, Optional
from app.models.llm.llm_email import EmailIntent, LLMEmailOutput
from app.services.job_application_service import job_application_service
from app.services.supabase_service import supabase_service
from app.services.base_service import BaseService, ServiceOperationError


class EmailParsingService(BaseService):
    """
    Service for parsing emails into job applications or events.
    Handles deduplication, raw email insertion, and intent-based processing.
    """

    def _initialize(self) -> None:
        """Initialize email parsing service."""
        self._log_operation("Email parsing service initialized")

    async def process_email(
        self,
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
        Main email processing workflow to parse emails into job applications or events.
        
        Args:
            parsed: LLMEmailOutput containing the extracted job information
            raw_email_id: External email ID for deduplication
            user_id: The user ID to associate with the application
            sender: Email sender
            subject: Email subject
            body_text: Plain text body of the email
            body_html: HTML body of the email
            received_at: Timestamp when email was received
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict containing the processing results
            
        Raises:
            ServiceOperationError: If all retry attempts fail
        """
        try:
            supabase = await supabase_service.get_client()
            
            # For non-job emails, skip database storage entirely
            if parsed.intent == EmailIntent.GENERAL:
                self._log_operation("non job-related email skipped", f"ID: {raw_email_id} - not job related")
                return {"status": "skipped", "intent": parsed.intent.value, "reason": "not_job_related"}
            
            existing_email = await supabase.table("emails").select("email_id").eq("external_email_id", raw_email_id).execute()
            
            if existing_email.data:
                self._log_operation("email already processed", f"ID: {raw_email_id}")
                return {"status": "duplicate", "email_id": existing_email.data[0]["email_id"]}
            
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
                raise ServiceOperationError("Failed to insert raw email record")
            
            email_record = email_response.data[0]
            email_id = email_record["email_id"]
            
            result = {"status": "processed", "email_id": email_id, "intent": parsed.intent.value}
            
            if parsed.intent == EmailIntent.NEW_APPLICATION:
                application_data = await job_application_service.handle_new_application(user_id, parsed, email_id)
                result["application"] = application_data
                
            elif parsed.intent == EmailIntent.APPLICATION_EVENT:
                event_data = await job_application_service.handle_application_event(user_id, parsed, email_id)
                result["event"] = event_data
                
            return result
            
        except Exception as e:
            self._log_error("processing email intent", e)
            raise ServiceOperationError(f"Failed to process email: {str(e)}")


email_parsing_service = EmailParsingService()