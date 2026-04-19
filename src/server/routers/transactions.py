from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.server.api.deps import require_roles
from src.server.db.session import get_db
from src.server.schemas.transactions import TransactionCreateRequest, TransactionResponse
from src.server.services.transactions import create_transaction


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse)
def create_tx(
    request: Request,
    payload: TransactionCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("customer")),
) -> TransactionResponse:
    # Idempotency key derived from (user_id + client request payload).
    raw = f"{user.user_id}:{payload.amount}:{payload.recipient}"
    idempotency_key = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    tx = create_transaction(
        db,
        user_id=user.user_id,
        amount=payload.amount,
        recipient=payload.recipient,
        device_id=payload.device_id,
        idempotency_key=idempotency_key,
    )
    try:
        reasons = __import__("json").loads(tx.reason_codes or "[]")
    except Exception:
        reasons = []
    decision = "ALLOW"
    if tx.status.startswith("HOLD"):
        decision = "HOLD"
    if tx.status.startswith("BLOCK"):
        decision = "BLOCK"
    return TransactionResponse(
        tx_id=tx.tx_id,
        user_id=tx.user_id,
        amount=float(tx.amount),
        risk_score=int(tx.risk_score),
        risk_level=tx.risk_level,
        reason_codes=list(reasons),
        status=tx.status,
        decision=decision,
        explanation={
            "why": "Explainable scoring based on history + device trust",
            "reasons": reasons,
        },
    )


@router.get("/me")
def list_my_transactions(db: Session = Depends(get_db), user=Depends(require_roles("customer"))):
    from sqlalchemy import select

    from src.server.models.transaction import Transaction

    rows = db.execute(
        select(Transaction).where(Transaction.user_id == user.user_id).order_by(Transaction.created_at.desc()).limit(100)
    ).scalars().all()
    items = []
    for tx in rows:
        try:
            reasons = __import__("json").loads(tx.reason_codes or "[]")
        except Exception:
            reasons = []
        items.append(
            {
                "tx_id": tx.tx_id,
                "amount": float(tx.amount),
                "risk_score": int(tx.risk_score),
                "risk_level": tx.risk_level,
                "reason_codes": reasons,
                "status": tx.status,
                "created_at": tx.created_at.isoformat() if tx.created_at else "",
            }
        )
    return {"items": items}
