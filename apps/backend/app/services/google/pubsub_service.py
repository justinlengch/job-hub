import base64
import json
import logging
from typing import Any, Dict

from google.auth.transport.requests import Request
from google.oauth2 import id_token

from app.core.config import settings

logger = logging.getLogger(__name__)


class PubSubService:
    """
    Minimal helpers for verifying Google Pub/Sub push OIDC tokens
    and decoding the push message envelope carrying Gmail change notifications.
    """

    _ALLOWED_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}

    def verify_token(self, authorization_header: str) -> Dict[str, Any]:
        """
        Verify the OIDC token included with a Pub/Sub push request.

        Returns the decoded claims if valid; raises ValueError otherwise.
        """
        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise ValueError("Missing or invalid Authorization header")

        token = authorization_header.split(" ", 1)[1].strip()
        if not token:
            raise ValueError("Empty bearer token")

        claims = id_token.verify_oauth2_token(
            token,
            Request(),
            audience=settings.PUBSUB_AUDIENCE,
        )

        issuer = claims.get("iss")
        if issuer not in self._ALLOWED_ISSUERS:
            raise ValueError("Invalid token issuer")

        email = claims.get("email")
        if not email or email != settings.PUSH_SA_EMAIL:
            raise ValueError("Service account email mismatch")

        aud = claims.get("aud")
        if aud != settings.PUBSUB_AUDIENCE:
            raise ValueError("Token audience mismatch")

        return claims

    def decode_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decode a Pub/Sub push JSON body into structured Gmail watch notification data.

        Expected envelope shape:
        {
          "message": {
             "data": "<base64>",
             "messageId": "...",
             "publishTime": "...",
             "attributes": { ... }
          },
          "subscription": "..."
        }
        """
        if not envelope:
            raise ValueError("Empty envelope")

        message = envelope.get("message")
        if not message:
            raise ValueError("Missing 'message' in envelope")

        data_b64 = message.get("data")
        if not data_b64:
            raise ValueError("Missing 'data' in message")

        try:
            decoded_bytes = base64.b64decode(data_b64)
            decoded_json = json.loads(decoded_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to decode message data: {e}")

        email_address = decoded_json.get("emailAddress")
        history_id = decoded_json.get("historyId")
        if not email_address or not history_id:
            raise ValueError("Decoded payload missing emailAddress or historyId")

        result = {
            "email_address": str(email_address),
            "history_id": str(history_id),
            "message_id": message.get("messageId"),
            "publish_time": message.get("publishTime"),
            "attributes": message.get("attributes") or {},
        }

        return result


pubsub_service = PubSubService()
