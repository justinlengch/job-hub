import time
from typing import Any, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ...core.config import settings
from ..base_service import (
    BaseService,
    ServiceInitializationError,
    ServiceOperationError,
)


class GmailService(BaseService):
    """Service for managing Gmail API operations including labels, filters, and watch lifecycle."""

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
                    "https://www.googleapis.com/auth/gmail.labels",
                    "https://www.googleapis.com/auth/gmail.settings.basic",
                ],
            )

            if not creds.valid:
                if creds.refresh_token:
                    creds.refresh(Request())
                else:
                    self._log_error(
                        "creating Gmail client",
                        ValueError("Missing refresh_token; cannot mint access token"),
                    )
                    return False

            self.service = build("gmail", "v1", credentials=creds)
            self._log_operation("Gmail client created successfully")
            return True

        except Exception as e:
            self._log_error("creating Gmail client", e)
            return False

    def create_gmail_client_with_service_account(
        self, service_account_file: str
    ) -> bool:
        """
        Create a Gmail API client using service account credentials.
        """
        try:
            creds = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.labels",
                    "https://www.googleapis.com/auth/gmail.settings.basic",
                ],
            )

            self.service = build("gmail", "v1", credentials=creds)
            self._log_operation(
                "Gmail client created successfully with service account"
            )
            return True

        except Exception as e:
            self._log_error("creating Gmail client with service account", e)
            return False

    def get_or_create_label(self, label_name: str = "Job Applications") -> str:
        """
        Get existing label ID or create a new label for job applications.
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")

        try:
            labels_result = self.service.users().labels().list(userId="me").execute()
            labels = labels_result.get("labels", [])

            for label in labels:
                if label["name"] == label_name:
                    self._log_operation(
                        "found existing label", f"{label_name} with ID: {label['id']}"
                    )
                    return label["id"]

            label_body = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
                "color": {"backgroundColor": "#149e60", "textColor": "#ffffff"},
            }

            result = (
                self.service.users()
                .labels()
                .create(userId="me", body=label_body)
                .execute()
            )

            self._log_operation(
                "created new label", f"{label_name} with ID: {result['id']}"
            )
            return result["id"]

        except HttpError as e:
            self._log_error("getting or creating label", e)
            raise ServiceOperationError(f"Failed to get or create label: {str(e)}")

    def create_job_application_filter(self, label_id: str) -> bool:
        """
        Create a Gmail filter to automatically label job application emails.
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")

        try:
            existing_filters = self.list_existing_filters()
            for existing_filter in existing_filters:
                action = existing_filter.get("action", {})
                if label_id in action.get("addLabelIds", []):
                    # Compare criteria; if different, replace the filter
                    existing_query = (existing_filter.get("criteria") or {}).get(
                        "query"
                    )
                    desired_query = (
                        None  # will be set below once filter_criteria is defined
                    )
                    # Defer immediate return; if criteria differ we will delete and recreate
                    filter_to_replace = existing_filter.get("id")
                    break

            filter_criteria = {
                "query": (
                    "(category:primary OR from:(@linkedin.com @indeed.com)) AND ("
                    'subject:("application received" OR "thank you for applying" OR '
                    '"your application to" OR "application submitted" OR '
                    '"interview invitation" OR "interview scheduled" OR "interview" OR '
                    '"software" OR "technical interview" OR "developer" OR "engineer" OR "backend" OR '
                    '"schedule interview" OR "assessment" OR "assessment invite" OR '
                    '"assessment requested" OR "assessment instructions" OR '
                    '"online assessment" OR "coding assessment" OR "coding test" OR '
                    '"technical test" OR "take-home assignment" OR "challenge" OR "assignment" OR '
                    '"offer letter" OR "job offer" OR '
                    '"regret to inform" OR "application status" OR '
                    '"decision on your application") '
                    "OR "
                    "from:(*@greenhouse.io *@lever.co *@ashbyhq.com *@smartrecruiters.com "
                    "*@myworkday.com *@workday.com *@recruitee.com *@workablemail.com)) "
                    "-category:promotions "
                    '-subject:(sale OR discount OR "% off" OR "free shipping" OR newsletter OR digest OR webinar OR promo OR event)'
                )
            }
            # If an existing filter for this label was found, decide whether to keep or replace it
            try:
                if "filter_to_replace" in locals():
                    desired_query = filter_criteria["query"]
                    if (
                        existing_query
                        and existing_query.strip() == desired_query.strip()
                    ):
                        self._log_operation(
                            "filter already exists",
                            f"Using existing filter for label ID: {label_id}",
                        )
                        return True
                    # Criteria changed — replace existing filter
                    if filter_to_replace:
                        self.delete_filter(filter_to_replace)
            except Exception:
                # Best-effort replacement; continue to (re)create below
                pass

            filter_action = {
                "addLabelIds": [label_id],
                "removeLabelIds": ["SPAM"],
                "markAsRead": False,
            }

            filter_body = {"criteria": filter_criteria, "action": filter_action}

            try:
                result = (
                    self.service.users()
                    .settings()
                    .filters()
                    .create(userId="me", body=filter_body)
                    .execute()
                )

                self._log_operation(
                    "created job application filter", f"ID: {result['id']}"
                )
                return True

            except HttpError as filter_error:
                if (
                    "already exists" in str(filter_error).lower()
                    or filter_error.resp.status == 409
                ):
                    self._log_operation(
                        "filter already exists", "Using existing filter configuration"
                    )
                    return True
                else:
                    raise filter_error

        except HttpError as e:
            self._log_error("creating filter", e)
            raise ServiceOperationError(f"Failed to create filter: {str(e)}")

    def setup_job_application_labeling(
        self, label_name: str = "Job Applications"
    ) -> str:
        """
        Complete setup for job application email labeling.
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")

        try:
            label_id = self.get_or_create_label(label_name)
            if not label_id:
                raise ServiceOperationError("Failed to get or create label")

            if not self.create_job_application_filter(label_id):
                raise ServiceOperationError("Failed to create filter")

            self._log_operation(
                "successfully set up job application labeling", f"label ID: {label_id}"
            )
            return label_id

        except Exception as e:
            self._log_error("setting up job application labeling", e)
            raise ServiceOperationError(f"Failed to set up labeling: {str(e)}")

    def list_existing_filters(self) -> list:
        """
        List all existing Gmail filters for the user.
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")

        try:
            result = (
                self.service.users().settings().filters().list(userId="me").execute()
            )
            filters = result.get("filter", [])

            self._log_operation(
                "listed existing filters", f"found {len(filters)} filters"
            )
            return filters

        except HttpError as e:
            self._log_error("listing filters", e)
            raise ServiceOperationError(f"Failed to list filters: {str(e)}")

    def delete_filter(self, filter_id: str) -> bool:
        """
        Delete a specific Gmail filter.
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")

        try:
            self.service.users().settings().filters().delete(
                userId="me", id=filter_id
            ).execute()

            self._log_operation("deleted filter", f"ID: {filter_id}")
            return True

        except HttpError as e:
            self._log_error("deleting filter", e)
            raise ServiceOperationError(f"Failed to delete filter: {str(e)}")

    # --- Watch lifecycle helpers ---

    def start_watch(
        self,
        topic_fqn: str,
        label_ids: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """
        Start (or restart) a Gmail push watch.
        Returns dict with history_id and expiration.
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")

        body: Dict[str, Any] = {
            "topicName": topic_fqn,
        }
        if label_ids:
            body["labelIds"] = label_ids
            body["labelFilterBehavior"] = "INCLUDE"

        try:
            resp = self.service.users().watch(userId="me", body=body).execute()
            result = {
                "history_id": resp.get("historyId"),
                "expiration": int(resp.get("expiration", 0)),
            }
            self._log_operation(
                "watch started",
                f"history_id={result['history_id']} exp={result['expiration']}",
            )
            return result
        except HttpError as e:
            self._log_error("starting watch", e)
            raise ServiceOperationError(f"Failed to start watch: {e}")

    def stop_watch(self) -> None:
        """
        Stop the current Gmail watch (best-effort).
        """
        if not self.service:
            raise ServiceOperationError("Gmail service not initialized")
        try:
            self.service.users().stop(userId="me").execute()
            self._log_operation("watch stopped")
        except HttpError as e:
            # Not fatal; log and continue
            self._log_error("stopping watch", e)

    def refresh_watch_if_needed(
        self,
        topic_fqn: str,
        label_ids: Optional[list[str]],
        watch_expiration_ms: Optional[int],
        threshold_seconds: int = 600,
    ) -> Optional[Dict[str, Any]]:
        """
        Renew watch if within threshold_seconds of expiration.
        Returns new watch data when refreshed, else None.
        """
        now_ms = int(time.time() * 1000)
        if not watch_expiration_ms:
            # No existing watch info; start one
            return self.start_watch(topic_fqn, label_ids)

        remaining = watch_expiration_ms - now_ms
        if remaining <= threshold_seconds * 1000:
            return self.start_watch(topic_fqn, label_ids)
        return None


# Global instance
gmail_service = GmailService()
