from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

from ..services.gmail_service import gmail_service
from ..services.base_service import ServiceOperationError, ServiceInitializationError
from ..core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


class GmailCredentials(BaseModel):
    access_token: str
    refresh_token: str


class FilterSetupRequest(BaseModel):
    credentials: GmailCredentials
    label_name: Optional[str] = "Job Applications"


class FilterSetupResponse(BaseModel):
    success: bool
    label_id: Optional[str] = None
    message: str


@router.post("/setup-filter", response_model=FilterSetupResponse)
async def setup_job_application_filter(
    request: FilterSetupRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Set up Gmail filter and label for job application emails.
    This creates both the label and the filter in one operation.
    """
    try:
        # Create Gmail client with user credentials
        credentials_dict = request.credentials.model_dump()
        
        if not gmail_service.create_gmail_client(credentials_dict):
            raise HTTPException(
                status_code=400,
                detail="Failed to authenticate with Gmail API"
            )
        
        # Set up complete labeling system
        label_name = request.label_name or "Job Applications"
        label_id = gmail_service.setup_job_application_labeling(label_name)
        
        return FilterSetupResponse(
            success=True,
            label_id=label_id,
            message=f"Successfully set up '{label_name}' label and filter"
        )
        
    except (ServiceOperationError, ServiceInitializationError) as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up Gmail filter: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/test-connection")
async def test_gmail_connection(
    credentials: GmailCredentials,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Test Gmail API connection with provided credentials.
    """
    try:
        credentials_dict = credentials.model_dump()
        
        if gmail_service.create_gmail_client(credentials_dict):
            return {"success": True, "message": "Gmail connection successful"}
        else:
            return {"success": False, "message": "Gmail connection failed"}
            
    except Exception as e:
        logger.error(f"Error testing Gmail connection: {str(e)}")
        return {"success": False, "message": f"Connection error: {str(e)}"}


