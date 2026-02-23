"""Rule-based fraud scoring with explainable reason codes."""

from __future__ import annotations

from datetime import datetime, timedelta


def score_transaction(
    transaction: dict,
    history: list[dict],
    recent_failed_attempts: int = 0,
) -> dict:
    """
    Compute risk score and explainable reasons.

    Returns:
        {
            "risk_score": int,
            "risk_level": "LOW" | "MEDIUM" | "HIGH",
            "reason_codes": list[str],
        }
    """
    score = 0
    reasons: list[str] = []

    amount = float(transaction["amount"])
    recipient = str(transaction["recipient"]).strip().lower()
    tx_time = _parse_time(transaction["timestamp"])

    if amount >= 3000:
        score += 35
        reasons.append("HIGH_AMOUNT")

    previous_recipients = {
        str(item.get("recipient", "")).strip().lower()
        for item in history
        if item.get("recipient")
    }
    if recipient and recipient not in previous_recipients:
        score += 20
        reasons.append("NEW_RECIPIENT")

    if tx_time.hour < 6 or tx_time.hour >= 22:
        score += 15
        reasons.append("ODD_HOUR")

    recent_cutoff = tx_time - timedelta(minutes=10)
    recent_count = 0
    for item in history:
        item_time_str = item.get("timestamp")
        if not item_time_str:
            continue
        item_time = _parse_time(item_time_str)
        if item_time >= recent_cutoff:
            recent_count += 1
    if recent_count >= 3:
        score += 20
        reasons.append("RAPID_BURST")

    if recent_failed_attempts >= 3:
        score += 20
        reasons.append("AUTH_FAILURES")

    score = min(score, 100)
    return {
        "risk_score": score,
        "risk_level": _risk_level(score),
        "reason_codes": reasons,
    }


def _risk_level(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)
