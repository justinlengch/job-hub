from typing import Optional, Dict, Any
from ..base_service import BaseService, ServiceOperationError
from .supabase_client import supabase_service


class ApplicationMatcherService(BaseService):
    """Service for matching and updating job applications."""
    
    def _initialize(self) -> None:
        """Initialize application matcher service."""
        self._log_operation("Application matcher service initialized")
    
    async def find_matching_application(
        self, 
        user_id: str, 
        company: str, 
        role: str, 
        location: Optional[str] = None
    ) -> Optional[str]:
        """
        Find existing job application that matches the company, role and optionally location.

        Args:
            user_id: User ID from authentication
            company: Company name to match
            role: Job role to match
            location: Job location to match (optional)

        Returns:
            Application ID if found, None otherwise
        """
        try:
            supabase = await supabase_service.get_client()

            # First try exact match
            query = supabase.table("job_applications").select("application_id").eq("user_id", user_id).eq("company", company).eq("role", role)
            
            response = await query.execute()
            
            if response.data and len(response.data) > 0:
                self._log_operation("exact match found", f"company: {company}, role: {role}")
                return response.data[0]["application_id"]
            
            # If no exact match, try case-insensitive match
            query = supabase.table("job_applications").select("application_id").eq("user_id", user_id).ilike("company", company).ilike("role", role)
            
            response = await query.execute()
            
            if response.data and len(response.data) > 0:
                self._log_operation("case-insensitive match found", f"company: {company}, role: {role}")
                return response.data[0]["application_id"]
            
            self._log_operation("no matching application found", f"company: {company}, role: {role}")
            return None
            
        except Exception as e:
            self._log_error("finding matching application", e)
            raise ServiceOperationError(f"Failed to find matching application: {str(e)}")
            

    async def update_application_fields(self, application_id: str, update_data: Dict[str, Any]) -> None:
        """
        Update specific fields of an existing job application.
        
        Args:
            application_id: ID of the application to update
            update_data: Dictionary of fields to update
        """
        try:
            supabase = await supabase_service.get_client()
            
            update_data["last_updated_at"] = "now()"
            
            response = await supabase.table("job_applications").update(update_data).eq("application_id", application_id).execute()
            
            if not response.data:
                raise ServiceOperationError(f"Application with ID {application_id} not found")
            
            self._log_operation("application updated", f"ID: {application_id}, fields: {list(update_data.keys())}")
            
        except Exception as e:
            self._log_error("updating application fields", e)
            raise ServiceOperationError(f"Failed to update application: {str(e)}")


    async def update_application_status(self, application_id: str, status: str) -> None:
        """
        Update the status of an existing job application.
        
        Args:
            application_id: ID of the application to update
            status: New status to set
        """
        try:
            await self.update_application_fields(application_id, {"status": status})
            self._log_operation("application status updated", f"ID: {application_id}, status: {status}")
        except Exception as e:
            self._log_error("updating application status", e)
            raise ServiceOperationError(f"Failed to update application status: {str(e)}")


application_matcher_service = ApplicationMatcherService()
