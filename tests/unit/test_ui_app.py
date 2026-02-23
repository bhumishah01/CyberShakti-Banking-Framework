import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from src.ui.app import app


client = TestClient(app)


def test_ui_home_loads() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "RuralShield" in response.text


def test_ui_user_create_and_tx_list_flow() -> None:
    user = {
        "user_id": "ui-user",
        "phone": "+919123450000",
        "pin": "1234",
        "replace": "1",
    }
    r1 = client.post("/users", data=user)
    assert r1.status_code == 200

    r2 = client.post(
        "/transactions",
        data={
            "user_id": "ui-user",
            "pin": "1234",
            "amount": "2500",
            "recipient": "Village Shop",
        },
    )
    assert r2.status_code == 200
    assert "Transaction created" in r2.text

    r3 = client.get("/transactions", params={"user_id": "ui-user", "pin": "1234", "limit": 5})
    assert r3.status_code == 200
    assert "Village Shop" in r3.text
