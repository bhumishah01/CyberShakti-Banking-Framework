"""Authentication service for PIN hashing, verification, and lockout control."""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import token_bytes

from src.database.init_db import DB_PATH, init_db

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
PIN_LENGTH = 4
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32


@dataclass(frozen=True)
class AuthResult:
    is_authenticated: bool
    reason: str
    failed_attempts: int
    lockout_until: str | None


def create_user(
    user_id: str,
    phone_number: str,
    pin: str,
    db_path: Path = DB_PATH,
    replace_existing: bool = False,
) -> None:
    """Create a user record with securely hashed PIN credentials."""
    init_db(db_path)
    _validate_pin(pin)
    now_iso = _now_utc().isoformat()
    pin_salt = token_bytes(16)
    phone_hash = _hash_phone(phone_number)
    pin_hash = _hash_pin(pin, pin_salt)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone() is not None
        if exists and not replace_existing:
            raise ValueError(f"user_exists:{user_id}")

        if exists and replace_existing:
            cursor.execute(
                """
                UPDATE users
                SET phone_hash = ?, pin_salt = ?, pin_hash = ?,
                    failed_attempts = 0, lockout_until = NULL, last_auth_at = NULL,
                    auth_config = ?, created_at = ?
                WHERE user_id = ?
                """,
                (
                    phone_hash,
                    pin_salt.hex(),
                    pin_hash.hex(),
                    json.dumps({"step_up_enabled": True}),
                    now_iso,
                    user_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (
                    user_id, phone_hash, pin_salt, pin_hash,
                    failed_attempts, lockout_until, last_auth_at, auth_config, created_at
                ) VALUES (?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                """,
                (
                    user_id,
                    phone_hash,
                    pin_salt.hex(),
                    pin_hash.hex(),
                    json.dumps({"step_up_enabled": True}),
                    now_iso,
                ),
            )
        conn.commit()


def authenticate_user(
    user_id: str,
    pin: str,
    db_path: Path = DB_PATH,
    now: datetime | None = None,
) -> AuthResult:
    """Authenticate a user with lockout-aware PIN verification."""
    init_db(db_path)
    _validate_pin(pin)
    current_time = now or _now_utc()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT pin_salt, pin_hash, failed_attempts, lockout_until
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return AuthResult(
                is_authenticated=False,
                reason="user_not_found",
                failed_attempts=0,
                lockout_until=None,
            )

        pin_salt_hex, pin_hash_hex, failed_attempts, lockout_until = row
        if _is_locked(lockout_until, current_time):
            return AuthResult(
                is_authenticated=False,
                reason="locked_out",
                failed_attempts=failed_attempts,
                lockout_until=lockout_until,
            )

        pin_salt = bytes.fromhex(pin_salt_hex)
        provided_hash_hex = _hash_pin(pin, pin_salt).hex()
        is_valid = hmac.compare_digest(provided_hash_hex, pin_hash_hex)
        if is_valid:
            cursor.execute(
                """
                UPDATE users
                SET failed_attempts = 0, lockout_until = NULL, last_auth_at = ?
                WHERE user_id = ?
                """,
                (current_time.isoformat(), user_id),
            )
            conn.commit()
            return AuthResult(
                is_authenticated=True,
                reason="authenticated",
                failed_attempts=0,
                lockout_until=None,
            )

        next_failed_attempts = failed_attempts + 1
        next_lockout_until = None
        reason = "invalid_pin"
        if next_failed_attempts >= MAX_FAILED_ATTEMPTS:
            next_lockout_until = (current_time + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            reason = "lockout_started"

        cursor.execute(
            """
            UPDATE users
            SET failed_attempts = ?, lockout_until = ?
            WHERE user_id = ?
            """,
            (next_failed_attempts, next_lockout_until, user_id),
        )
        conn.commit()
        return AuthResult(
            is_authenticated=False,
            reason=reason,
            failed_attempts=next_failed_attempts,
            lockout_until=next_lockout_until,
        )


def verify_pin(user_id: str, pin: str, db_path: Path = DB_PATH) -> bool:
    """Boolean compatibility helper around `authenticate_user`."""
    return authenticate_user(user_id=user_id, pin=pin, db_path=db_path).is_authenticated


def derive_session_key(user_id: str, pin: str, db_path: Path = DB_PATH) -> bytes:
    """
    Derive a deterministic session key after successful PIN authentication.

    This key is a bridge step for Step 2 and will later be wrapped by OS keystore keys.
    """
    auth_result = authenticate_user(user_id=user_id, pin=pin, db_path=db_path)
    if not auth_result.is_authenticated:
        raise PermissionError(f"Cannot derive session key: {auth_result.reason}")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pin_salt FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError("User not found during key derivation")
        pin_salt_hex = row[0]

    salt = bytes.fromhex(pin_salt_hex)
    return hashlib.scrypt(
        (user_id + ":" + pin).encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )


def _validate_pin(pin: str) -> None:
    if not pin.isdigit() or len(pin) != PIN_LENGTH:
        raise ValueError(f"PIN must be exactly {PIN_LENGTH} digits")


def _hash_pin(pin: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        pin.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )


def _hash_phone(phone_number: str) -> str:
    return hashlib.sha256(phone_number.strip().encode("utf-8")).hexdigest()


def _is_locked(lockout_until: str | None, now: datetime) -> bool:
    if not lockout_until:
        return False
    try:
        return now < datetime.fromisoformat(lockout_until)
    except ValueError:
        return False


def _now_utc() -> datetime:
    return datetime.now(UTC)
