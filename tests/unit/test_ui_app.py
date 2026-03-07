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
    assert "Secure transaction saved successfully" in r2.text

    r3 = client.get("/transactions", params={"user_id": "ui-user", "pin": "1234", "limit": 5})
    assert r3.status_code == 200
    assert "Village Shop" in r3.text
    assert "Pending Sync" in r3.text


def test_ui_seed_and_export_report() -> None:
    seed = client.post("/seed-demo")
    assert seed.status_code == 200
    assert "Demo data seeded" in seed.text

    report = client.get("/export/report")
    assert report.status_code == 200
    payload = report.json()
    assert "generated_at" in payload
    assert "stats" in payload
    assert "audit" in payload
    assert payload["stats"]["tx_count"] >= 1


def test_ui_release_held_transaction_endpoint_exists() -> None:
    response = client.post(
        "/transactions/release",
        data={"tx_id": "missing", "user_id": "missing", "pin": "1234"},
    )
    assert response.status_code in {200, 400}
    assert "Release" in response.text or "failed" in response.text.lower()


def test_ui_trusted_contact_and_panic_freeze_endpoints() -> None:
    user = {
        "user_id": "safety-user",
        "phone": "+919123409999",
        "pin": "1234",
        "replace": "1",
    }
    _ = client.post("/users", data=user)

    r1 = client.post(
        "/users/trusted-contact",
        data={"user_id": "safety-user", "pin": "1234", "trusted_contact": "+919888777666"},
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/users/panic-freeze",
        data={"user_id": "safety-user", "pin": "1234", "minutes": "30"},
    )
    assert r2.status_code == 200


def test_ui_scenario_simulator_endpoint() -> None:
    response = client.post(
        "/simulate/scenario",
        data={
            "scenario_id": "account_takeover",
            "user_id": "sim-user",
            "pin": "1234",
            "lang": "en",
        },
    )
    assert response.status_code == 200
    assert "Scenario executed" in response.text


def test_ui_agent_mode_pages() -> None:
    page = client.get("/agent")
    assert page.status_code == 200

    action = client.post(
        "/agent/assist",
        data={
            "user_id": "agent-user",
            "phone": "+919111111111",
            "pin": "1234",
            "amount": "2100",
            "recipient": "Village Store",
            "lang": "en",
        },
    )
    assert action.status_code == 200
    assert "Assisted Transaction Result" in action.text


def test_ui_impact_report_page() -> None:
    _ = client.post(
        "/simulate/scenario",
        data={
            "scenario_id": "scam_high_amount",
            "user_id": "impact-user",
            "pin": "1234",
            "lang": "en",
        },
    )
    response = client.get("/report/impact")
    assert response.status_code == 200
    assert "Fraud Impact Report" in response.text


def test_ui_professor_demo_walkthrough_page() -> None:
    response = client.get("/demo/walkthrough")
    assert response.status_code == 200
    assert "Professor Demo Walkthrough" in response.text
