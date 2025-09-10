import logging
from typing import Dict, List, Tuple

from app.services.base_service import BaseService, ServiceOperationError

logger = logging.getLogger(__name__)


class GmailHistoryService(BaseService):
    """
    Enumerate Gmail history to find new/changed messages carrying a target label.
    Returns lightweight message refs (IDs only) for downstream parsing.
    """

    def _initialize(self) -> None:
        self._log_operation("Gmail history service initialized")

    def process_history(
        self, user_id: str, gmail_client, since_history_id: str, label_id: str
    ) -> Tuple[List[Dict], str]:
        """
        Walk Gmail History API starting at since_history_id and collect message refs
        that include the target label.

        Returns (refs, latest_history_id_seen)
        refs: [{messageId, threadId, historyId}]
        """
        if not gmail_client:
            raise ServiceOperationError("Gmail client not provided")

        refs: Dict[str, Dict] = {}
        latest_history_id = since_history_id
        page_token = None
        logger.info(
            f"history start user={user_id} since={since_history_id} label_id={label_id}"
        )

        try:
            while True:
                request = (
                    gmail_client.users()
                    .history()
                    .list(
                        userId="me",
                        startHistoryId=since_history_id,
                        historyTypes=["messageAdded", "labelAdded"],
                        pageToken=page_token,
                    )
                )
                response = request.execute()

                for hist in response.get("history", []):
                    hist_id = hist.get("id")
                    if hist_id and int(str(hist_id)) > int(str(latest_history_id)):
                        latest_history_id = hist_id

                    # messagesAdded entries contain new messages
                    for added in hist.get("messagesAdded", []):
                        msg = added.get("message", {})
                        labels = set(msg.get("labelIds", []))
                        if label_id in labels:
                            mid = msg.get("id")
                            if mid and mid not in refs:
                                refs[mid] = {
                                    "messageId": mid,
                                    "threadId": msg.get("threadId"),
                                    "historyId": str(hist_id),
                                }
                                logger.info(
                                    f"history ref_collected user={user_id} messageId={mid} threadId={msg.get('threadId')} historyId={hist_id} source=messagesAdded"
                                )

                    # labelAdded events may add the label after initial receipt
                    for labeled in hist.get("labelsAdded", []):
                        msg = labeled.get("message", {})
                        labels = set(msg.get("labelIds", []))
                        if label_id in labels:
                            mid = msg.get("id")
                            if mid and mid not in refs:
                                refs[mid] = {
                                    "messageId": mid,
                                    "threadId": msg.get("threadId"),
                                    "historyId": str(hist_id),
                                }
                                logger.info(
                                    f"history ref_collected user={user_id} messageId={mid} threadId={msg.get('threadId')} historyId={hist_id} source=labelsAdded"
                                )

                page_token = response.get("nextPageToken")
                logger.info(
                    f"history page_processed user={user_id} since={since_history_id} next_page={bool(page_token)} latest={latest_history_id}"
                )
                if not page_token:
                    break

            ref_list = list(refs.values())
            self._log_operation(
                "history processed",
                f"user={user_id} since={since_history_id} refs={len(ref_list)} latest={latest_history_id}",
            )

            # NOTE: We intentionally do not persist refs here (no dedicated table yet).
            # Downstream parsing flow will handle idempotent persistence of full email data.

            return ref_list, latest_history_id

        except Exception as e:
            self._log_error("processing history", e)
            raise ServiceOperationError(f"Failed to process Gmail history: {e}")


gmail_history_service = GmailHistoryService()
