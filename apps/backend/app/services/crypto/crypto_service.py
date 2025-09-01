import base64
import secrets
from typing import Dict, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


class CryptoError(Exception):
    """Base crypto error."""


class CryptoInitializationError(CryptoError):
    """Raised when the crypto service cannot initialize (bad/missing key)."""


class CryptoService:
    """
    AES-GCM encrypt/decrypt helper using a single 32-byte key provided via CRYPTO_KEY_B64.

    - Key is loaded once at process start.
    - AES-GCM uses a 12-byte random nonce per encryption.
    - Outputs base64-encoded 'nonce_b64' and 'cipher_b64'.
    - Does not log or return plaintext beyond the decrypt() call result.
    """

    NONCE_SIZE_BYTES = 12  # Recommended size for AES-GCM nonce

    def __init__(
        self, key_b64: Optional[str] = None, key_version: Optional[int] = None
    ):
        key_b64 = key_b64 if key_b64 is not None else settings.CRYPTO_KEY_B64
        if not key_b64:
            raise CryptoInitializationError(
                "CRYPTO_KEY_B64 is required for AES-GCM encryption"
            )

        try:
            key = base64.b64decode(key_b64, validate=True)
        except Exception as e:
            raise CryptoInitializationError(f"CRYPTO_KEY_B64 is not valid base64: {e}")

        if len(key) != 32:
            raise CryptoInitializationError(
                f"CRYPTO_KEY_B64 must decode to 32 bytes (got {len(key)})"
            )

        self._key = key
        self._aesgcm = AESGCM(self._key)
        # Versioning enables future key rotation; callers can persist this number with ciphertext
        self._key_version = (
            key_version if key_version is not None else settings.GMAIL_KEY_VERSION
        )

    @property
    def key_version(self) -> int:
        return self._key_version

    def encrypt(self, plaintext: str) -> Dict[str, str]:
        """
        Encrypt plaintext with AES-GCM.

        Returns a dict:
          {
            "gmail_refresh_nonce_b64": "<base64 nonce>",
            "gmail_refresh_cipher_b64": "<base64 ciphertext>",
            "gmail_key_version": "<int as str>"
          }

        Note: The ciphertext contains the GCM auth tag appended by the AESGCM implementation.
        """
        if not isinstance(plaintext, str):
            raise CryptoError("encrypt() expects a string plaintext")

        nonce = secrets.token_bytes(self.NONCE_SIZE_BYTES)
        data = plaintext.encode("utf-8")

        # No associated data; add if you want integrity bind to context
        cipher = self._aesgcm.encrypt(nonce, data, associated_data=None)

        return {
            "gmail_refresh_nonce_b64": base64.b64encode(nonce).decode("ascii"),
            "gmail_refresh_cipher_b64": base64.b64encode(cipher).decode("ascii"),
            "gmail_key_version": str(self._key_version),
        }

    def decrypt(self, nonce_b64: str, cipher_b64: str) -> str:
        """
        Decrypt AES-GCM ciphertext and return plaintext string.
        """
        try:
            nonce = base64.b64decode(nonce_b64, validate=True)
            cipher = base64.b64decode(cipher_b64, validate=True)
        except Exception as e:
            raise CryptoError(f"Invalid base64 input: {e}")

        if len(nonce) != self.NONCE_SIZE_BYTES:
            raise CryptoError(
                f"Invalid nonce length: expected {self.NONCE_SIZE_BYTES}, got {len(nonce)}"
            )

        try:
            plain_bytes = self._aesgcm.decrypt(nonce, cipher, associated_data=None)
            return plain_bytes.decode("utf-8")
        except Exception as e:
            # Do not include sensitive material in error messages
            raise CryptoError(f"Decryption failed: {e}")


# Global instance to be reused across the application
crypto_service = CryptoService()
