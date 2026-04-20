"""Rule-based fraud scoring with explainable reason codes."""

from __future__ import annotations

from datetime import datetime, timedelta


def score_transaction(
    transaction: dict,
    history: list[dict],
    recent_failed_attempts: int = 0,
    *,
    profile: dict | None = None,
    rapid_count_2m: int = 0,
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

    # Rule 1: absolute high amount (simple baseline rule)
    if amount >= 3000:
        score += 35
        reasons.append("HIGH_AMOUNT")

    # Adaptive rule: compare to user's own baseline (behavior profiling)
    try:
        avg_amount = float((profile or {}).get("avg_amount", 0.0) or 0.0)
        tx_count = int((profile or {}).get("tx_count", 0) or 0)
    except Exception:
        avg_amount, tx_count = 0.0, 0
    if tx_count >= 3 and avg_amount > 0 and amount >= (avg_amount * 2.5):
        score += 25
        reasons.append("HIGH_AMOUNT_VS_AVG")

    previous_recipients = {
        str(item.get("recipient", "")).strip().lower()
        for item in history
        if item.get("recipient")
    }
    if recipient and recipient not in previous_recipients:
        score += 20
        reasons.append("NEW_RECIPIENT")

    # Rule: odd hour baseline
    if tx_time.hour < 6 or tx_time.hour >= 22:
        score += 15
        reasons.append("ODD_HOUR")

    # Adaptive rule: unusual time vs preferred hours
    try:
        preferred_hours = (profile or {}).get("preferred_hours", []) or []
        preferred_hours = [int(x) for x in preferred_hours if isinstance(x, (int, str))]
    except Exception:
        preferred_hours = []
    if tx_count >= 5 and preferred_hours and (tx_time.hour not in set(preferred_hours)):
        score += 10
        reasons.append("UNUSUAL_TIME")

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

    # Suspicious pattern: 5+ transactions within 2 minutes
    if int(rapid_count_2m or 0) >= 5:
        score += 25
        reasons.append("FIVE_IN_2_MIN")

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
