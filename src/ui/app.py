"""Web UI for RuralShield runtime demo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.audit.chain import verify_audit_chain
from src.auth.service import create_user
from src.database.init_db import init_db
from src.database.transaction_store import (
    create_secure_transaction,
    get_dashboard_stats,
    list_secure_transactions,
)
from src.sync.client import make_http_sender
from src.sync.manager import sync_outbox


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = Path("data/ruralshield.db")

app = FastAPI(title="RuralShield UI", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _ctx(request: Request, message: str = "", error: str = "") -> dict:
    stats = get_dashboard_stats(db_path=DEFAULT_DB)
    return {
        "request": request,
        "message": message,
        "error": error,
        "db_path": str(DEFAULT_DB),
        "stats": stats,
    }


@app.get("/")
def index(request: Request):
    init_db(DEFAULT_DB)
    return templates.TemplateResponse("index.html", _ctx(request))


@app.post("/users")
def add_user(
    request: Request,
    user_id: str = Form(...),
    phone: str = Form(...),
    pin: str = Form(...),
    replace: str | None = Form(default=None),
):
    try:
        create_user(
            user_id=user_id.strip(),
            phone_number=phone.strip(),
            pin=pin.strip(),
            db_path=DEFAULT_DB,
            replace_existing=bool(replace),
        )
        msg = f"User {'replaced' if replace else 'created'}: {user_id.strip()}"
        return templates.TemplateResponse("index.html", _ctx(request, message=msg))
    except Exception as exc:
        return templates.TemplateResponse("index.html", _ctx(request, error=str(exc)), status_code=400)


@app.post("/transactions")
def add_transaction(
    request: Request,
    user_id: str = Form(...),
    pin: str = Form(...),
    amount: float = Form(...),
    recipient: str = Form(...),
):
    try:
        stored = create_secure_transaction(
            user_id=user_id.strip(),
            pin=pin.strip(),
            amount=amount,
            recipient=recipient.strip(),
            db_path=DEFAULT_DB,
        )
        reason_text = ", ".join(_friendly_reason(code) for code in stored.reason_codes) or "No alert triggers"
        msg = (
            "Secure transaction saved successfully. "
            f"Risk is {_friendly_risk(stored.risk_level)} ({stored.risk_score}/100). "
            f"Reason: {reason_text}. "
            "Next step: open Transaction List to review, then Sync Pending Transactions."
        )
        return templates.TemplateResponse("index.html", _ctx(request, message=msg))
    except Exception as exc:
        return templates.TemplateResponse("index.html", _ctx(request, error=str(exc)), status_code=400)


@app.get("/transactions")
def list_transactions(request: Request, user_id: str, pin: str, limit: int = 10):
    try:
        items = list_secure_transactions(
            user_id=user_id.strip(),
            pin=pin.strip(),
            db_path=DEFAULT_DB,
            limit=limit,
        )
        formatted = []
        for row in items:
            formatted.append(
                {
                    **row,
                    "display_time": _friendly_time(row["timestamp"]),
                    "display_risk": f"{_friendly_risk(row['risk_level'])} ({row['risk_score']}/100)",
                    "display_reasons": [_friendly_reason(code) for code in row.get("reason_codes", [])],
                    "display_status": _friendly_status(row["status"]),
                }
            )

        context = _ctx(request)
        context["transactions"] = formatted
        context["active_user"] = user_id.strip()
        return templates.TemplateResponse("transactions.html", context)
    except Exception as exc:
        context = _ctx(request, error=str(exc))
        context["transactions"] = []
        context["active_user"] = user_id.strip()
        return templates.TemplateResponse("transactions.html", context, status_code=400)


@app.post("/sync")
def do_sync(request: Request, server_url: str = Form("http://localhost:8000")):
    try:
        sender = make_http_sender(server_url.strip())
        summary = sync_outbox(db_path=DEFAULT_DB, sender=sender)
        msg = (
            "Sync completed: "
            f"processed={summary.processed}, synced={summary.synced}, "
            f"duplicates={summary.duplicates}, retried={summary.retried}"
        )
        return templates.TemplateResponse("index.html", _ctx(request, message=msg))
    except Exception as exc:
        return templates.TemplateResponse("index.html", _ctx(request, error=str(exc)), status_code=400)


@app.get("/audit")
def audit_status(request: Request):
    result = verify_audit_chain(db_path=DEFAULT_DB)
    if result.is_valid:
        msg = f"Audit chain valid. Entries checked: {result.checked_entries}"
        return templates.TemplateResponse("index.html", _ctx(request, message=msg))

    err = f"Audit chain invalid: {result.error}"
    return templates.TemplateResponse("index.html", _ctx(request, error=err), status_code=400)


@app.get("/reset")
def reset_to_home():
    return RedirectResponse(url="/", status_code=303)


@app.post("/seed-demo")
def seed_demo_data(request: Request):
    """Insert a realistic demo user + transactions for live presentation."""
    try:
        user_id = "demo_user"
        pin = "1234"
        create_user(
            user_id=user_id,
            phone_number="+919000000001",
            pin=pin,
            db_path=DEFAULT_DB,
            replace_existing=True,
        )

        now = datetime.now(UTC)
        samples = [
            (450.0, "Local Merchant", now - timedelta(minutes=24)),
            (1100.0, "Family Member", now - timedelta(minutes=16)),
            (3650.0, "Unknown Receiver", now - timedelta(minutes=8)),
        ]
        for amount, recipient, tx_time in samples:
            create_secure_transaction(
                user_id=user_id,
                pin=pin,
                amount=amount,
                recipient=recipient,
                db_path=DEFAULT_DB,
                timestamp=tx_time,
            )

        msg = "Demo data seeded. Use user_id=demo_user and pin=1234."
        return templates.TemplateResponse("index.html", _ctx(request, message=msg))
    except Exception as exc:
        return templates.TemplateResponse("index.html", _ctx(request, error=str(exc)), status_code=400)


@app.get("/export/report")
def export_report():
    """Export current system snapshot for faculty review."""
    stats = get_dashboard_stats(db_path=DEFAULT_DB)
    audit = verify_audit_chain(db_path=DEFAULT_DB)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "stats": stats,
        "audit": {
            "is_valid": audit.is_valid,
            "checked_entries": audit.checked_entries,
            "error": audit.error,
        },
    }
    return JSONResponse(payload)


def _friendly_risk(level: str) -> str:
    mapping = {"LOW": "Low", "MEDIUM": "Medium", "HIGH": "High"}
    return mapping.get(level, level.title())


def _friendly_status(status: str) -> str:
    mapping = {
        "PENDING": "Pending Sync",
        "SYNCED": "Synced to Server",
        "SYNCED_DUPLICATE_ACK": "Synced (Duplicate Acknowledged)",
        "RETRYING_SYNC": "Retrying Sync",
        "REJECTED_INTEGRITY_FAIL": "Blocked (Integrity Check Failed)",
    }
    return mapping.get(status, status.replace("_", " ").title())


def _friendly_reason(code: str) -> str:
    mapping = {
        "NEW_RECIPIENT": "New recipient not seen before",
        "HIGH_AMOUNT": "Unusually high amount",
        "ODD_HOUR": "Transaction at unusual hour",
        "RAPID_BURST": "Multiple rapid transactions",
        "AUTH_FAILURES": "Recent failed login attempts",
    }
    return mapping.get(code, code.replace("_", " ").title())


def _friendly_time(iso_ts: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_ts)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return iso_ts
