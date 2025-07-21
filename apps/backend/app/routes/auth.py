from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

from ..services.gmail_service import gmail_service
from ..services.supabase_service import supabase_service
from ..services.base_service import ServiceOperationError
from ..core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class AuthCallbackRequest(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    provider: str = "google"


class UserSetupRequest(BaseModel):
    access_token: str
    refresh_token: str
    setup_gmail_automation: bool = True
    label_name: Optional[str] = "Job Applications"


async def setup_user_gmail_automation(
    user_id: str,
    access_token: str,
    refresh_token: str,
    label_name: str = "Job Applications"
) -> Dict[str, Any]:
    """
    Background task to set up Gmail automation for a user.
    This runs asynchronously after user authentication.
    """
    try:
        # Create Gmail client with user credentials
        credentials = {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        
        if not gmail_service.create_gmail_client(credentials):
            logger.error(f"Failed to create Gmail client for user {user_id}")
            return {"success": False, "error": "Failed to authenticate with Gmail"}
        
        # Set up label and filter
        label_id = gmail_service.setup_job_application_labeling(label_name)
        
        # Store the label_id in user preferences (optional)
        supabase = await supabase_service.get_client()
        await supabase.table("user_preferences").upsert({
            "user_id": user_id,
            "gmail_label_id": label_id,
            "gmail_automation_enabled": True,
            "updated_at": "now()"
        }).execute()
        
        logger.info(f"Successfully set up Gmail automation for user {user_id}")
        return {
            "success": True,
            "label_id": label_id,
            "message": f"Gmail automation set up successfully with label '{label_name}'"
        }
        
    except Exception as e:
        logger.error(f"Error setting up Gmail automation for user {user_id}: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/setup-user")
async def setup_new_user(
    request: UserSetupRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user)
):
    """
    Set up a new user after authentication.
    This endpoint should be called from the frontend after successful OAuth.
    """
    try:
        if request.setup_gmail_automation:
            # Add background task to set up Gmail automation
            background_tasks.add_task(
                setup_user_gmail_automation,
                current_user_id,
                request.access_token,
                request.refresh_token,
                request.label_name or "Job Applications"
            )
            
            return {
                "success": True,
                "message": "User setup initiated. Gmail automation will be configured shortly.",
                "user_id": current_user_id
            }
        else:
            return {
                "success": True,
                "message": "User setup complete (Gmail automation skipped).",
                "user_id": current_user_id
            }
            
    except Exception as e:
        logger.error(f"Error in user setup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"User setup failed: {str(e)}")


@router.get("/user-preferences")
async def get_user_preferences(current_user_id: str = Depends(get_current_user)):
    """
    Get user preferences including Gmail automation status.
    """
    try:
        supabase = await supabase_service.get_client()
        result = await supabase.table("user_preferences").select("*").eq("user_id", current_user_id).execute()
        
        if result.data:
            return {"success": True, "preferences": result.data[0]}
        else:
            return {
                "success": True,
                "preferences": {
                    "user_id": current_user_id,
                    "gmail_automation_enabled": False,
                    "gmail_label_id": None
                }
            }
            
    except Exception as e:
        logger.error(f"Error fetching user preferences: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch user preferences")
