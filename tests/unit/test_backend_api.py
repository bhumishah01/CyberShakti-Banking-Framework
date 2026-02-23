import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from src.backend.app import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_sync_endpoint_returns_duplicate_for_same_idempotency_key() -> None:
    payload = {
        "tx_id": "tx-1",
        "idempotency_key": "idem-1",
        "payload_enc": "encrypted-payload",
    }

    first = client.post("/sync/transactions", json=payload)
    second = client.post("/sync/transactions", json=payload)

    assert first.status_code == 200
    assert first.json()["status"] == "synced"

    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"


def test_rule_update_and_list() -> None:
    update = {
        "rules": [
            {
                "rule_id": "night-risk",
                "rule_version": "1.0.0",
                "rule_data": {"start_hour": 22, "end_hour": 6, "score": 15},
                "updated_at": "2026-02-23T10:00:00+00:00",
            }
        ]
    }

    post_response = client.post("/rules", json=update)
    assert post_response.status_code == 200

    get_response = client.get("/rules")
    assert get_response.status_code == 200
    rules = get_response.json()["rules"]
    ids = {rule["rule_id"] for rule in rules}
    assert "night-risk" in ids
