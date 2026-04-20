"""Minimal backend API for sync acknowledgments and fraud rule distribution."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock

from fastapi import FastAPI
from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    # Newer UI sends user_id so the server can store/attribute offline sync items.
    user_id: str | None = None
    tx_id: str
    idempotency_key: str
    payload_enc: str
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


app = FastAPI(title="RuralShield Sync API", version="0.1.0")

_sync_lock = Lock()
_seen_idempotency_keys: set[str] = set()
_rule_lock = Lock()
_rules: dict[str, FraudRule] = {
    "base-high-amount": FraudRule(
        rule_id="base-high-amount",
        rule_version="1.0.0",
        rule_data={"threshold": 3000, "score": 35},
        updated_at=datetime.now(UTC).isoformat(),
    )
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ruralshield-sync-api"}


@app.post("/sync/transactions", response_model=SyncResponse)
def sync_transaction(payload: SyncRequest) -> SyncResponse:
    with _sync_lock:
        if payload.idempotency_key in _seen_idempotency_keys:
            return SyncResponse(status="duplicate", server_time=datetime.now(UTC).isoformat())
        _seen_idempotency_keys.add(payload.idempotency_key)

    return SyncResponse(status="synced", server_time=datetime.now(UTC).isoformat())


@app.get("/rules", response_model=RuleListResponse)
def list_rules() -> RuleListResponse:
    with _rule_lock:
        return RuleListResponse(rules=list(_rules.values()))


@app.post("/rules", response_model=RuleListResponse)
def update_rules(request: RuleUpdateRequest) -> RuleListResponse:
    with _rule_lock:
        for rule in request.rules:
            _rules[rule.rule_id] = rule
        return RuleListResponse(rules=list(_rules.values()))
