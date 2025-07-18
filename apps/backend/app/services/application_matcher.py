from typing import Optional, Dict, Any
from app.services.supabase import get_supabase_client

async def find_matching_application(user_id: str, company: str, role: str, location: Optional[str] = None) -> Optional[str]:
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
    supabase = await get_supabase_client()

    # First try exact match
    query = supabase.table("job_applications").select("application_id").eq("user_id", user_id).eq("company", company).eq("role", role)
    
    if location:
        query = query.eq("location", location)

    response = await query.execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]["application_id"]
    
    # If no exact match, try case-insensitive match
    query = supabase.table("job_applications").select("application_id").eq("user_id", user_id).ilike("company", company).ilike("role", role)
    
    if location:
        query = query.ilike("location", location)

    response = await query.execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]["application_id"]
    
    return None

async def update_application_fields(application_id: str, update_data: Dict[str, Any]) -> None:
    """
    Update specific fields of an existing job application.
    
    Args:
        application_id: ID of the application to update
        update_data: Dictionary of fields to update
    """
    supabase = await get_supabase_client()
    
    # Always update the last_updated_at timestamp
    update_data["last_updated_at"] = "now()"
    
    await supabase.table("job_applications").update(update_data).eq("application_id", application_id).execute()

async def update_application_status(application_id: str, status: str) -> None:
    """
    Update the status of an existing job application.
    
    Args:
        application_id: ID of the application to update
        status: New status to set
    """
    await update_application_fields(application_id, {"status": status})
