from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.server.api.deps import require_roles
from src.server.db.session import get_db
from src.server.schemas.auth import RegisterRequest
from src.server.schemas.transactions import TransactionCreateRequest, TransactionResponse
from src.server.services.auth import register_user
from src.server.services.transactions import create_transaction


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/onboard")
def onboard(payload: RegisterRequest, db: Session = Depends(get_db), user=Depends(require_roles("agent"))):
    if payload.role != "customer":
        raise HTTPException(status_code=400, detail="agent_can_only_onboard_customers")
    try:
        u = register_user(db, user_id=payload.user_id, phone=payload.phone, password=payload.password, role="customer")
        return {"status": "created", "user_id": u.user_id}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/assisted-transaction", response_model=TransactionResponse)
def assisted_transaction(
    payload: TransactionCreateRequest,
    customer_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("agent")),
) -> TransactionResponse:
    tx = create_transaction(
        db,
        user_id=customer_id,
        amount=payload.amount,
        recipient=payload.recipient,
        device_id=payload.device_id,
        idempotency_key=f"agent:{user.user_id}:{customer_id}:{payload.amount}:{payload.recipient}",
    )
    reasons = []
    try:
        reasons = __import__("json").loads(tx.reason_codes or "[]")
    except Exception:
        reasons = []
    return TransactionResponse(
        tx_id=tx.tx_id,
        user_id=tx.user_id,
        amount=float(tx.amount),
        risk_score=int(tx.risk_score),
        risk_level=tx.risk_level,
        reason_codes=list(reasons),
        status=tx.status,
    )

