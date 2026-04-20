from __future__ import annotations

"""Compatibility endpoints for the original offline-first prototype.

The early UI sends:
- POST /sync/transactions
- GET /rules

This router implements those endpoints but stores incoming encrypted payloads in Postgres
when available, so the project can demonstrate:
offline SQLite -> (night sync) -> server inbox (Postgres).
"""

import uuid
from datetime import UTC, datetime
from threading import Lock

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.server.db.session import get_db
from src.server.models.legacy_inbox import LegacySyncInbox


router = APIRouter(tags=["legacy-compat"])


class SyncRequest(BaseModel):
    user_id: str = Field(min_length=1)
    tx_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=8)
    payload_enc: str = Field(min_length=1)
    retry_count: int = 0


class SyncResponse(BaseModel):
    status: str = Field(pattern="^(synced|duplicate)$")
    server_time: str


class FraudRule(BaseModel):
    rule_id: str
    rule_version: str
    rule_data: dict
    updated_at: str


class RuleUpdateRequest(BaseModel):
    rules: list[FraudRule]


class RuleListResponse(BaseModel):
    rules: list[FraudRule]


_rule_lock = Lock()
_rules: dict[str, FraudRule] = {
    "base-high-amount": FraudRule(
        rule_id="base-high-amount",
        rule_version="1.0.0",
        rule_data={"threshold": 3000, "score": 35},
        updated_at=datetime.now(UTC).isoformat(),
    )
}


@router.post("/sync/transactions", response_model=SyncResponse)
def sync_transaction(payload: SyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    """Acknowledge receipt of an encrypted outbox item.

    Idempotency:
    - unique (user_id, idempotency_key) ensures duplicates are safely ignored.
    """
    item = LegacySyncInbox(
        inbox_id=uuid.uuid4().hex,
        user_id=payload.user_id,
        tx_id=payload.tx_id,
        idempotency_key=payload.idempotency_key,
        payload_enc=payload.payload_enc,
        retry_count=int(payload.retry_count or 0),
    )
    try:
        db.add(item)
        db.commit()
        return SyncResponse(status="synced", server_time=datetime.now(UTC).isoformat())
    except IntegrityError:
        db.rollback()
        return SyncResponse(status="duplicate", server_time=datetime.now(UTC).isoformat())


@router.get("/rules", response_model=RuleListResponse)
def list_rules() -> RuleListResponse:
    with _rule_lock:
        return RuleListResponse(rules=list(_rules.values()))


@router.post("/rules", response_model=RuleListResponse)
def update_rules(request: RuleUpdateRequest) -> RuleListResponse:
    with _rule_lock:
        for rule in request.rules:
            _rules[rule.rule_id] = rule
        return RuleListResponse(rules=list(_rules.values()))

