from datetime import datetime
from typing import Any, Dict, List, Optional
from app.services.supabase.application_matcher_service import application_matcher_service
from app.models.llm.llm_email import LLMEmailOutput
from app.services.base_service import BaseService, ServiceOperationError
from app.services.supabase.supabase_client import supabase_service


class JobApplicationService(BaseService):
    """Service for managing job application CRUD operations."""
    
    def _initialize(self) -> None:
        """Initialize job application service."""
        self._log_operation("Job application service initialized")

    async def handle_new_application(
        self,
        user_id: str,
        parsed: LLMEmailOutput,
        email_id: str
    ) -> Dict[str, Any]:
        """
        Handle NEW_APPLICATION intent: Insert into job_applications and link raw_email.
        """
        supabase = await supabase_service.get_client()
        
        try:
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
            
            app_response = await supabase.table("job_applications").insert(application_data).execute()
            
            if not app_response.data:
                raise ServiceOperationError("Failed to insert job application")
            
            created_app = app_response.data[0]
            application_id = created_app["application_id"]
            
            await supabase.table("emails").update({"application_id": application_id}).eq("email_id", email_id).execute()
            
            self._log_operation("created new application", f"ID: {application_id}")
            return created_app
            
        except Exception as e:
            raise ServiceOperationError(f"Failed to create new application in supabase")
                

    async def handle_application_event(
        self,
        user_id: str,
        parsed: LLMEmailOutput,
        email_id: str,
    ) -> Dict[str, Any]:
        """
        Handle APPLICATION_EVENT intent: Lookup application, insert event, update fields, and link raw_email.
        """
        supabase = await supabase_service.get_client()
        
        try:
            application_id = await application_matcher_service.find_matching_application(user_id, parsed.company, parsed.role)
            
            if not application_id:
                self._log_operation("no matching application found", f"user: {user_id}, company: {parsed.company}, role: {parsed.role}")
                return {"status": "no_match", "message": "No matching application found"}
            
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
                raise ServiceOperationError("Failed to insert application event")
            
            created_event = event_response.data[0]
            
            update_data = {
                "last_updated_at": datetime.now().isoformat(),
                "last_email_received_at": datetime.now().isoformat()
            }
            
            if parsed.status:
                update_data["status"] = parsed.status.value
            if parsed.location:
                update_data["location"] = parsed.location
            if parsed.salary_range:
                update_data["salary_range"] = parsed.salary_range
            if parsed.notes:
                update_data["notes"] = parsed.notes
            
            await supabase.table("job_applications").update(update_data).eq("application_id", application_id).execute()
            
            await supabase.table("emails").update({"application_id": application_id}).eq("email_id", email_id).execute()
            
            self._log_operation("processed application event", f"application: {application_id}")
            return {
                "application_id": application_id,
                "event": created_event,
                "updated_fields": list(update_data.keys())
            }
            
        except Exception as e:
            raise ServiceOperationError(f"Failed to process application event")

job_application_service = JobApplicationService()
