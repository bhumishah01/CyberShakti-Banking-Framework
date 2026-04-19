from __future__ import annotations

from pydantic import BaseModel, Field


class OutboxItem(BaseModel):
    tx_id: str
    idempotency_key: str
    payload_enc: str


class SyncPushRequest(BaseModel):
    user_id: str
    device_id: str = ""
    items: list[OutboxItem] = Field(default_factory=list)


class SyncItemResult(BaseModel):
    tx_id: str
    idempotency_key: str
    result: str  # synced/duplicate/rejected/conflict
    detail: str = ""
    server_status: str = "PENDING"


class SyncPushResponse(BaseModel):
    server_time: str
    results: list[SyncItemResult]

