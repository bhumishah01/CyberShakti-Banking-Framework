from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from src.server.core.security import create_access_token, hash_password, verify_password
from src.server.models.device import Device
from src.server.models.user import User


def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.strip().encode("utf-8")).hexdigest()


def register_user(db: Session, *, user_id: str, phone: str, password: str, role: str) -> User:
    existing = db.get(User, user_id)
    if existing:
        raise ValueError("user_exists")
    user = User(
        user_id=user_id,
        role=role,
        phone_hash=_hash_phone(phone),
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, *, user_id: str, password: str, device_id: str = "") -> tuple[str, str]:
    user = db.get(User, user_id)
    if user is None:
        raise PermissionError("invalid_credentials")
    if not verify_password(password, user.password_hash):
        raise PermissionError("invalid_credentials")

    # Device binding: enroll first seen, mark untrusted if new.
    if device_id:
        device = db.get(Device, device_id)
        if device is None:
            # Enroll to this user.
            db.add(Device(device_id=device_id, user_id=user.user_id, trust_level="trusted"))
            db.commit()
        else:
            if device.user_id != user.user_id:
                # Same device id used by another user => suspicious. Mark untrusted.
                device.trust_level = "untrusted"
                db.commit()

    token = create_access_token(subject=user.user_id, role=user.role)
    return token, user.role

