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


def decide_intervention(risk_score: int, risk_level: str, reason_codes: list[str]) -> dict:
    """
    Convert risk output into an operational safety action.

    Actions:
    - ALLOW: normal flow
    - STEP_UP: proceed after additional user caution/verification
    - HOLD: store and require manual release before sync
    - BLOCK: locally block transaction to prevent immediate loss
    """
    reasons = set(reason_codes)

    if "AUTH_FAILURES" in reasons and risk_score >= 70:
        return {
            "action": "BLOCK",
            "title": "Blocked for your protection",
            "guidance": [
                "Recent failed login attempts were detected.",
                "Do not proceed until you verify account ownership.",
                "Contact bank support or trusted agent.",
            ],
        }

    if {"HIGH_AMOUNT", "NEW_RECIPIENT"}.issubset(reasons):
        return {
            "action": "HOLD",
            "title": "Transaction held for safety review",
            "guidance": [
                "Large transfer to a first-time recipient is risky.",
                "Verify recipient identity by phone or in person.",
                "Use 'Release Held Transaction' only after verification.",
            ],
        }

    if risk_level == "HIGH":
        return {
            "action": "HOLD",
            "title": "High-risk transaction held",
            "guidance": [
                "Risk is high for this transaction pattern.",
                "Wait 30 minutes and re-check request authenticity.",
                "Proceed only after trusted confirmation.",
            ],
        }

    if risk_level == "MEDIUM":
        return {
            "action": "STEP_UP",
            "title": "Additional verification recommended",
            "guidance": [
                "This transaction needs extra caution.",
                "Re-confirm recipient and amount carefully.",
                "Proceed only if this request is expected.",
            ],
        }

    return {
        "action": "ALLOW",
        "title": "Transaction safe to proceed",
        "guidance": [
            "No major scam pattern detected.",
            "Transaction will stay queued until synced.",
        ],
    }


def _risk_level(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)
