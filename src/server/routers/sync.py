from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.server.api.deps import require_roles
from src.server.db.session import get_db
from src.server.schemas.sync import SyncPushRequest, SyncPushResponse, SyncItemResult
from src.server.services.sync import push_outbox, server_time


router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/push", response_model=SyncPushResponse)
def push(payload: SyncPushRequest, db: Session = Depends(get_db), user=Depends(require_roles("customer", "agent"))):
    results_raw = push_outbox(db, user_id=payload.user_id, items=[i.model_dump() for i in payload.items])
    results = [SyncItemResult(**r) for r in results_raw]
    return SyncPushResponse(server_time=server_time(), results=results)

