from src.sync.client import fetch_rules, make_http_sender


class _DummyResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_make_http_sender_posts_payload(monkeypatch) -> None:
    captured = {}

    def fake_post(url, json, timeout):  # noqa: ANN001
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _DummyResponse({"status": "synced"})

    monkeypatch.setattr("requests.post", fake_post)

    sender = make_http_sender("http://localhost:8000", timeout=2.5)
    result = sender({"tx_id": "1", "idempotency_key": "abc", "payload_enc": "x"})

    assert result["status"] == "synced"
    assert captured["url"] == "http://localhost:8000/sync/transactions"
    assert captured["timeout"] == 2.5


def test_fetch_rules_returns_rules(monkeypatch) -> None:
    def fake_get(url, timeout):  # noqa: ANN001
        assert url == "http://localhost:8000/rules"
        assert timeout == 3.0
        return _DummyResponse(
            {
                "rules": [
                    {
                        "rule_id": "r1",
                        "rule_version": "1.0",
                        "rule_data": {"threshold": 10},
                        "updated_at": "2026-02-23T10:00:00+00:00",
                    }
                ]
            }
        )

    monkeypatch.setattr("requests.get", fake_get)

    rules = fetch_rules("http://localhost:8000", timeout=3.0)
    assert len(rules) == 1
    assert rules[0]["rule_id"] == "r1"
