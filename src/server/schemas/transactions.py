from __future__ import annotations

from pydantic import BaseModel, Field


class TransactionCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    recipient: str = Field(min_length=1, max_length=120)
    device_id: str = ""


class TransactionResponse(BaseModel):
    tx_id: str
    user_id: str
    amount: float
    risk_score: int
    risk_level: str
    reason_codes: list[str]
    status: str

