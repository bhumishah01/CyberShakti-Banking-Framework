from datetime import datetime

from src.fraud.engine import score_transaction


def test_score_transaction_new_recipient_only() -> None:
    tx = {
        "amount": 500,
        "recipient": "New Person",
        "timestamp": "2026-02-23T13:00:00+00:00",
    }
    history = [
        {
            "amount": "400.00",
            "recipient": "Known Person",
            "timestamp": "2026-02-23T12:45:00+00:00",
        }
    ]

    risk = score_transaction(tx, history, recent_failed_attempts=0)
    assert risk["risk_score"] == 20
    assert risk["risk_level"] == "LOW"
    assert risk["reason_codes"] == ["NEW_RECIPIENT"]


def test_score_transaction_high_risk_combination() -> None:
    tx_time = datetime.fromisoformat("2026-02-23T23:30:00+00:00")
    tx = {
        "amount": 4500,
        "recipient": "Unknown Receiver",
        "timestamp": tx_time.isoformat(),
    }
    history = [
        {"amount": "100.00", "recipient": "Alice", "timestamp": "2026-02-23T23:28:00+00:00"},
        {"amount": "120.00", "recipient": "Bob", "timestamp": "2026-02-23T23:26:00+00:00"},
        {"amount": "90.00", "recipient": "Charlie", "timestamp": "2026-02-23T23:25:00+00:00"},
    ]

    risk = score_transaction(tx, history, recent_failed_attempts=3)
    assert risk["risk_score"] == 100
    assert risk["risk_level"] == "HIGH"
    assert set(risk["reason_codes"]) == {
        "HIGH_AMOUNT",
        "NEW_RECIPIENT",
        "ODD_HOUR",
        "RAPID_BURST",
        "AUTH_FAILURES",
    }
