"""
Crypto service exports and lightweight helpers.

This module exposes:
- crypto_service: a process-wide AES-GCM helper instance
- decrypt_refresh_token: convenience function for pipeline-only in-memory decryption

Important:
- Do not persist plaintext tokens. This helper is intended solely for ephemeral,
  in-memory use within the pipeline (e.g., to mint access tokens or call Gmail APIs).
"""

from typing import Final

from .crypto_service import (
    CryptoError,
    CryptoInitializationError,
    CryptoService,
    crypto_service,
)


def decrypt_refresh_token(nonce_b64: str, cipher_b64: str) -> str:
    """
    Decrypt an AES-GCM encrypted Gmail refresh token.

    Parameters:
    - nonce_b64: Base64-encoded 12-byte nonce used during encryption.
    - cipher_b64: Base64-encoded ciphertext (includes GCM tag).

    Returns:
    - The plaintext refresh token as a string.

    Notes:
    - This is for pipeline usage only. Do NOT log or persist the plaintext.
    - Raises CryptoError on base64/cryptographic errors.
    """
    return crypto_service.decrypt(nonce_b64, cipher_b64)


__all__: Final = [
    "CryptoService",
    "CryptoError",
    "CryptoInitializationError",
    "crypto_service",
    "decrypt_refresh_token",
]
