"""Crypto helpers for encryption and integrity verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from secrets import token_bytes

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def derive_crypto_keys(session_key: bytes) -> tuple[bytes, bytes]:
    """Derive separate encryption and signature keys from a session key."""
    enc_key = hashlib.sha256(session_key + b":enc").digest()
    sig_key = hashlib.sha256(session_key + b":sig").digest()
    return enc_key, sig_key


def encrypt_payload(plaintext: str, key: bytes) -> dict[str, str]:
    """Encrypt a UTF-8 payload using AES-GCM."""
    nonce = token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "nonce": _b64(nonce),
        "ciphertext": _b64(ciphertext),
    }


def decrypt_payload(payload: dict[str, str], key: bytes) -> str:
    """Decrypt a payload produced by `encrypt_payload`."""
    nonce = _from_b64(payload["nonce"])
    ciphertext = _from_b64(payload["ciphertext"])
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def sign_payload(payload: str, key: bytes) -> str:
    """Create an HMAC-SHA256 signature for payload integrity."""
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(payload: str, signature: str, key: bytes) -> bool:
    """Verify HMAC signature in constant time."""
    expected = sign_payload(payload, key)
    return hmac.compare_digest(expected, signature)


def canonical_json(data: dict) -> str:
    """Stable JSON representation for deterministic signatures."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("utf-8")


def _from_b64(value: str) -> bytes:
    return base64.b64decode(value.encode("utf-8"))
