"""Authentication service for PIN hashing, verification, and lockout control.

This file handles user security:
- PIN hashing + verification
- lockout after repeated failures
- trusted contact + panic freeze settings
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import token_bytes

from src.audit.change_log import log_change
from src.database.init_db import DB_PATH, init_db

# === Security policy settings ===
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
PIN_LENGTH = 4
# Scrypt parameters (slow hash for PIN security)
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32


@dataclass(frozen=True)
class AuthResult:
    # Returned by authenticate_user() to explain outcome
    is_authenticated: bool
    reason: str
    failed_attempts: int
    lockout_until: str | None


def create_user(
    user_id: str,
    phone_number: str,
    pin: str,
    title: str = "",
    first_name: str = "",
    last_name: str = "",
    db_path: Path = DB_PATH,
    replace_existing: bool = False,
) -> None:
    """Create a user record with securely hashed PIN credentials."""
    # Validate and hash user info
    init_db(db_path)
    _validate_pin(pin)
    now_iso = _now_utc().isoformat()
    pin_salt = token_bytes(16)
    phone_hash = _hash_phone(phone_number)
    pin_hash = _hash_pin(pin, pin_salt)
    clean_title = str(title or "").strip().lower()
    if clean_title not in {"mr", "ms", "mx", ""}:
        clean_title = ""
    clean_first = str(first_name or "").strip()
    clean_last = str(last_name or "").strip()

    # Default auth config for step-up + panic freeze
    default_auth_config = {
        "step_up_enabled": True,
        "trusted_contact": "",
        "freeze_until": "",
        # Biometric + device placeholders (offline prototype).
        "face_hash_algo": "",
        "face_hash": "",
        "device_id": "",
    }

    change_events: list[dict] = []
    # Save user to SQLite
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone() is not None
        if exists and not replace_existing:
            raise ValueError(f"user_exists:{user_id}")

        if exists and replace_existing:
            cursor.execute(
                "SELECT phone_hash FROM users WHERE user_id = ?",
                (user_id,),
            )
            prev_phone_hash = cursor.fetchone()
            cursor.execute(
                """
                UPDATE users
                SET title = ?, first_name = ?, last_name = ?,
                    phone_hash = ?, pin_salt = ?, pin_hash = ?,
                    failed_attempts = 0, lockout_until = NULL, last_auth_at = NULL,
                    auth_config = ?, created_at = ?
                WHERE user_id = ?
                """,
                (
                    clean_title,
                    clean_first,
                    clean_last,
                    phone_hash,
                    pin_salt.hex(),
                    pin_hash.hex(),
                    json.dumps(default_auth_config),
                    now_iso,
                    user_id,
                ),
            )
            change_events.extend(
                [
                    {
                        "field_name": "phone_hash",
                        "old_value": prev_phone_hash[0] if prev_phone_hash else "",
                        "new_value": phone_hash,
                        "source": "user_replace",
                    },
                    {
                        "field_name": "pin_hash",
                        "old_value": "<redacted>",
                        "new_value": "<redacted>",
                        "source": "user_replace",
                    },
                ]
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (
                    user_id, title, first_name, last_name, phone_hash, pin_salt, pin_hash,
                    failed_attempts, lockout_until, last_auth_at, auth_config, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                """,
                (
                    user_id,
                    clean_title,
                    clean_first,
                    clean_last,
                    phone_hash,
                    pin_salt.hex(),
                    pin_hash.hex(),
                    json.dumps(default_auth_config),
                    now_iso,
                ),
            )
            change_events.append(
                {
                    "field_name": "user_created",
                    "old_value": "",
                    "new_value": "created",
                    "source": "user_create",
                }
            )
        conn.commit()

    for event in change_events:
        log_change(
            entity_type="user",
            entity_id=user_id,
            field_name=event["field_name"],
            old_value=event["old_value"],
            new_value=event["new_value"],
            actor=user_id,
            source=event["source"],
            db_path=db_path,
        )


def set_trusted_contact(
    user_id: str, pin: str, trusted_contact: str, db_path: Path = DB_PATH
) -> None:
    """Set or update trusted contact for high-risk approvals."""
    # Only allow if PIN is valid
    if not trusted_contact.strip():
        raise ValueError("trusted_contact cannot be empty")
    _ = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    config = get_user_auth_config(user_id=user_id, db_path=db_path)
    config["trusted_contact"] = trusted_contact.strip()
    _update_auth_config(user_id=user_id, config=config, db_path=db_path)

