from __future__ import annotations

from pydantic import BaseModel, Field


class SyncV2Item(BaseModel):
    tx_id: str
    idempotency_key: str
    # base64(zlib(json_bytes))
    payload_b64z: str
    priority: int = Field(default=50, ge=0, le=100)


class SyncV2PushRequest(BaseModel):
    user_id: str
    device_id: str = ""
    items: list[SyncV2Item] = Field(default_factory=list)


class SyncV2ItemResult(BaseModel):
    tx_id: str
    idempotency_key: str
    result: str
    server_status: str
    risk_score: int = 0
    risk_level: str = "LOW"
    reasons: list[str] = Field(default_factory=list)
    detail: str = ""


class SyncV2PushResponse(BaseModel):
    server_time: str
    results: list[SyncV2ItemResult]

