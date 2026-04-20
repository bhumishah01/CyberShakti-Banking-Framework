from __future__ import annotations

import base64
import json
import zlib

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.server.api.deps import require_roles
from src.server.db.session import get_db
from src.server.schemas.sync import SyncPushRequest, SyncPushResponse, SyncItemResult
from src.server.schemas.sync_v2 import SyncV2ItemResult, SyncV2PushRequest, SyncV2PushResponse
from src.server.services.sync import push_outbox, server_time
from src.server.services.transactions import create_transaction


router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/push", response_model=SyncPushResponse)
def push(payload: SyncPushRequest, db: Session = Depends(get_db), user=Depends(require_roles("customer", "agent"))):
    results_raw = push_outbox(db, user_id=payload.user_id, items=[i.model_dump() for i in payload.items])
    results = [SyncItemResult(**r) for r in results_raw]
    return SyncPushResponse(server_time=server_time(), results=results)


def _decode_payload_b64z(payload_b64z: str) -> dict:
    raw = base64.urlsafe_b64decode(payload_b64z.encode("utf-8"))
    json_bytes = zlib.decompress(raw)
    return json.loads(json_bytes.decode("utf-8"))


@router.post("/push_v2", response_model=SyncV2PushResponse)
def push_v2(payload: SyncV2PushRequest, db: Session = Depends(get_db), user=Depends(require_roles("customer", "agent"))):
    # Sort by priority descending so critical actions sync first on low bandwidth.
    items = sorted(payload.items, key=lambda x: int(x.priority), reverse=True)
    results: list[SyncV2ItemResult] = []
    for item in items:
        try:
            decoded = _decode_payload_b64z(item.payload_b64z)
            amount = float(decoded.get("amount", 0))
            recipient = str(decoded.get("recipient", ""))
        except Exception:
            results.append(
                SyncV2ItemResult(
                    tx_id=item.tx_id,
                    idempotency_key=item.idempotency_key,
                    result="rejected",
                    server_status="REJECTED",
                    detail="invalid_payload",
                )
            )
            continue

        tx = create_transaction(
            db,
            user_id=payload.user_id,
            amount=amount,
            recipient=recipient,
            device_id=payload.device_id,
            idempotency_key=item.idempotency_key,
        )
        try:
            reasons = json.loads(tx.reason_codes or "[]")
        except Exception:
            reasons = []
        results.append(
            SyncV2ItemResult(
                tx_id=tx.tx_id,
                idempotency_key=item.idempotency_key,
                result="synced",
                server_status=tx.status,
                risk_score=int(tx.risk_score),
                risk_level=tx.risk_level,
                reasons=list(reasons),
                detail="processed_v2",
            )
        )
    return SyncV2PushResponse(server_time=server_time(), results=results)


@router.get("/logs")
def logs(db: Session = Depends(get_db), user=Depends(require_roles("bank_officer"))):
    # Bank visibility into sync history.
    from sqlalchemy import select

    from src.server.models.sync import SyncLog

    rows = db.execute(select(SyncLog).order_by(SyncLog.created_at.desc()).limit(200)).scalars().all()
    return {
        "items": [
            {
                "log_id": r.log_id,
                "user_id": r.user_id,
                "tx_id": r.tx_id,
                "idempotency_key": r.idempotency_key,
                "result": r.result,
                "detail": r.detail,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ]
    }


@router.get("/status")
def status(db: Session = Depends(get_db), user=Depends(require_roles("bank_officer"))):
    # Lightweight operational visibility for the dashboard.
    from sqlalchemy import func, select

    from src.server.models.legacy_inbox import LegacySyncInbox
    from src.server.models.sync import SyncLog, SyncQueue

    queue_pending = db.execute(select(func.count()).select_from(SyncQueue)).scalar_one()
    sync_logs = db.execute(select(func.count()).select_from(SyncLog)).scalar_one()
    legacy_inbox = db.execute(select(func.count()).select_from(LegacySyncInbox)).scalar_one()
    return {"queue_items": int(queue_pending), "sync_logs": int(sync_logs), "legacy_inbox": int(legacy_inbox)}
