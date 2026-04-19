from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.server.models.fraud_log import FraudLog
from src.server.models.transaction import Transaction


def behavioral_profile(db: Session, *, user_id: str) -> dict:
    # Simple behavioral profiling from server-side history.
    # (avg amount, tx count last 24h, typical hour)
    day_ago = datetime.now(UTC) - timedelta(hours=24)
    q = select(
        func.count(Transaction.tx_id),
        func.coalesce(func.avg(Transaction.amount), 0),
        func.coalesce(func.max(Transaction.amount), 0),
    ).where(Transaction.user_id == user_id, Transaction.created_at >= day_ago)
    count_24h, avg_amount, max_amount = db.execute(q).one()
    return {
        "count_24h": int(count_24h or 0),
        "avg_amount": float(avg_amount or 0),
        "max_amount": float(max_amount or 0),
    }


def dynamic_risk_score(
    *,
    amount: float,
    recipient_is_new: bool,
    profile: dict,
    new_device: bool,
    trust_score: int = 60,
) -> tuple[int, str, list[str], dict]:
    score = 0
    reasons: list[str] = []
    explanation: dict = {"signals": {}, "rules": [], "final": {}}

    avg_amount = float(profile.get("avg_amount", 0) or 0)
    explanation["signals"] = {
        "avg_amount": avg_amount,
        "count_24h": int(profile.get("count_24h", 0) or 0),
        "trust_score": int(trust_score),
    }
    if recipient_is_new:
        score += 20
        reasons.append("NEW_RECIPIENT")
        explanation["rules"].append({"rule": "NEW_RECIPIENT", "points": 20})

    # If amount is much higher than baseline, add points.
    if avg_amount > 0 and amount > (avg_amount * 2.5):
        score += 30
        reasons.append("HIGH_AMOUNT")
        explanation["rules"].append({"rule": "HIGH_AMOUNT_VS_BASELINE", "points": 30})
    elif amount > 5000:
        score += 20
        reasons.append("HIGH_AMOUNT")
        explanation["rules"].append({"rule": "HIGH_AMOUNT_ABSOLUTE", "points": 20})

    if int(profile.get("count_24h", 0)) >= 8:
        score += 15
        reasons.append("RAPID_BURST")
        explanation["rules"].append({"rule": "RAPID_BURST_24H", "points": 15})

    if new_device:
        score += 35
        reasons.append("NEW_DEVICE")
        explanation["rules"].append({"rule": "NEW_DEVICE", "points": 35})

    # Trust score reduces risk a bit (but never fully cancels a red flag).
    if trust_score >= 85:
        score -= 10
        explanation["rules"].append({"rule": "HIGH_TRUST_DISCOUNT", "points": -10})
    elif trust_score <= 35:
        score += 10
        explanation["rules"].append({"rule": "LOW_TRUST_PENALTY", "points": 10})

    score = max(0, min(100, score))
    level = "LOW"
    if score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    explanation["final"] = {"risk_score": score, "risk_level": level, "reasons": reasons}
    return score, level, reasons, explanation


def log_fraud(db: Session, *, log_id: str, tx_id: str, user_id: str, risk_score: int, risk_level: str, reasons: list[str]) -> None:
    db.add(
        FraudLog(
            log_id=log_id,
            tx_id=tx_id,
            user_id=user_id,
            risk_score=risk_score,
            risk_level=risk_level,
            reasons_json=json.dumps(reasons),
        )
    )
    db.commit()
