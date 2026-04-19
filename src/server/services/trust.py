from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.server.models.device import Device
from src.server.models.sync import SyncLog


@dataclass(frozen=True)
class TrustSignals:
    device_trust: str  # trusted/untrusted/unknown
    sync_success_30d: int
    sync_fail_30d: int


def _sync_counts(db: Session, *, user_id: str) -> tuple[int, int]:
    since = datetime.now(UTC) - timedelta(days=30)
    rows = db.execute(
        select(SyncLog.result).where(SyncLog.user_id == user_id, SyncLog.created_at >= since)
    ).scalars().all()
    ok = sum(1 for r in rows if r in {"synced", "duplicate"})
    bad = sum(1 for r in rows if r in {"rejected", "conflict"})
    return ok, bad


def trust_signals(db: Session, *, user_id: str, device_id: str) -> TrustSignals:
    device = db.get(Device, device_id) if device_id else None
    device_trust = "unknown"
    if device is not None and device.user_id == user_id:
        device_trust = device.trust_level or "trusted"
    ok, bad = _sync_counts(db, user_id=user_id)
    return TrustSignals(device_trust=device_trust, sync_success_30d=ok, sync_fail_30d=bad)


def trust_score(signals: TrustSignals) -> int:
    # Simple, explainable trust score 0..100.
    score = 60
    if signals.device_trust == "trusted":
        score += 20
    elif signals.device_trust == "untrusted":
        score -= 30

    score += min(15, signals.sync_success_30d // 5)
    score -= min(25, signals.sync_fail_30d * 5)
    return max(0, min(100, score))

