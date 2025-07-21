from typing import Optional, Dict, Any
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from .base_service import BaseService, ServiceInitializationError, ServiceOperationError
from ..core.config import settings


class GmailService(BaseService):
    """Service for managing Gmail API operations including labels and filters."""
    
    def __init__(self):
        self.service = None
        super().__init__()
    
    def _initialize(self) -> None:
        """Initialize Gmail service configuration."""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ServiceInitializationError("Google OAuth credentials are required")
        self._log_operation("Gmail service initialized")
    
    def create_gmail_client(self, user_credentials: Dict[str, Any]) -> bool:
        """
        Create a Gmail API client using user's OAuth credentials.
        
        Args:
            user_credentials: Dictionary containing OAuth tokens and refresh tokens
            
        Returns:
            bool: True if client creation successful, False otherwise
        """
        try:
            creds = Credentials(
                token=user_credentials.get("access_token"),
                refresh_token=user_credentials.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.modify",
                    "https://www.googleapis.com/auth/gmail.labels"
                ]
            )
            
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            self.service = build("gmail", "v1", credentials=creds)
            self._log_operation("Gmail client created successfully")
            return True
            
        except Exception as e:
            self._log_error("creating Gmail client", e)
            return False
    
    def create_gmail_client_with_service_account(self, service_account_file: str) -> bool:
        """
        Create a Gmail API client using service account credentials.
        
        Args:
            service_account_file: Path to service account JSON file
            
        Returns:
            bool: True if client creation successful, False otherwise
        """
        try:
            creds = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.modify",
                    "https://www.googleapis.com/auth/gmail.labels"
                ]
            )
            
            self.service = build("gmail", "v1", credentials=creds)
            self._log_operation("Gmail client created successfully with service account")
            return True
            
        except Exception as e:
            self._log_error("creating Gmail client with service account", e)
            return False
    
    def get_or_create_label(self, label_name: str = "Job Applications") -> str:
        """
        Get existing label ID or create a new label for job applications.
        
        Args:
            label_name: Name of the label to create/find
            
        Returns:
            str: Label ID if successful
            
        Raises:
            ServiceOperationError: If operation fails
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")
        
        try:
            labels_result = self.service.users().labels().list(userId="me").execute()
            labels = labels_result.get("labels", [])
            
            for label in labels:
                if label["name"] == label_name:
                    self._log_operation("found existing label", f"{label_name} with ID: {label['id']}")
                    return label["id"]
            
            label_body = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
                "color": {
                    "backgroundColor": "#16a085", 
                    "textColor": "#ffffff"
                }
            }
            
            result = self.service.users().labels().create(
                userId="me",
                body=label_body
            ).execute()
            
            self._log_operation("created new label", f"{label_name} with ID: {result['id']}")
            return result["id"]
            
        except HttpError as e:
            self._log_error("getting or creating label", e)
            raise ServiceOperationError(f"Failed to get or create label: {str(e)}")
    
    def create_job_application_filter(self, label_id: str) -> bool:
        """
        Create a Gmail filter to automatically label job application emails.
        
        Args:
            label_id: ID of the label to apply to matching emails
            
        Returns:
            bool: True if filter creation successful
            
        Raises:
            ServiceOperationError: If operation fails
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")
        
        try:
            filter_criteria = {
                "query": (
                    "(subject:(resume OR CV OR application OR interview OR position OR "
                    "opportunity OR hiring OR recruitment OR job OR career OR "
                    "candidate OR applicant OR offer OR screening OR assessment OR "
                    "\"application received\" OR \"we received your application\" OR \"confirmation of your application\" OR "
                    "\"thank you for applying\" OR \"thank you for your application\" OR \"thank you for your interest\" OR "
                    "\"your application to\" OR \"application submitted for\" OR "
                    "\"interview invitation\" OR \"schedule interview\" OR \"invitation to interview\" OR "
                    "\"next steps\" OR \"move forward\" OR \"follow-up\" OR "
                    "\"job offer\" OR \"offer letter\" OR \"pleased to inform\" OR \"status update\" OR \"application status\" OR "
                    "\"talent partner\" OR \"technical recruiter\" OR \"sourcing recruiter\" OR \"founding engineer\" OR "
                    "\"quick call\" OR SWE OR SDE OR \"be a good fit\" OR "
                    "\"job application\" OR \"Job opportunity\" OR \"Career opportunity\") OR "
                    "from:(@linkedin.com OR @indeed.com OR @glassdoor.com OR "
                    "@workday.com OR @greenhouse.io OR @lever.co OR @bamboohr.com OR "
                    "@jobvite.com OR @smartrecruiters.com OR @talentsoft.com OR "
                    "@successfactors.com OR @cornerstone.com OR noreply OR recruiting OR "
                    "talent OR hr OR careers) OR "
                    "has:attachment filename:(pdf OR doc OR docx)) AND "
                    "NOT (subject:(spam OR advertisement OR promotion OR sale))"
                )
            }
            
            filter_action = {
                "addLabelIds": [label_id],
                "removeLabelIds": ["SPAM"],
                "markAsRead": False  
            }
            
            filter_body = {
                "criteria": filter_criteria,
                "action": filter_action
            }
            
            result = self.service.users().settings().filters().create(
                userId="me",
                body=filter_body
            ).execute()
            
            self._log_operation("created job application filter", f"ID: {result['id']}")
            return True
            
        except HttpError as e:
            self._log_error("creating filter", e)
            raise ServiceOperationError(f"Failed to create filter: {str(e)}")
    
    def setup_job_application_labeling(self, label_name: str = "Job Applications") -> str:
        """
        Complete setup for job application email labeling.
        Creates label and filter in one operation.
        
        Args:
            label_name: Name of the label for job applications
            
        Returns:
            str: Label ID if successful setup
            
        Raises:
            ServiceOperationError: If operation fails
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")
        
        label_id = self.get_or_create_label(label_name)
        if not label_id:
            raise ServiceOperationError("Failed to get or create label")
        
        if not self.create_job_application_filter(label_id):
            raise ServiceOperationError("Failed to create filter")
        
        self._log_operation("successfully set up job application labeling", f"label ID: {label_id}")
        return label_id
    
    def list_existing_filters(self) -> list:
        """
        List all existing Gmail filters for the user.
        
        Returns:
            list: List of existing filters
            
        Raises:
            ServiceOperationError: If operation fails
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")
        
        try:
            result = self.service.users().settings().filters().list(userId="me").execute()
            filters = result.get("filter", [])
            
            self._log_operation("listed existing filters", f"found {len(filters)} filters")
            return filters
            
        except HttpError as e:
            self._log_error("listing filters", e)
            raise ServiceOperationError(f"Failed to list filters: {str(e)}")
    
    def delete_filter(self, filter_id: str) -> bool:
        """
        Delete a specific Gmail filter.
        
        Args:
            filter_id: ID of the filter to delete
            
        Returns:
            bool: True if deletion successful
            
        Raises:
            ServiceOperationError: If operation fails
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")
        
        try:
            self.service.users().settings().filters().delete(
                userId="me",
                id=filter_id
            ).execute()
            
            self._log_operation("deleted filter", f"ID: {filter_id}")
            return True
            
        except HttpError as e:
            self._log_error("deleting filter", e)
            raise ServiceOperationError(f"Failed to delete filter: {str(e)}")


# Global instance
gmail_service = GmailService()