def remove_trusted_contact(user_id: str, pin: str, db_path: Path = DB_PATH) -> None:
    """Remove trusted contact (set to empty) after validating PIN."""
    _ = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    config = get_user_auth_config(user_id=user_id, db_path=db_path)
    config["trusted_contact"] = ""
    _update_auth_config(user_id=user_id, config=config, db_path=db_path)


def enable_panic_freeze(
    user_id: str, pin: str, minutes: int = 60, db_path: Path = DB_PATH
) -> str:
    """Freeze outgoing transactions for a limited duration."""
    # Validate PIN, then set freeze time in auth_config
    if minutes <= 0:
        raise ValueError("minutes must be > 0")
    _ = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    freeze_until = (_now_utc() + timedelta(minutes=minutes)).isoformat()
    config = get_user_auth_config(user_id=user_id, db_path=db_path)
    config["freeze_until"] = freeze_until
    _update_auth_config(user_id=user_id, config=config, db_path=db_path)
    return freeze_until


def get_user_auth_config(user_id: str, db_path: Path = DB_PATH) -> dict:
    # Read auth config from DB (step-up, trusted contact, freeze)
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT auth_config FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    if row is None:
        raise ValueError(f"user_not_found:{user_id}")
    raw = row[0] or "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("step_up_enabled", True)
    payload.setdefault("trusted_contact", "")
    payload.setdefault("freeze_until", "")
    return payload


def is_user_frozen(user_id: str, db_path: Path = DB_PATH) -> bool:
    # True if panic freeze window is active
    config = get_user_auth_config(user_id=user_id, db_path=db_path)
    freeze_until = config.get("freeze_until", "")
    if not freeze_until:
        return False
    try:
        return _now_utc() < datetime.fromisoformat(str(freeze_until))
    except ValueError:
        return False


def authenticate_user(
    user_id: str,
    pin: str,
    db_path: Path = DB_PATH,
    now: datetime | None = None,
) -> AuthResult:
    """Authenticate a user with lockout-aware PIN verification."""
    # Main PIN verification + lockout logic
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
        # Suspicious pattern alert: multiple failed login attempts.
        if next_failed_attempts in {3, 5}:
            try:
                from src.database.monitoring_store import create_alert, create_notification

                create_alert(
                    alert_type="FAILED_LOGINS",
                    severity="MEDIUM" if next_failed_attempts == 3 else "HIGH",
                    message=f"{user_id}: {next_failed_attempts} failed login attempts",
                    user_id=user_id,
                    metadata={"failed_attempts": next_failed_attempts},
                    db_path=db_path,
                )
                create_notification(
                    notif_type="suspicious_activity",
                    title="Suspicious login attempts",
                    body=f"{next_failed_attempts} failed login attempts detected. If this wasn't you, freeze the account.",
                    role="customer",
                    user_id=user_id,
                    db_path=db_path,
                )
            except Exception:
                pass
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
    # This key is used to derive encryption + signature keys
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
    # PIN must be exactly 4 digits
    if not pin.isdigit() or len(pin) != PIN_LENGTH:
        raise ValueError(f"PIN must be exactly {PIN_LENGTH} digits")


def _hash_pin(pin: str, salt: bytes) -> bytes:
    # Slow hash for PIN storage
    return hashlib.scrypt(
        pin.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )


def _hash_phone(phone_number: str) -> str:
    # Store a hash of phone number (not raw)
    return hashlib.sha256(phone_number.strip().encode("utf-8")).hexdigest()


def _is_locked(lockout_until: str | None, now: datetime) -> bool:
    # Returns True if lockout is still active
    if not lockout_until:
        return False
    try:
        # Be defensive: if some older data format stored a dict-like value, avoid AttributeError.
        val = lockout_until
        if isinstance(val, dict):
            val = val.get("lockout_until") or val.get("value") or val.get("$date") or ""
        return now < datetime.fromisoformat(str(val))
    except ValueError:
        return False


def _now_utc() -> datetime:
    # Unified time source (UTC)
    return datetime.now(UTC)


def _update_auth_config(user_id: str, config: dict, db_path: Path) -> None:
    # Persist auth_config JSON back to DB
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET auth_config = ? WHERE user_id = ?",
            (json.dumps(config), user_id),
        )
        conn.commit()


