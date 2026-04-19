from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.server.api.deps import require_roles
from src.server.db.session import get_db
from src.server.models.fraud_log import FraudLog


router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.get("/logs")
def list_logs(db: Session = Depends(get_db), user=Depends(require_roles("bank_officer"))):
    rows = db.execute(select(FraudLog).order_by(FraudLog.created_at.desc()).limit(200)).scalars().all()
    items = []
    for row in rows:
        try:
            reasons = json.loads(row.reasons_json or "[]")
        except Exception:
            reasons = []
        items.append(
            {
                "log_id": row.log_id,
                "tx_id": row.tx_id,
                "user_id": row.user_id,
                "risk_score": row.risk_score,
                "risk_level": row.risk_level,
                "reasons": reasons,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
        )
    return {"items": items}

