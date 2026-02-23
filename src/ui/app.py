"""Web UI for RuralShield runtime demo."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.audit.chain import verify_audit_chain
from src.auth.service import create_user
from src.database.init_db import init_db
from src.database.transaction_store import create_secure_transaction, list_secure_transactions
from src.sync.client import make_http_sender
from src.sync.manager import sync_outbox


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = Path("data/ruralshield.db")

app = FastAPI(title="RuralShield UI", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _ctx(request: Request, message: str = "", error: str = "") -> dict:
    return {
        "request": request,
        "message": message,
        "error": error,
        "db_path": str(DEFAULT_DB),
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
        msg = (
            f"Transaction created: {stored.tx_id} | "
            f"risk={stored.risk_score} ({stored.risk_level}) | "
            f"reasons={','.join(stored.reason_codes) if stored.reason_codes else 'NONE'}"
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
        context = _ctx(request)
        context["transactions"] = items
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