def enroll_or_verify_face_hash(
    user_id: str,
    pin: str,
    captured_algo: str,
    captured_hash: str,
    *,
    # Slightly relaxed threshold improves stability across low-end webcams / lighting changes.
    max_distance: int = 24,
    db_path: Path = DB_PATH,
) -> tuple[bool, str]:
    """Enroll face hash on first use; verify on subsequent logins.

    Returns (ok, reason):
    - ok=True, reason='enrolled' when first-time enrollment happens
    - ok=True, reason='verified' when match is within threshold
    - ok=False, reason='mismatch' when match fails
    """
    # Require correct PIN before any biometric action.
    _ = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)

    config = get_user_auth_config(user_id=user_id, db_path=db_path)
    stored_algo = str(config.get("face_hash_algo", "") or "")
    stored_hash = str(config.get("face_hash", "") or "")

    captured_algo = (captured_algo or "").strip().lower()
    captured_hash = (captured_hash or "").strip().lower()
    if not captured_algo or not captured_hash:
        return False, "missing"

    if not stored_hash:
        config["face_hash_algo"] = captured_algo
        config["face_hash"] = captured_hash
        _update_auth_config(user_id=user_id, config=config, db_path=db_path)
        log_change(
            entity_type="user",
            entity_id=user_id,
            field_name="face_hash",
            old_value="",
            new_value="<enrolled>",
            actor=user_id,
            source="face_enroll",
            db_path=db_path,
        )
        return True, "enrolled"

    if stored_algo != captured_algo:
        return False, "algo_mismatch"

    # Local import to avoid circular dependency from auth -> ui.
    from src.auth.biometric import hamming_distance_hex64

    distance = hamming_distance_hex64(stored_hash, captured_hash)
    return (distance <= max_distance), ("verified" if distance <= max_distance else "mismatch")


def refresh_face_hash_on_trusted_device(
    *,
    user_id: str,
    pin: str,
    captured_algo: str,
    captured_hash: str,
    db_path: Path = DB_PATH,
) -> None:
    """Refresh stored face hash after successful PIN on a trusted device.

    Why this exists:
    - Webcam lighting/angle changes can cause dHash drift and repeated false mismatches.
    - For a demo/prototype, it's better UX to "heal" the template when device trust is high.

    Security note:
    - Call this ONLY after device verification indicates the device is trusted (not new_device).
    """
    _ = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    config = get_user_auth_config(user_id=user_id, db_path=db_path)
    old_algo = str(config.get("face_hash_algo", "") or "")
    old_hash = str(config.get("face_hash", "") or "")

    captured_algo = (captured_algo or "").strip().lower()
    captured_hash = (captured_hash or "").strip().lower()
    if not captured_algo or not captured_hash:
        return

    config["face_hash_algo"] = captured_algo
    config["face_hash"] = captured_hash
    _update_auth_config(user_id=user_id, config=config, db_path=db_path)

    # Log only that a refresh happened; do not store the raw hash in logs.
    log_change(
        entity_type="user",
        entity_id=user_id,
        field_name="face_hash",
        old_value="<set>" if (old_algo or old_hash) else "",
        new_value="<refreshed>",
        actor=user_id,
        source="face_refresh_trusted_device",
        db_path=db_path,
    )


def enroll_or_verify_device_id(
    user_id: str,
    pin: str,
    device_id: str,
    *,
    db_path: Path = DB_PATH,
) -> tuple[bool, str]:
    """Enroll device id on first use; flag new device on mismatch.

    Returns (ok, reason):
    - ok=True, reason='enrolled' when first-time enrollment happens
    - ok=True, reason='verified' when the device matches
    - ok=True, reason='new_device' when a different device is seen (not a hard-fail)
    """
    _ = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    device_id = (device_id or "").strip()
    if not device_id:
        return False, "missing"

    config = get_user_auth_config(user_id=user_id, db_path=db_path)
    stored = str(config.get("device_id", "") or "").strip()
    if not stored:
        config["device_id"] = device_id
        _update_auth_config(user_id=user_id, config=config, db_path=db_path)
        try:
            from src.database.device_store import upsert_device

            upsert_device(user_id=user_id, device_id=device_id, is_trusted=True, db_path=db_path)
        except Exception:
            pass
        log_change(
            entity_type="user",
            entity_id=user_id,
            field_name="device_id",
            old_value="",
            new_value="<enrolled>",
            actor=user_id,
            source="device_enroll",
            db_path=db_path,
        )
        return True, "enrolled"

    if stored == device_id:
        try:
            from src.database.device_store import upsert_device

            upsert_device(user_id=user_id, device_id=device_id, is_trusted=True, db_path=db_path)
        except Exception:
            pass
        return True, "verified"
    try:
        from src.database.device_store import upsert_device

        upsert_device(user_id=user_id, device_id=device_id, is_trusted=False, db_path=db_path)
    except Exception:
        pass
    return True, "new_device"
