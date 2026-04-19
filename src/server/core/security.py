from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import jwt
from passlib.context import CryptContext

from src.server.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, role: str) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.jwt_access_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _aes_key() -> bytes:
    # Derive a stable 32-byte AES key from env config.
    return hashlib.sha256(settings.field_enc_key.encode("utf-8")).digest()


def encrypt_field(plaintext: str, *, aad: str) -> str:
    # AES-GCM encryption; returns base64(nonce + ciphertext).
    aesgcm = AESGCM(_aes_key())
    nonce = hashlib.sha256(f"{aad}:{datetime.now(UTC).isoformat()}".encode("utf-8")).digest()[:12]
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad.encode("utf-8"))
    return base64.urlsafe_b64encode(nonce + ct).decode("utf-8")


def decrypt_field(token: str, *, aad: str) -> str:
    aesgcm = AESGCM(_aes_key())
    raw = base64.urlsafe_b64decode(token.encode("utf-8"))
    nonce, ct = raw[:12], raw[12:]
    pt = aesgcm.decrypt(nonce, ct, aad.encode("utf-8"))
    return pt.decode("utf-8")

