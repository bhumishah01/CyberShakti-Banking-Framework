"""HTTP sender adapter for sync manager."""

from __future__ import annotations

from typing import Callable

import requests


def make_http_sender(base_url: str, timeout: float = 10.0) -> Callable[[dict], dict]:
    """Build sender callback compatible with `sync_outbox`."""
    normalized = base_url.rstrip("/")

    def sender(packet: dict) -> dict:
        response = requests.post(
            f"{normalized}/sync/transactions",
            json=packet,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    return sender


def fetch_rules(base_url: str, timeout: float = 10.0) -> list[dict]:
    """Fetch latest fraud rules from backend."""
    normalized = base_url.rstrip("/")
    response = requests.get(f"{normalized}/rules", timeout=timeout)
    response.raise_for_status()
    body = response.json()
    return body.get("rules", [])
