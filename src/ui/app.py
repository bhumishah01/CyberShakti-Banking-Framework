"""Web UI for RuralShield runtime demo.

This file wires the HTML pages to the core security logic:
- routes (URLs)
- form inputs
- local database reads
- response messages for the demo
"""

from __future__ import annotations

import base64
import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
import csv
import os
from pathlib import Path
from typing import Any

import logging
import traceback

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.audit.chain import verify_audit_chain
from src.auth.service import (
    authenticate_user,
    create_user,
    enable_panic_freeze,
    enroll_or_verify_device_id,
    enroll_or_verify_face_hash,
    get_user_auth_config,
    set_trusted_contact,
)
from src.auth.biometric import compute_dhash64_from_png
from src.database.init_db import DB_PATH, init_db
from src.database.transaction_store import (
    create_secure_transaction,
    get_dashboard_stats,
    list_secure_transactions,
    read_secure_transaction,
    release_held_transaction,
)
from src.database.monitoring_store import list_notifications
from src.database.profile_store import get_or_create_profile, preferred_hours
from src.database.device_store import list_devices
from src.database.monitoring_store import list_recent_alerts
from src.sync.client import make_http_sender
from src.sync.manager import sync_outbox


# === App configuration ===
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = DB_PATH  # absolute, stable path (prevents “user not found” due to different cwd)
DEFAULT_SERVER_URL = os.environ.get("RURALSHIELD_SERVER_URL", "http://localhost:8000")
SUPPORTED_LANGS = {"en", "hi", "or", "gu", "de"}
DEFAULT_BANK_USERNAME = "bank_admin"
DEFAULT_BANK_PASSWORD = "admin123"
ROLE_COOKIE = "ruralshield_role"
USER_COOKIE = "ruralshield_user"
FACE_COOKIE = "ruralshield_face_verified"
DEVICE_COOKIE = "ruralshield_device_trust"
JWT_COOKIE = "ruralshield_jwt"
LANG_COOKIE = "ruralshield_lang"
FLASH_MSG_COOKIE = "ruralshield_flash_msg"
FLASH_ERR_COOKIE = "ruralshield_flash_err"
FLASH_VOICE_COOKIE = "ruralshield_flash_voice"
FACE_CAPTURE_DIR = DB_PATH.parent / "face_captures"
BUILD_ID = os.environ.get("RURALSHIELD_BUILD_ID", "after_midsem-local")

# FastAPI app + static assets + HTML templates
app = FastAPI(title="RuralShield UI", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
# Workaround for a cache-key issue that can surface with newer Starlette/Jinja2 combos
# where an unhashable dict ends up in the template cache key.
# Disabling cache is fine for this project/demo and avoids 500s on template load.
templates.env.cache = None

logger = logging.getLogger("ruralshield.ui")


@app.exception_handler(Exception)
async def _unhandled_exception(request: Request, exc: Exception):
    # Never show a blank/black 500 screen during demo; render a friendly page and log details.
    # Also write a local file so a student can show exact errors without digging in terminal.
    try:
        log_path = DB_PATH.parent / "ui_errors.log"
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"time_utc={datetime.now(UTC).isoformat()}\n")
            f.write(f"path={request.url.path} method={request.method}\n")
            f.write(f"user={request.cookies.get(USER_COOKIE, '')} role={request.cookies.get(ROLE_COOKIE, '')}\n")
            f.write(f"error={type(exc).__name__}: {exc}\n")
            f.write(traceback.format_exc() + "\n")
    except Exception:
        pass
    try:
        logger.exception("UI error path=%s method=%s user=%s", request.url.path, request.method, request.cookies.get(USER_COOKIE, ""))
    except Exception:
        pass
    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept or "*/*" in accept or accept == "":
        lang = _lang_from_request(request)
        return render_template(
            request,
            "error.html",
            {
                "lang": lang,
                "i18n": _bundle(lang),
                "langs": _language_choices(),
                "error": str(exc),
                "path": request.url.path,
                "build_id": BUILD_ID,
            },
            status_code=500,
        )
    return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


def render_template(
    request: Request,
    name: str,
    context: dict,
    *,
    status_code: int = 200,
):
    """Render a Jinja template safely across Starlette templating API versions.

    Starlette has had two common calling conventions:
    1. TemplateResponse(request, name, context, ...)
    2. TemplateResponse(name, context, ...) where context must include {"request": request}

    We support both to prevent "Internal Server Error" screens caused by a signature mismatch.
    """

    # Ensure request is always available to the template.
    ctx = dict(context or {})
    ctx.setdefault("request", request)

    try:
        resp = templates.TemplateResponse(request, name, ctx, status_code=status_code)
    except TypeError:
        resp = templates.TemplateResponse(name, ctx, status_code=status_code)

    # Demo UX: prevent caching so pages always reflect latest DB state after POST+redirect.
    try:
        resp.headers["Cache-Control"] = "no-store"
    except Exception:
        pass

    # Persist language choice (used when query param is missing).
    lang = str(ctx.get("lang") or "").strip()
    if lang:
        try:
            resp.set_cookie(LANG_COOKIE, lang, max_age=60 * 60 * 24 * 30, samesite="lax")
        except Exception:
            pass
    return resp


def _json_ok(data: Any | None = None, message: str = "ok") -> JSONResponse:
    payload: dict[str, Any] = {"status": "success", "message": message, "data": data or {}}
    return JSONResponse(payload, status_code=200)


def _json_err(message: str, *, status_code: int = 400, data: Any | None = None) -> JSONResponse:
    payload: dict[str, Any] = {"status": "error", "message": message, "data": data or {}}
    return JSONResponse(payload, status_code=int(status_code))


def _server_api_url() -> str:
    return DEFAULT_SERVER_URL.rstrip("/")


def _jwt_from_request(request: Request) -> str:
    return request.cookies.get(JWT_COOKIE, "")

def _tf(lang: str, key: str, **kwargs) -> str:
    # Translate + safe format (for templates we prefer pre-formatted strings).
    try:
        return str(_t(lang, key)).format(**kwargs)
    except Exception:
        return str(_t(lang, key))


def _flash_redirect(url: str, *, message: str = "", error: str = "", voice_text: str = "") -> RedirectResponse:
    # Very small "flash" system via short-lived cookies.
    resp = RedirectResponse(url=url, status_code=303)
    if message:
        resp.set_cookie(FLASH_MSG_COOKIE, message, max_age=15, samesite="lax")
    if error:
        resp.set_cookie(FLASH_ERR_COOKIE, error, max_age=15, samesite="lax")
    if voice_text:
        resp.set_cookie(FLASH_VOICE_COOKIE, voice_text, max_age=15, samesite="lax")
    return resp


def _customer_redirect(lang: str, *, message: str = "", error: str = "", voice_text: str = "") -> RedirectResponse:
    return _flash_redirect(f"/dashboard/customer?lang={lang}", message=message, error=error, voice_text=voice_text)


def _lang_from_request(request: Request, fallback: str = "en") -> str:
    raw = request.query_params.get("lang") or request.cookies.get(LANG_COOKIE) or fallback
    return _resolve_lang(str(raw))


def _read_and_clear_flash(request: Request, context: dict) -> dict:
    # Populate context with flash values. Caller must delete cookies on the Response.
    msg = request.cookies.get(FLASH_MSG_COOKIE, "")
    err = request.cookies.get(FLASH_ERR_COOKIE, "")
    v = request.cookies.get(FLASH_VOICE_COOKIE, "")
    if msg and not context.get("message"):
        context["message"] = msg
    if err and not context.get("error"):
        context["error"] = err
    if v and not context.get("voice_text"):
        context["voice_text"] = v
    return context


def _api_call(
    method: str,
    path: str,
    *,
    token: str = "",
    json_body: dict | None = None,
    timeout: float = 6.0,
) -> dict:
    """Server-side call from UI -> Server API. Uses JWT in Authorization header."""
    import requests

    url = f"{_server_api_url()}{path}"
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.request(method, url, json=json_body, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, dict) else {"data": data}


def _ensure_server_session_for_customer(user_id: str, pin: str, device_id: str) -> tuple[str, str]:
    """Return (jwt, role) for server dashboards.

    Demo choice: use the customer's PIN as the server password so the same login works.
    """
    try:
        out = _api_call(
            "POST",
            "/auth/login",
            json_body={"user_id": user_id, "password": pin, "device_id": device_id},
        )
        return str(out.get("access_token", "")), str(out.get("role", "customer"))
    except Exception:
        _api_call(
            "POST",
            "/auth/register",
            json_body={"user_id": user_id, "phone": "+910000000000", "password": pin, "role": "customer"},
        )
        out = _api_call(
            "POST",
            "/auth/login",
            json_body={"user_id": user_id, "password": pin, "device_id": device_id},
        )
        return str(out.get("access_token", "")), str(out.get("role", "customer"))


def _ensure_server_session_for_bank() -> tuple[str, str]:
    """Return (jwt, role) for bank dashboards.

    Demo choice: auto-provision a bank_officer with the UI admin credentials.
    """
    user_id = DEFAULT_BANK_USERNAME
    password = DEFAULT_BANK_PASSWORD
    try:
        out = _api_call(
            "POST",
            "/auth/login",
            json_body={"user_id": user_id, "password": password, "device_id": ""},
        )
        return str(out.get("access_token", "")), str(out.get("role", "bank_officer"))
    except Exception:
        _api_call(
            "POST",
            "/auth/register",
            json_body={"user_id": user_id, "phone": "+910000000001", "password": password, "role": "bank_officer"},
        )
        out = _api_call(
            "POST",
            "/auth/login",
            json_body={"user_id": user_id, "password": password, "device_id": ""},
        )
        return str(out.get("access_token", "")), str(out.get("role", "bank_officer"))


def _server_dashboard_customer_data(token: str) -> dict[str, Any]:
    tx = _api_call("GET", "/transactions/me", token=token)
    items = list(tx.get("items", [])) if isinstance(tx, dict) else []

    spent = 0.0
    for it in items:
        try:
            spent += float(it.get("amount", 0) or 0)
        except Exception:
            pass

    balance = max(0.0, 50000.0 - spent)  # mock balance for demo
    return {"balance": balance, "transactions": items}


def _server_dashboard_bank_data(token: str, status: str = "") -> dict[str, Any]:
    q = f"?status={status}" if status else ""
    tx = _api_call("GET", f"/transactions{q}", token=token)
    fraud = _api_call("GET", "/fraud/logs", token=token)
    sync_status = _api_call("GET", "/sync/status", token=token)
    return {
        "transactions": list(tx.get("items", [])) if isinstance(tx, dict) else [],
        "fraud_logs": list(fraud.get("items", [])) if isinstance(fraud, dict) else [],
        "sync_status": sync_status if isinstance(sync_status, dict) else {},
    }


def _ctx(
    request: Request,
    message: str = "",
    error: str = "",
    lang: str = "en",
    voice_text: str = "",
) -> dict:
    # Common context shared by dashboard pages.
    # NOTE: login pages should avoid this (it hits SQLite and can feel slow).
    stats = get_dashboard_stats(db_path=DEFAULT_DB)
    i18n = _bundle(lang)
    recent_changes = _load_recent_change_log()
    return {
        "request": request,
        "message": message,
        "error": error,
        "db_path": str(DEFAULT_DB),
        "stats": stats,
        "recent_changes": recent_changes,
        "lang": lang,
        "i18n": i18n,
        "langs": _language_choices(),
        "scenarios": _scenario_choices(lang),
        "voice_text": voice_text,
    }


def _login_ctx(
    request: Request,
    message: str = "",
    error: str = "",
    lang: str = "en",
) -> dict:
    # Minimal context for login/entry pages (fast, no DB reads).
    i18n = _bundle(lang)
    return {
        "request": request,
        "message": message,
        "error": error,
        "lang": lang,
        "i18n": i18n,
        "langs": _language_choices(),
    }


def _login_context(request: Request, lang: str, mode: str, message: str = "", error: str = "") -> dict:
    context = _login_ctx(request, message=message, error=error, lang=lang)
    context["login_mode"] = mode
    return context


def _user_ctx(request: Request) -> dict:
    # Session-like data is kept in cookies to keep the demo simple.
    # Back-compat: older cookies used role=admin, but we now present it as bank portal.
    role = request.cookies.get(ROLE_COOKIE, "")
    if role == "admin":
        role = "bank"
    return {
        "role": role,
        "active_user": request.cookies.get(USER_COOKIE, ""),
        "face_verified": request.cookies.get(FACE_COOKIE, "") == "1",
        "device_trust": request.cookies.get(DEVICE_COOKIE, "trusted"),
    }


def _require_role(request: Request, expected_role: str) -> RedirectResponse | None:
    if _user_ctx(request).get("role") != expected_role:
        return RedirectResponse(url="/", status_code=303)
    return None


def _customer_stats(user_id: str) -> dict:
    init_db(DEFAULT_DB)
    stats = {"total": 0, "pending": 0, "held": 0, "blocked": 0, "synced": 0}
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,))
        stats["total"] = int(cursor.fetchone()[0])
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ? AND status = 'PENDING'",
            (user_id,),
        )
        stats["pending"] = int(cursor.fetchone()[0])
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ? AND status IN ('HOLD_FOR_REVIEW','AWAITING_TRUSTED_APPROVAL')",
            (user_id,),
        )
        stats["held"] = int(cursor.fetchone()[0])
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ? AND (status LIKE 'BLOCKED_%' OR status = 'BLOCKED_LOCAL')",
            (user_id,),
        )
        stats["blocked"] = int(cursor.fetchone()[0])
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ? AND status = 'SYNCED'",
            (user_id,),
        )
        stats["synced"] = int(cursor.fetchone()[0])
    return stats


def _recent_tx_meta(user_id: str, limit: int = 5) -> list[dict]:
    # Mini statement without decrypting amounts/recipients (privacy-first).
    init_db(DEFAULT_DB)
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT tx_id, timestamp, risk_score, risk_level, status, reason_codes
            FROM transactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cursor.fetchall()
    items = []
    for tx_id, ts, risk_score, risk_level, status, reason_codes in rows:
        items.append(
            {
                "tx_id": tx_id,
                "timestamp": _friendly_time(ts),
                "risk_score": int(risk_score),
                "risk_level": str(risk_level),
                "status": str(status),
                "reason_codes": _safe_parse_reason_codes(reason_codes),
            }
        )
    return items


def _last_sync_time() -> str:
    init_db(DEFAULT_DB)
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT created_at FROM audit_log WHERE event_type = 'SYNC_RESULT' ORDER BY created_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
    if not row:
        return "-"
    return _friendly_time(row[0])


def _customer_dashboard_context(
    request: Request,
    lang: str,
    message: str = "",
    error: str = "",
    voice_text: str = "",
) -> dict:
    context = _ctx(request, message=message, error=error, lang=lang, voice_text=voice_text)
    session = _user_ctx(request)
    context.update(session)
    context["customer_stats"] = _customer_stats(session["active_user"]) if session["active_user"] else {
        "total": 0,
        "pending": 0,
        "held": 0,
        "blocked": 0,
        "synced": 0,
    }
    if session.get("active_user"):
        # Behavior profile (for explainability)
        try:
            prof = get_or_create_profile(session["active_user"], db_path=DEFAULT_DB)
            context["profile"] = {
                "avg_amount": prof.avg_amount,
                "tx_count": prof.tx_count,
                "user_risk_score": prof.user_risk_score,
                "preferred_hours": preferred_hours(prof, top_n=3),
            }
        except Exception:
            context["profile"] = {"avg_amount": 0.0, "tx_count": 0, "user_risk_score": 0, "preferred_hours": []}
        context["mini_statement"] = _recent_tx_meta(session["active_user"], limit=5)
        context["last_sync_at"] = _last_sync_time()
        # Safety settings (trusted contact + freeze) shown in customer UI.
        try:
            auth_cfg = get_user_auth_config(user_id=session["active_user"], db_path=DEFAULT_DB)
        except Exception:
            auth_cfg = {"trusted_contact": "", "freeze_until": ""}
        context["trusted_contact_current"] = str(auth_cfg.get("trusted_contact", "") or "").strip()
        context["freeze_until"] = str(auth_cfg.get("freeze_until", "") or "").strip() or "-"
        # Notifications panel (customer)
        try:
            context["notifications"] = list_notifications(role="customer", user_id=session["active_user"], db_path=DEFAULT_DB, limit=10)
        except Exception:
            context["notifications"] = []
        # Simple user risk indicator for low-literacy UX.
        stats = context["customer_stats"]
        device_untrusted = context.get("device_trust") == "untrusted"
        if device_untrusted or int(stats.get("held", 0)) > 0 or int(stats.get("blocked", 0)) > 0:
            context["user_risk_badge"] = "warning"
        else:
            context["user_risk_badge"] = "safe"
    else:
        context["mini_statement"] = []
        context["last_sync_at"] = "-"
        context["user_risk_badge"] = "safe"
        context["trusted_contact_current"] = ""
        context["freeze_until"] = "-"
        context["notifications"] = []
        context["profile"] = {"avg_amount": 0.0, "tx_count": 0, "user_risk_score": 0, "preferred_hours": []}
    return context


def _admin_dashboard_context(
    request: Request,
    lang: str,
    message: str = "",
    error: str = "",
    voice_text: str = "",
) -> dict:
    context = _ctx(request, message=message, error=error, lang=lang, voice_text=voice_text)
    context.update(_user_ctx(request))
    context["portal_title"] = _bundle(lang).get("admin_portal_title", "Bank/Admin Security Portal")
    context["portal_subtitle"] = _bundle(lang).get("admin_portal_subtitle", "Central controls for fraud review, sync, and audit")
    return context


def _local_admin_overview(db_path: Path = DEFAULT_DB) -> dict:
    # Lightweight overview for admin portal (local SQLite).
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM transactions")
        tx_count = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'PENDING'")
        pending = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE status IN ('HOLD_FOR_REVIEW','AWAITING_TRUSTED_APPROVAL')")
        held = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE (status LIKE 'BLOCKED_%' OR status = 'BLOCKED_LOCAL')")
        blocked = int(cursor.fetchone()[0])
        allowed = max(0, tx_count - held - blocked)
    return {
        "user_count": user_count,
        "tx_count": tx_count,
        "allowed": allowed,
        "held": held,
        "blocked": blocked,
        "pending_sync": pending,
    }


def _fraud_trends(db_path: Path = DEFAULT_DB, days: int = 7) -> list[dict]:
    # Simple "chart-ready" grouped data.
    init_db(db_path)
    days = max(1, int(days))
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT substr(created_at, 1, 10) AS day, COUNT(*)
            FROM alerts
            GROUP BY day
            ORDER BY day DESC
            LIMIT {days}
            """
        )
        alert_rows = cursor.fetchall()
        cursor.execute(
            f"""
            SELECT substr(created_at, 1, 10) AS day, alert_type, COUNT(*)
            FROM alerts
            GROUP BY day, alert_type
            ORDER BY day DESC
            LIMIT {days * 20}
            """
        )
        type_rows = cursor.fetchall()
        cursor.execute(
            f"""
            SELECT substr(timestamp, 1, 10) AS day, COUNT(*)
            FROM transactions
            WHERE risk_score >= 70 OR risk_level = 'HIGH'
            GROUP BY day
            ORDER BY day DESC
            LIMIT {days}
            """
        )
        risk_rows = cursor.fetchall()
    alert_map = {d: int(c) for d, c in alert_rows}
    risk_map = {d: int(c) for d, c in risk_rows}
    type_map: dict[str, dict[str, int]] = {}
    for d, alert_type, c in type_rows:
        if not d:
            continue
        type_map.setdefault(d, {})
        type_map[d][str(alert_type)] = int(c)
    all_days = sorted(set(alert_map.keys()) | set(risk_map.keys()), reverse=True)[:days]
    out = []
    for d in all_days:
        types = type_map.get(d, {})
        # Build a short "type breakdown" string: TYPE:count, TYPE:count
        top_types = sorted(types.items(), key=lambda kv: kv[1], reverse=True)[:4]
        type_breakdown = ", ".join([f"{k}:{v}" for k, v in top_types]) if top_types else "-"
        out.append({"day": d, "alerts": alert_map.get(d, 0), "high_risk_txs": risk_map.get(d, 0)})
        out[-1]["by_type"] = type_breakdown
    return list(reversed(out))


def _high_risk_users(db_path: Path = DEFAULT_DB, limit: int = 10) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, user_risk_score, last_tx_at, tx_count, avg_amount
            FROM user_profiles
            ORDER BY user_risk_score DESC, updated_at DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cursor.fetchall()
    items = []
    for user_id, risk, last_tx_at, tx_count, avg_amount in rows:
        items.append(
            {
                "user_id": user_id,
                "user_risk_score": int(risk or 0),
                "last_tx_at": _friendly_time(last_tx_at) if last_tx_at else "-",
                "tx_count": int(tx_count or 0),
                "avg_amount": float(avg_amount or 0.0),
            }
        )
    return items


def _risk_distribution(db_path: Path = DEFAULT_DB) -> dict:
    """Return distribution of user risk buckets (low/medium/high) based on user_profiles."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_risk_score FROM user_profiles")
        rows = cursor.fetchall()
    low = med = high = 0
    for (score,) in rows:
        try:
            s = int(score or 0)
        except Exception:
            s = 0
        if s >= 70:
            high += 1
        elif s >= 40:
            med += 1
        else:
            low += 1
    total = max(1, low + med + high)
    return {
        "low": low,
        "medium": med,
        "high": high,
        "total": (low + med + high),
        "low_pct": int(round((low / total) * 100)),
        "medium_pct": int(round((med / total) * 100)),
        "high_pct": int(round((high / total) * 100)),
    }


def _top_fraud_reasons(db_path: Path = DEFAULT_DB, limit: int = 6) -> list[dict]:
    """Aggregate most common fraud reason codes from local transactions."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT reason_codes
            FROM transactions
            ORDER BY timestamp DESC
            LIMIT 1000
            """
        )
        rows = cursor.fetchall()
    counts: dict[str, int] = {}
    for (raw,) in rows:
        codes = _safe_parse_reason_codes(raw if isinstance(raw, str) else None)
        for c in codes:
            if not c:
                continue
            counts[c] = counts.get(c, 0) + 1
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[: max(1, int(limit))]
    return [{"reason": k, "count": v} for k, v in top]


def _local_tx_amount_recipient(tx_ids: list[str], db_path: Path = DEFAULT_DB) -> dict[str, dict]:
    # Pull "amount" and "recipient" from local change_log (demo visibility).
    if not tx_ids:
        return {}
    init_db(db_path)
    placeholders = ",".join("?" for _ in tx_ids)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT c.entity_id, c.field_name, c.new_value
            FROM change_log c
            JOIN (
              SELECT entity_id, field_name, MAX(created_at) AS mx
              FROM change_log
              WHERE entity_type = 'transaction'
                AND field_name IN ('amount','recipient')
              GROUP BY entity_id, field_name
            ) m
            ON c.entity_id = m.entity_id AND c.field_name = m.field_name AND c.created_at = m.mx
            WHERE c.entity_type = 'transaction'
              AND c.entity_id IN ({placeholders})
            """,
            (*tx_ids,),
        )
        rows = cursor.fetchall()
    out: dict[str, dict] = {}
    for entity_id, field_name, new_value in rows:
        out.setdefault(entity_id, {})
        out[entity_id][field_name] = new_value
    return out


def _local_transactions(db_path: Path = DEFAULT_DB, status_filter: str = "", limit: int = 100) -> list[dict]:
    init_db(db_path)
    status_filter = (status_filter or "").strip().upper()
    where = ""
    params: list[Any] = []
    if status_filter == "HELD":
        where = "WHERE status IN ('HOLD_FOR_REVIEW','AWAITING_TRUSTED_APPROVAL')"
    elif status_filter == "BLOCKED":
        where = "WHERE (status LIKE 'BLOCKED_%' OR status = 'BLOCKED_LOCAL')"
    elif status_filter == "ALLOWED":
        where = "WHERE status NOT IN ('HOLD_FOR_REVIEW','AWAITING_TRUSTED_APPROVAL') AND (status NOT LIKE 'BLOCKED_%' AND status != 'BLOCKED_LOCAL')"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT tx_id, user_id, timestamp, risk_score, risk_level, status, reason_codes
            FROM transactions
            {where}
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (*params, int(limit)),
        )
        rows = cursor.fetchall()
    tx_ids = [r[0] for r in rows]
    extra = _local_tx_amount_recipient(tx_ids, db_path=db_path)
    items = []
    for tx_id, user_id, ts, risk_score, risk_level, status, reason_codes in rows:
        meta = extra.get(tx_id, {})
        decision = "ALLOW"
        try:
            if str(status or "").startswith("BLOCKED"):
                decision = "BLOCK"
            elif str(status or "") in {"HOLD_FOR_REVIEW", "AWAITING_TRUSTED_APPROVAL"}:
                decision = "HOLD"
        except Exception:
            decision = "ALLOW"
        items.append(
            {
                "tx_id": tx_id,
                "user_id": user_id,
                "timestamp": _friendly_time(ts),
                "risk_score": int(risk_score or 0),
                "risk_level": str(risk_level or ""),
                "decision": decision,
                "status": str(status or ""),
                "reason_codes": _safe_parse_reason_codes(reason_codes if isinstance(reason_codes, str) else json.dumps(reason_codes or {})),
                "amount": meta.get("amount", "-"),
                "recipient": meta.get("recipient", "-"),
            }
        )
    return items


def _set_freeze_until(*, user_id: str, freeze_until: str, db_path: Path = DEFAULT_DB) -> None:
    """Admin-only helper: set freeze_until in auth_config without requiring user PIN."""
    init_db(db_path)
    user_id = user_id.strip()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT auth_config FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row is None:
            raise ValueError("user_not_found")
        raw = row[0] or "{}"
        try:
            cfg = json.loads(raw)
        except Exception:
            cfg = {}
        if not isinstance(cfg, dict):
            cfg = {}
        cfg["freeze_until"] = freeze_until
        cursor.execute("UPDATE users SET auth_config = ? WHERE user_id = ?", (json.dumps(cfg), user_id))
        conn.commit()


def _fetch_outbox_rows(limit: int = 200) -> list[dict]:
    # Read local sync queue (outbox) for the Sync Queue page.
    init_db(DEFAULT_DB)
    query = (
        "SELECT outbox_id, tx_id, sync_state, retry_count, next_retry_at, last_error "
        "FROM outbox ORDER BY rowid DESC LIMIT ?"
    )
    rows = []
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
    items = []
    for outbox_id, tx_id, sync_state, retry_count, next_retry_at, last_error in rows:
        items.append(
            {
                "created_at": "",
                "outbox_id": outbox_id,
                "tx_id": tx_id,
                "sync_state": sync_state,
                "retry_count": retry_count,
                "next_retry": next_retry_at or "-",
                "last_error": last_error or "-",
            }
        )
    return items


def _outbox_stats(rows: list[dict]) -> dict:
    # Aggregate counts for the Sync Queue cards.
    counts = {"PENDING": 0, "RETRYING": 0, "SYNCED": 0, "HOLD": 0, "BLOCKED": 0}
    for row in rows:
        state = row.get("sync_state", "")
        if state in counts:
            counts[state] += 1
    return {
        "pending": counts["PENDING"],
        "retrying": counts["RETRYING"],
        "synced": counts["SYNCED"],
        "held": counts["HOLD"],
        "blocked": counts["BLOCKED"],
    }


def _store_face_capture(data_url: str, role: str) -> str:
    cleaned = (data_url or "").strip()
    prefix = "data:image/png;base64,"
    if not cleaned.startswith(prefix):
        raise ValueError("Face capture is missing or invalid. Please capture your face before login.")
    FACE_CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    payload = cleaned[len(prefix) :]
    image_bytes = base64.b64decode(payload)
    filename = f"{role}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
    path = FACE_CAPTURE_DIR / filename
    path.write_bytes(image_bytes)
    return str(path)


def _face_hash_from_capture_path(capture_path: str) -> tuple[str, str]:
    # Compute a lightweight perceptual hash from the captured PNG.
    png_bytes = Path(capture_path).read_bytes()
    face_hash = compute_dhash64_from_png(png_bytes)
    return face_hash.algo, face_hash.hex64


@app.get("/")
def index(request: Request):
    lang = _lang_from_request(request)
    # After-midsem home: make it obvious this is the upgraded build and link to server API docs.
    i18n = _bundle(lang)
    return render_template(
        request,
        "after_home.html",
        {
            "lang": lang,
            "i18n": i18n,
            "langs": _language_choices(),
            "server_url": DEFAULT_SERVER_URL.rstrip("/"),
            "build_id": BUILD_ID,
        },
    )


@app.get("/customer")
def customer_entry(request: Request):
    # Clean, memorable entry URL for the customer portal.
    lang = _lang_from_request(request)
    return RedirectResponse(url=f"/customer/login?lang={lang}", status_code=303)


@app.get("/bank")
def bank_entry(request: Request):
    # Clean, memorable entry URL for the bank portal.
    lang = _lang_from_request(request)
    return RedirectResponse(url=f"/bank/login?lang={lang}", status_code=303)


@app.get("/customer/login")
def customer_login_page(request: Request):
    lang = _lang_from_request(request)
    return render_template(request, "login.html", _login_context(request, lang=lang, mode="customer"))

@app.get("/customer/register")
def customer_register_page(request: Request):
    lang = _lang_from_request(request)
    return render_template(request, "login.html", _login_context(request, lang=lang, mode="customer_register"))


@app.post("/customer/register")
def customer_register(
    request: Request,
    user_id: str = Form(...),
    phone: str = Form(...),
    pin: str = Form(...),
    face_image: str = Form(default=""),
    device_id: str = Form(default=""),
    lang: str = Form(default="en"),
):
    # Offline-first onboarding: create user locally + enroll face + enroll device.
    lang = _resolve_lang(lang)
    try:
        capture_path = _store_face_capture(face_image, role="customer")
        captured_algo, captured_hash = _face_hash_from_capture_path(capture_path)
    except Exception:
        return render_template(
            request,
            "login.html",
            _login_context(request, lang=lang, mode="customer_register", error=_t(lang, "face_required")),
            status_code=400,
        )

    try:
        create_user(
            user_id=user_id.strip(),
            phone_number=phone.strip(),
            pin=pin.strip(),
            db_path=DEFAULT_DB,
            replace_existing=False,
        )
    except Exception as exc:
        # Likely user_exists; keep message simple.
        return render_template(
            request,
            "login.html",
            _login_context(request, lang=lang, mode="customer_register", error=str(exc)),
            status_code=400,
        )

    ok_face, _ = enroll_or_verify_face_hash(
        user_id=user_id.strip(),
        pin=pin.strip(),
        captured_algo=captured_algo,
        captured_hash=captured_hash,
        db_path=DEFAULT_DB,
    )
    if not ok_face:
        return render_template(
            request,
            "login.html",
            _login_context(request, lang=lang, mode="customer_register", error=_t(lang, "face_mismatch")),
            status_code=400,
        )

    ok_dev, dev_reason = enroll_or_verify_device_id(
        user_id=user_id.strip(),
        pin=pin.strip(),
        device_id=device_id,
        db_path=DEFAULT_DB,
    )
    if not ok_dev:
        return render_template(
            request,
            "login.html",
            _login_context(request, lang=lang, mode="customer_register", error=_t(lang, "device_required")),
            status_code=400,
        )

    response = RedirectResponse(url=f"/dashboard/customer?lang={lang}", status_code=303)
    response.set_cookie(ROLE_COOKIE, "customer")
    response.set_cookie(USER_COOKIE, user_id.strip())
    response.set_cookie(FACE_COOKIE, "1")
    response.set_cookie(DEVICE_COOKIE, "untrusted" if dev_reason == "new_device" else "trusted")
    # After-midsem: also create a server JWT session (PIN-as-password) so dashboards can fetch API data.
    try:
        token, _ = _ensure_server_session_for_customer(user_id.strip(), pin.strip(), device_id=device_id)
        if token:
            response.set_cookie(JWT_COOKIE, token, httponly=True, samesite="lax")
    except Exception:
        # Server may be offline during registration; UI still works in offline-only mode.
        pass
    return response


@app.get("/bank/login")
def bank_login_page(request: Request):
    lang = _lang_from_request(request)
    return render_template(request, "login.html", _login_context(request, lang=lang, mode="bank"))


@app.get("/admin/login")
def admin_login_compat(request: Request):
    # Back-compat route for old links.
    lang = _lang_from_request(request)
    return RedirectResponse(url=f"/bank/login?lang={lang}", status_code=303)


@app.post("/login")
def login(
    request: Request,
    role: str = Form(...),
    lang: str = Form(default="en"),
    user_id: str = Form(default=""),
    pin: str = Form(default=""),
    admin_username: str = Form(default=""),
    admin_password: str = Form(default=""),
    face_image: str = Form(default=""),
    device_id: str = Form(default=""),
):
    lang = _resolve_lang(lang)
    role = (role or "").strip().lower()
    # Back-compat: older template posted role=admin. Treat it as bank login.
    if role == "admin":
        role = "bank"
    if role not in {"customer", "bank"}:
        context = _login_context(request, lang=lang, mode="choose", error=_t(lang, "invalid_role"))
        return render_template(request, "login.html", context, status_code=400)

    try:
        capture_path = _store_face_capture(face_image, role=role)
        captured_algo, captured_hash = _face_hash_from_capture_path(capture_path)
    except Exception:
        context = _login_context(request, lang=lang, mode=role, error=_t(lang, "face_required"))
        return render_template(request, "login.html", context, status_code=400)

    if role == "customer":
        try:
            auth = authenticate_user(user_id=user_id.strip(), pin=pin.strip(), db_path=DEFAULT_DB)
        except Exception as exc:
            # Avoid 500s on malformed PIN etc; show a friendly error.
            context = _login_context(
                request,
                lang=lang,
                mode="customer",
                error=f"{_t(lang, 'customer_login_failed')}: {str(exc)}",
            )
            return render_template(request, "login.html", context, status_code=400)
        if not auth.is_authenticated:
            reason = getattr(auth, "reason", "") or ""
            if reason == "user_not_found":
                err = "User not found. Please register first."
            elif reason in {"invalid_pin", "lockout_started", "locked_out"}:
                err = "Incorrect PIN or account temporarily locked. Please try again."
            else:
                err = _t(lang, "customer_login_failed")
            context = _login_context(request, lang=lang, mode="customer", error=err)
            return render_template(request, "login.html", context, status_code=400)
        ok, why = enroll_or_verify_face_hash(
            user_id=user_id.strip(),
            pin=pin.strip(),
            captured_algo=captured_algo,
            captured_hash=captured_hash,
            db_path=DEFAULT_DB,
        )
        if not ok:
            context = _login_context(request, lang=lang, mode="customer", error=_t(lang, "face_mismatch"))
            return render_template(request, "login.html", context, status_code=400)
        ok_dev, dev_reason = enroll_or_verify_device_id(
            user_id=user_id.strip(),
            pin=pin.strip(),
            device_id=device_id,
            db_path=DEFAULT_DB,
        )
        if not ok_dev:
            context = _login_context(request, lang=lang, mode="customer", error=_t(lang, "device_required"))
            return render_template(request, "login.html", context, status_code=400)
        response = RedirectResponse(url=f"/dashboard/customer?lang={lang}", status_code=303)
        response.set_cookie(ROLE_COOKIE, "customer")
        response.set_cookie(USER_COOKIE, user_id.strip())
        response.set_cookie(FACE_COOKIE, "1")
        response.set_cookie(DEVICE_COOKIE, "untrusted" if dev_reason == "new_device" else "trusted")
        # After-midsem: mint server JWT session (PIN-as-password) for API-backed dashboard.
        try:
            token, _ = _ensure_server_session_for_customer(user_id.strip(), pin.strip(), device_id=device_id)
            if token:
                response.set_cookie(JWT_COOKIE, token, httponly=True, samesite="lax")
        except Exception:
            pass
        return response

    if role == "bank":
        if admin_username.strip() != DEFAULT_BANK_USERNAME or admin_password.strip() != DEFAULT_BANK_PASSWORD:
            context = _login_context(request, lang=lang, mode="bank", error=_t(lang, "admin_login_failed"))
            return render_template(request, "login.html", context, status_code=400)
        # Bank portal UX: require a live face capture step (already enforced by the UI),
        # but do NOT hard-block login on a strict hash match.
        # Low-end webcams + lighting changes can cause false mismatches, which is too disruptive for demos.
        bank_face_path = DB_PATH.parent / "bank_face_hash.json"
        try:
            bank_face_path.parent.mkdir(parents=True, exist_ok=True)
            bank_face_path.write_text(json.dumps({"algo": captured_algo, "hash": captured_hash}))
        except Exception:
            pass
        response = RedirectResponse(url=f"/bank/dashboard?lang={lang}", status_code=303)
        response.set_cookie(ROLE_COOKIE, "bank")
        response.set_cookie(USER_COOKIE, DEFAULT_BANK_USERNAME)
        response.set_cookie(FACE_COOKIE, "1")
        # After-midsem: bank portal uses server API via a bank_officer JWT.
        try:
            token, _ = _ensure_server_session_for_bank()
            if token:
                response.set_cookie(JWT_COOKIE, token, httponly=True, samesite="lax")
        except Exception:
            pass
        return response

    context = _login_context(request, lang=lang, mode="choose", error=_t(lang, "invalid_role"))
    return render_template(request, "login.html", context, status_code=400)


@app.get("/logout")
def logout(lang: str = "en"):
    response = RedirectResponse(url=f"/?lang={_resolve_lang(lang)}", status_code=303)
    response.delete_cookie(ROLE_COOKIE)
    response.delete_cookie(USER_COOKIE)
    response.delete_cookie(FACE_COOKIE)
    response.delete_cookie(JWT_COOKIE)
    response.delete_cookie(FLASH_MSG_COOKIE)
    response.delete_cookie(FLASH_ERR_COOKIE)
    response.delete_cookie(FLASH_VOICE_COOKIE)
    return response


@app.get("/customer/dashboard")
def customer_dashboard(request: Request):
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _lang_from_request(request)
    return RedirectResponse(url=f"/dashboard/customer?lang={lang}", status_code=303)


@app.get("/dashboard/customer")
def customer_home(request: Request):
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _lang_from_request(request)
    context = _customer_dashboard_context(request, lang=lang)
    token = _jwt_from_request(request)
    context["server_url"] = _server_api_url()
    context["server"] = {"connected": False, "error": "", "balance": 0.0}
    if token:
        try:
            data = _server_dashboard_customer_data(token)
            context["server"] = {"connected": True, "error": "", "balance": float(data.get("balance", 0.0))}
        except Exception as exc:
            context["server"] = {"connected": False, "error": str(exc), "balance": 0.0}
    # Build customer alert strings server-side (avoid template .format on missing keys).
    alerts: list[str] = []
    if context.get("device_trust") == "untrusted":
        alerts.append(f"{_t(lang, 'cust_alert_new_device_title')} {_t(lang, 'cust_alert_new_device_body')}")
    try:
        held = int((context.get("customer_stats") or {}).get("held", 0))
    except Exception:
        held = 0
    try:
        pending = int((context.get("customer_stats") or {}).get("pending", 0))
    except Exception:
        pending = 0
    if held > 0:
        alerts.append(f"{_t(lang, 'cust_alert_held_title')} {_tf(lang, 'cust_alert_held_body', count=held)}")
    if pending > 0:
        alerts.append(f"{_t(lang, 'cust_alert_pending_title')} {_tf(lang, 'cust_alert_pending_body', count=pending)}")
    if not alerts:
        alerts.append(f"{_t(lang, 'cust_alert_clear_title')} {_t(lang, 'cust_alert_clear_body')}")
    context["alerts"] = alerts

    context = _read_and_clear_flash(request, context)
    resp = render_template(request, "customer_home.html", context)
    resp.delete_cookie(FLASH_MSG_COOKIE)
    resp.delete_cookie(FLASH_ERR_COOKIE)
    resp.delete_cookie(FLASH_VOICE_COOKIE)
    return resp


@app.get("/bank/dashboard")
def bank_dashboard(request: Request):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _lang_from_request(request)
    context = _admin_dashboard_context(request, lang=lang)
    token = _jwt_from_request(request)
    context["server"] = {"connected": False, "error": "", "transactions": [], "fraud_logs": [], "sync_status": {}}
    # Local admin panels (always available offline).
    view = (request.query_params.get("view") or "").strip().lower()
    status_filter = {"held": "HELD", "blocked": "BLOCKED", "allowed": "ALLOWED"}.get(view, "")
    context["local_admin"] = {
        "overview": _local_admin_overview(DEFAULT_DB),
        "trends": _fraud_trends(DEFAULT_DB, days=7),
        "high_risk_users": _high_risk_users(DEFAULT_DB, limit=10),
        # Curated admin intelligence (for professor/demo visibility).
        "risk_distribution": _risk_distribution(DEFAULT_DB),
        "top_reasons": _top_fraud_reasons(DEFAULT_DB, limit=6),
        "alerts": list_recent_alerts(DEFAULT_DB, limit=20),
        "devices": list_devices(DEFAULT_DB, limit=50),
        "notifications": list_notifications(role="bank", user_id=None, db_path=DEFAULT_DB, limit=20),
        "transactions": _local_transactions(DEFAULT_DB, status_filter=status_filter, limit=120),
        "view": view or "all",
    }
    if token:
        try:
            data = _server_dashboard_bank_data(token)
            context["server"] = {"connected": True, "error": "", **data}
        except Exception as exc:
            context["server"] = {"connected": False, "error": str(exc), "transactions": [], "fraud_logs": [], "sync_status": {}}
    return render_template(request, "bank_dashboard.html", context)


@app.post("/bank/server/tx/review")
def bank_review_server_tx(
    request: Request,
    tx_id: str = Form(...),
    decision: str = Form(...),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    token = _jwt_from_request(request)
    if not token:
        return render_template(
            request,
            "bank_dashboard.html",
            _admin_dashboard_context(request, error="Missing server session. Please re-login.", lang=lang),
            status_code=400,
        )
    try:
        _api_call("POST", f"/transactions/{tx_id}/review", token=token, json_body={"decision": decision})
        return RedirectResponse(url=f"/bank/dashboard?lang={lang}", status_code=303)
    except Exception as exc:
        ctx = _admin_dashboard_context(request, error=str(exc), lang=lang)
        return render_template(request, "bank_dashboard.html", ctx, status_code=400)


@app.post("/bank/local/tx/review")
def bank_review_local_tx(
    request: Request,
    tx_id: str = Form(...),
    decision: str = Form(...),
    lang: str = Form(default="en"),
):
    """Approve/reject a locally HELD transaction (offline admin workflow)."""
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    tx_id = tx_id.strip()
    decision = (decision or "").strip().lower()
    if decision not in {"approve", "reject"}:
        return RedirectResponse(url=f"/bank/dashboard?lang={lang}", status_code=303)

    init_db(DEFAULT_DB)
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, status FROM transactions WHERE tx_id = ?",
            (tx_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return RedirectResponse(url=f"/bank/dashboard?lang={lang}", status_code=303)
        user_id, status = row
        if status not in {"HOLD_FOR_REVIEW", "AWAITING_TRUSTED_APPROVAL"}:
            return RedirectResponse(url=f"/bank/dashboard?lang={lang}", status_code=303)

        if decision == "approve":
            cursor.execute(
                "UPDATE transactions SET status = 'PENDING' WHERE tx_id = ?",
                (tx_id,),
            )
            cursor.execute("UPDATE outbox SET sync_state = 'PENDING' WHERE tx_id = ?", (tx_id,))
            conn.commit()
            try:
                from src.database.monitoring_store import create_notification

                create_notification(
                    notif_type="held_approved",
                    title="Held transaction approved",
                    body=f"Transaction {tx_id[:8]}... for {user_id} approved and queued for sync.",
                    role="bank",
                    user_id=str(user_id),
                    db_path=DEFAULT_DB,
                )
            except Exception:
                pass
        else:
            cursor.execute(
                "UPDATE transactions SET status = 'BLOCKED_MANUAL_REJECT' WHERE tx_id = ?",
                (tx_id,),
            )
            cursor.execute("UPDATE outbox SET sync_state = 'BLOCKED' WHERE tx_id = ?", (tx_id,))
            conn.commit()
            try:
                from src.database.monitoring_store import create_alert, create_notification

                create_alert(
                    alert_type="HELD_REJECTED",
                    severity="MEDIUM",
                    message=f"{user_id}: bank rejected held transaction {tx_id}",
                    user_id=str(user_id),
                    metadata={"tx_id": tx_id},
                    db_path=DEFAULT_DB,
                )
                create_notification(
                    notif_type="held_rejected",
                    title="Held transaction rejected",
                    body=f"Transaction {tx_id[:8]}... for {user_id} rejected (blocked locally).",
                    role="bank",
                    user_id=str(user_id),
                    db_path=DEFAULT_DB,
                )
            except Exception:
                pass

    return RedirectResponse(url=f"/bank/dashboard?lang={lang}&view=held", status_code=303)


@app.post("/customer/server/transactions")
def customer_create_server_tx(
    request: Request,
    amount: float = Form(...),
    recipient: str = Form(...),
    device_id: str = Form(default=""),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    token = _jwt_from_request(request)
    if not token:
        return _customer_redirect(lang, error="Missing server session. Please re-login.")
    try:
        _api_call(
            "POST",
            "/transactions",
            token=token,
            json_body={"amount": float(amount), "recipient": recipient.strip(), "device_id": device_id.strip()},
        )
        return _customer_redirect(lang, message="Server transaction created.")
    except Exception as exc:
        return _customer_redirect(lang, error=str(exc))


@app.get("/admin/dashboard")
def admin_dashboard_compat(request: Request):
    # Back-compat route for old links.
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    return RedirectResponse(url=f"/bank/dashboard?lang={lang}", status_code=303)


# =========================
# Admin API (Local SQLite)
# =========================

@app.get("/admin/api/fraud-trends")
def admin_api_fraud_trends(request: Request, days: int = 7):
    guard = _require_role(request, "bank")
    if guard:
        return _json_err("forbidden", status_code=403)
    try:
        return _json_ok({"items": _fraud_trends(DEFAULT_DB, days=int(days))})
    except Exception as exc:
        return _json_err(str(exc), status_code=500)


@app.get("/admin/api/high-risk-users")
def admin_api_high_risk_users(request: Request, limit: int = 20):
    guard = _require_role(request, "bank")
    if guard:
        return _json_err("forbidden", status_code=403)
    try:
        return _json_ok({"items": _high_risk_users(DEFAULT_DB, limit=int(limit))})
    except Exception as exc:
        return _json_err(str(exc), status_code=500)


@app.get("/admin/api/alerts")
def admin_api_alerts(request: Request, limit: int = 50):
    guard = _require_role(request, "bank")
    if guard:
        return _json_err("forbidden", status_code=403)
    try:
        return _json_ok({"items": list_recent_alerts(DEFAULT_DB, limit=int(limit))})
    except Exception as exc:
        return _json_err(str(exc), status_code=500)


@app.get("/admin/api/devices")
def admin_api_devices(request: Request, limit: int = 200):
    guard = _require_role(request, "bank")
    if guard:
        return _json_err("forbidden", status_code=403)
    try:
        return _json_ok({"items": list_devices(DEFAULT_DB, limit=int(limit))})
    except Exception as exc:
        return _json_err(str(exc), status_code=500)


@app.get("/admin/api/transactions")
def admin_api_transactions(request: Request, status: str = "", limit: int = 200):
    guard = _require_role(request, "bank")
    if guard:
        return _json_err("forbidden", status_code=403)
    try:
        # status: all|held|blocked|allowed
        view = (status or "").strip().lower()
        status_filter = {"held": "HELD", "blocked": "BLOCKED", "allowed": "ALLOWED"}.get(view, "")
        items = _local_transactions(DEFAULT_DB, status_filter=status_filter, limit=int(limit))
        return _json_ok({"items": items})
    except Exception as exc:
        return _json_err(str(exc), status_code=500)


@app.get("/admin/api/user-profile/{user_id}")
def admin_api_user_profile(request: Request, user_id: str):
    guard = _require_role(request, "bank")
    if guard:
        return _json_err("forbidden", status_code=403)
    try:
        prof = get_or_create_profile(user_id.strip(), db_path=DEFAULT_DB)
        payload = {
            "user_id": prof.user_id,
            "tx_count": prof.tx_count,
            "avg_amount": prof.avg_amount,
            "user_risk_score": prof.user_risk_score,
            "preferred_hours": preferred_hours(prof, top_n=3),
            "last_tx_at": prof.last_tx_at or "",
        }
        return _json_ok(payload)
    except Exception as exc:
        return _json_err(str(exc), status_code=500)


@app.post("/admin/api/transactions/{tx_id}/review")
def admin_api_review_tx(request: Request, tx_id: str, decision: str = Form(...)):
    guard = _require_role(request, "bank")
    if guard:
        return _json_err("forbidden", status_code=403)
    try:
        tx_id = tx_id.strip()
        decision = (decision or "").strip().lower()
        if decision not in {"approve", "reject"}:
            return _json_err("invalid_decision", status_code=400)
        # reuse local review logic: update status + outbox
        init_db(DEFAULT_DB)
        with sqlite3.connect(DEFAULT_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, status FROM transactions WHERE tx_id = ?", (tx_id,))
            row = cursor.fetchone()
            if row is None:
                return _json_err("tx_not_found", status_code=404)
            user_id, status = row
            if status not in {"HOLD_FOR_REVIEW", "AWAITING_TRUSTED_APPROVAL"}:
                return _json_err("tx_not_held", status_code=409)
            if decision == "approve":
                cursor.execute("UPDATE transactions SET status = 'PENDING' WHERE tx_id = ?", (tx_id,))
                cursor.execute("UPDATE outbox SET sync_state = 'PENDING' WHERE tx_id = ?", (tx_id,))
            else:
                cursor.execute("UPDATE transactions SET status = 'BLOCKED_MANUAL_REJECT' WHERE tx_id = ?", (tx_id,))
                cursor.execute("UPDATE outbox SET sync_state = 'BLOCKED' WHERE tx_id = ?", (tx_id,))
            conn.commit()
        return _json_ok({"tx_id": tx_id, "decision": decision})
    except Exception as exc:
        return _json_err(str(exc), status_code=500)


@app.post("/admin/api/users/{user_id}/freeze")
def admin_api_freeze_user(request: Request, user_id: str, minutes: int = Form(default=60)):
    guard = _require_role(request, "bank")
    if guard:
        return _json_err("forbidden", status_code=403)
    try:
        minutes = int(minutes)
        if minutes <= 0:
            return _json_err("invalid_minutes", status_code=400)
        freeze_until = (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()
        _set_freeze_until(user_id=user_id, freeze_until=freeze_until, db_path=DEFAULT_DB)
        return _json_ok({"user_id": user_id, "freeze_until": freeze_until}, message="frozen")
    except Exception as exc:
        return _json_err(str(exc), status_code=500)


@app.post("/admin/api/users/{user_id}/unfreeze")
def admin_api_unfreeze_user(request: Request, user_id: str):
    guard = _require_role(request, "bank")
    if guard:
        return _json_err("forbidden", status_code=403)
    try:
        _set_freeze_until(user_id=user_id, freeze_until="", db_path=DEFAULT_DB)
        return _json_ok({"user_id": user_id, "freeze_until": ""}, message="unfrozen")
    except Exception as exc:
        return _json_err(str(exc), status_code=500)


@app.get("/agent")
def agent_mode(request: Request):
    # Assisted agent/kiosk workflow page
    guard = _require_role(request, "bank")
    if guard:
        return guard
    init_db(DEFAULT_DB)
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    context = _admin_dashboard_context(request, lang=lang)
    context["agent_result"] = None
    return templates.TemplateResponse(request, "agent.html", context)


@app.post("/users")
def add_user(
    request: Request,
    user_id: str = Form(...),
    phone: str = Form(...),
    pin: str = Form(...),
    replace: str | None = Form(default=None),
    lang: str = Form(default="en"),
):
    # Create or replace a local user (stored in SQLite).
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    try:
        create_user(
            user_id=user_id.strip(),
            phone_number=phone.strip(),
            pin=pin.strip(),
            db_path=DEFAULT_DB,
            replace_existing=bool(replace),
        )
        msg = f"User {'replaced' if replace else 'created'}: {user_id.strip()}"
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, message=msg, lang=lang))
    except Exception as exc:
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, error=str(exc), lang=lang), status_code=400
        )


@app.post("/transactions")
def add_transaction(
    request: Request,
    user_id: str = Form(...),
    pin: str = Form(...),
    amount: float = Form(...),
    recipient: str = Form(...),
    lang: str = Form(default="en"),
):
    # Create a transaction: encrypt locally + risk score + add to outbox.
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    try:
        stored = create_secure_transaction(
            user_id=user_id.strip(),
            pin=pin.strip(),
            amount=amount,
            recipient=recipient.strip(),
            db_path=DEFAULT_DB,
        )
        reason_text = ", ".join(_friendly_reason(code, lang=lang) for code in stored.reason_codes) or _t(lang, "no_alert")
        msg = (
            f"{_t(lang, 'tx_saved')} "
            f"{_t(lang, 'risk_label')} {_friendly_risk(stored.risk_level, lang=lang)} ({stored.risk_score}/100). "
            f"{_t(lang, 'decision_label')} {_friendly_action(stored.action_decision, lang=lang)}. "
            f"{_t(lang, 'reason_label')} {reason_text}. "
            f"{_t(lang, 'guidance_label')} {' '.join(stored.intervention_guidance)}"
        )
        if stored.approval_required:
            msg += (
                f" {_t(lang, 'trusted_required')} ({_t(lang, 'contact_ending')} {stored.trusted_contact_hint}). "
                f"{_t(lang, 'demo_code')}: {stored.approval_code_for_demo}"
            )
        voice_text = _build_voice_prompt(
            lang=lang,
            risk_level=stored.risk_level,
            action=stored.action_decision,
            guidance=list(stored.intervention_guidance),
        )
        return templates.TemplateResponse(request, "index.html",
            _admin_dashboard_context(request, message=msg, lang=lang, voice_text=voice_text),
        )
    except Exception as exc:
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, error=str(exc), lang=lang), status_code=400
        )


@app.post("/customer/transactions")
def add_customer_transaction(
    request: Request,
    pin: str = Form(...),
    amount: float = Form(...),
    recipient: str = Form(...),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    user_id = request.cookies.get(USER_COOKIE, "").strip()
    device_untrusted = _user_ctx(request).get("device_trust") == "untrusted"
    if not user_id:
        return _customer_redirect(lang, error=_t(lang, "not_logged_in"))
    try:
        stored = create_secure_transaction(
            user_id=user_id,
            pin=pin.strip(),
            amount=amount,
            recipient=recipient.strip(),
            db_path=DEFAULT_DB,
            extra_reason_codes=(["NEW_DEVICE"] if device_untrusted else None),
            extra_risk_points=(35 if device_untrusted else 0),
            force_hold=device_untrusted,
        )
        # Keep the flash message small (stored in a cookie). Full reasons are available per-transaction.
        decision = _friendly_action(stored.action_decision, lang=lang)
        risk = f"{_friendly_risk(stored.risk_level, lang=lang)} ({stored.risk_score}/100)"
        msg = f"{_t(lang, 'tx_saved')} {_t(lang, 'decision_label')} {decision}. {_t(lang, 'risk_label')} {risk}."
        if stored.approval_required:
            msg += f" {_t(lang, 'trusted_required')} {_t(lang, 'demo_code')}: {stored.approval_code_for_demo}"
        voice_text = _build_voice_prompt(
            lang=lang,
            risk_level=stored.risk_level,
            action=stored.action_decision,
            guidance=list(stored.intervention_guidance),
        )
        return _customer_redirect(lang, message=msg, voice_text=voice_text)
    except Exception as exc:
        return _customer_redirect(lang, error=str(exc))


@app.post("/customer/trusted-contact")
def update_customer_trusted_contact(
    request: Request,
    pin: str = Form(...),
    trusted_contact: str = Form(...),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    user_id = request.cookies.get(USER_COOKIE, "").strip()
    if not user_id:
        return _customer_redirect(lang, error=_t(lang, "not_logged_in"))
    try:
        set_trusted_contact(user_id=user_id, pin=pin.strip(), trusted_contact=trusted_contact.strip(), db_path=DEFAULT_DB)
        msg = f"{_t(lang, 'trusted_updated')} {user_id}."
        return _customer_redirect(lang, message=msg)
    except Exception as exc:
        return _customer_redirect(lang, error=str(exc))


@app.post("/customer/panic-freeze")
def customer_panic_freeze(
    request: Request,
    pin: str = Form(...),
    minutes: int = Form(default=60),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    user_id = request.cookies.get(USER_COOKIE, "").strip()
    if not user_id:
        return _customer_redirect(lang, error=_t(lang, "not_logged_in"))
    try:
        freeze_until = enable_panic_freeze(user_id=user_id, pin=pin.strip(), minutes=minutes, db_path=DEFAULT_DB)
        msg = f"{_t(lang, 'freeze_enabled')} {freeze_until} ({user_id})."
        return _customer_redirect(lang, message=msg)
    except Exception as exc:
        return _customer_redirect(lang, error=str(exc))


@app.get("/customer/history")
def customer_history_page(request: Request, lang: str = ""):
    """Customer transaction history (decrypt requires PIN)."""
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _lang_from_request(request, fallback=lang or "en")
    context = _customer_dashboard_context(request, lang=lang)
    context.update({"history": [], "history_limit": 10})
    return render_template(request, "customer_history.html", context)


@app.post("/customer/history")
def customer_history_view(
    request: Request,
    pin: str = Form(...),
    limit: int = Form(default=10),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    user_id = request.cookies.get(USER_COOKIE, "").strip()
    context = _customer_dashboard_context(request, lang=lang)
    try:
        items = list_secure_transactions(
            user_id=user_id,
            pin=pin.strip(),
            db_path=DEFAULT_DB,
            limit=int(limit),
        )
        formatted = []
        for row in items:
            formatted.append(
                {
                    **row,
                    "display_time": _friendly_time(row.get("timestamp", "")),
                    "display_risk": f"{_friendly_risk(row.get('risk_level','LOW'), lang=lang)} ({int(row.get('risk_score', 0))}/100)",
                    "display_reasons": [_friendly_reason(code, lang=lang) for code in row.get("reason_codes", [])],
                    "display_status": _friendly_status(row.get("status", ""), lang=lang),
                    "display_action": _friendly_action(row.get("action_decision", "ALLOW"), lang=lang),
                }
            )
        context.update({"history": formatted, "history_limit": int(limit)})
        return render_template(request, "customer_history.html", context)
    except Exception as exc:
        context.update({"history": [], "history_limit": int(limit), "error": str(exc)})
        return render_template(request, "customer_history.html", context, status_code=400)


@app.get("/customer/tx/{tx_id}")
def customer_tx_detail_page(request: Request, tx_id: str, lang: str = ""):
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _lang_from_request(request, fallback=lang or "en")
    context = _customer_dashboard_context(request, lang=lang)
    context.update({"tx_id": tx_id, "details": None})
    return render_template(request, "customer_tx_detail.html", context)


@app.post("/customer/tx/{tx_id}")
def customer_tx_detail_view(
    request: Request,
    tx_id: str,
    pin: str = Form(...),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "customer")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    user_id = request.cookies.get(USER_COOKIE, "").strip()
    context = _customer_dashboard_context(request, lang=lang)
    context["tx_id"] = tx_id
    try:
        row = read_secure_transaction(tx_id=tx_id, user_id=user_id, pin=pin.strip(), db_path=DEFAULT_DB)
        reason_codes = row.get("reason_codes", []) or []
        reason_text = ", ".join(_friendly_reason(str(c), lang=lang) for c in reason_codes) or _t(lang, "no_alert")
        guidance = []
        try:
            guidance = list((row.get("intervention", {}) or {}).get("guidance", []) or [])
        except Exception:
            guidance = []
        context["details"] = {
            "amount": row.get("amount", ""),
            "recipient": row.get("recipient", ""),
            "risk_score": row.get("risk_score", 0),
            "risk_level": row.get("risk_level", ""),
            "status": row.get("status", ""),
            "reason_text": reason_text,
            "guidance": guidance,
        }
        return render_template(request, "customer_tx_detail.html", context)
    except Exception as exc:
        context["details"] = None
        context["error"] = str(exc)
        return render_template(request, "customer_tx_detail.html", context, status_code=400)


@app.post("/agent/assist")
def agent_assist(
    request: Request,
    user_id: str = Form(...),
    phone: str = Form(...),
    pin: str = Form(...),
    amount: float = Form(...),
    recipient: str = Form(...),
    trusted_contact: str = Form(default=""),
    lang: str = Form(default="en"),
):
    # Agent flow: user + transaction in one screen.
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    clean_user = user_id.strip()
    clean_pin = pin.strip()
    init_db(DEFAULT_DB)
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (clean_user,))
        user_exists = cursor.fetchone() is not None

    if user_exists:
        auth = authenticate_user(user_id=clean_user, pin=clean_pin, db_path=DEFAULT_DB)
        if not auth.is_authenticated:
            context = _ctx(request, error=_t(lang, "invalid_pin_existing"), lang=lang)
            context.update(_user_ctx(request))
            context["agent_result"] = None
            return templates.TemplateResponse(request, "agent.html", context, status_code=400)
    else:
        try:
            create_user(
                user_id=clean_user,
                phone_number=phone.strip(),
                pin=clean_pin,
                db_path=DEFAULT_DB,
                replace_existing=False,
            )
        except ValueError as exc:
            context = _ctx(request, error=str(exc), lang=lang)
            context.update(_user_ctx(request))
            context["agent_result"] = None
            return templates.TemplateResponse(request, "agent.html", context, status_code=400)

    if trusted_contact.strip():
        set_trusted_contact(
            user_id=clean_user,
            pin=clean_pin,
            trusted_contact=trusted_contact.strip(),
            db_path=DEFAULT_DB,
        )

    try:
        stored = create_secure_transaction(
            user_id=clean_user,
            pin=clean_pin,
            amount=amount,
            recipient=recipient.strip(),
            db_path=DEFAULT_DB,
        )
    except Exception as exc:
        context = _ctx(request, error=str(exc), lang=lang)
        context.update(_user_ctx(request))
        context["agent_result"] = None
        return templates.TemplateResponse(request, "agent.html", context, status_code=400)

    reasons = [_friendly_reason(code, lang=lang) for code in stored.reason_codes]
    guidance = list(stored.intervention_guidance)
    voice_text = _build_voice_prompt(
        lang=lang,
        risk_level=stored.risk_level,
        action=stored.action_decision,
        guidance=guidance,
    )
    summary = (
        f"{_t(lang, 'agent_done')} "
        f"{_t(lang, 'risk_label')} {_friendly_risk(stored.risk_level, lang=lang)} ({stored.risk_score}/100). "
        f"{_t(lang, 'decision_label')} {_friendly_action(stored.action_decision, lang=lang)}."
    )
    context = _ctx(request, message=summary, lang=lang, voice_text=voice_text)
    context.update(_user_ctx(request))
    context["agent_result"] = {
        "user_id": clean_user,
        "tx_id": stored.tx_id,
        "risk": f"{_friendly_risk(stored.risk_level, lang=lang)} ({stored.risk_score}/100)",
        "action": _friendly_action(stored.action_decision, lang=lang),
        "status": _friendly_status(stored.status, lang=lang),
        "reasons": reasons,
        "guidance": guidance,
        "approval_required": stored.approval_required,
        "approval_code_for_demo": stored.approval_code_for_demo,
    }
    return templates.TemplateResponse(request, "agent.html", context)


@app.get("/transactions")
def list_transactions(request: Request, user_id: str, pin: str, limit: int = 10, lang: str = "en"):
    lang = _resolve_lang(lang)
    session = _user_ctx(request)
    if session.get("role") == "customer":
        # Customer portal uses /customer/history (requires PIN; avoids exposing arbitrary user_id in query params).
        return _flash_redirect(f"/customer/history?lang={lang}", error=_t(lang, "cust_use_history"))
    if session["role"] == "customer" and session["active_user"] and session["active_user"] != user_id.strip():
        return _flash_redirect(f"/customer/history?lang={lang}", error=_t(lang, "customer_scope_error"))
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
                    "display_risk": f"{_friendly_risk(row['risk_level'], lang=lang)} ({row['risk_score']}/100)",
                    "display_reasons": [
                        _friendly_reason(code, lang=lang) for code in row.get("reason_codes", [])
                    ],
                    "display_status": _friendly_status(row["status"], lang=lang),
                    "display_action": _friendly_action(row.get("action_decision", "ALLOW"), lang=lang),
                    "display_intervention_title": row.get("intervention", {}).get("title", ""),
                    "display_intervention_guidance": row.get("intervention", {}).get("guidance", []),
                    "display_approval": (
                        f"{_t(lang, 'required')} ({_t(lang, 'contact_ending')} {row.get('trusted_contact_hint', '')})"
                        if row.get("approval_required")
                        else _t(lang, "not_required")
                    ),
                }
            )

        context = _customer_dashboard_context(request, lang=lang) if _user_ctx(request).get("role") == "customer" else _admin_dashboard_context(request, lang=lang)
        context["transactions"] = formatted
        context["active_user"] = user_id.strip()
        return render_template(request, "transactions.html", context)
    except Exception as exc:
        context = _customer_dashboard_context(request, lang=lang, error=str(exc)) if _user_ctx(request).get("role") == "customer" else _admin_dashboard_context(request, error=str(exc), lang=lang)
        context["transactions"] = []
        context["active_user"] = user_id.strip()
        return render_template(request, "transactions.html", context, status_code=400)


@app.get("/users/list")
def list_users(request: Request, lang: str = "en"):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    init_db(DEFAULT_DB)
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, failed_attempts, last_auth_at, auth_config, created_at
            FROM users
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()
    users = []
    for user_id, failed_attempts, last_auth_at, auth_config, created_at in rows:
        trusted_contact = ""
        freeze_until = ""
        try:
            payload = json.loads(auth_config or "{}")
            trusted_contact = str(payload.get("trusted_contact", ""))
            freeze_until = str(payload.get("freeze_until", ""))
        except Exception:
            trusted_contact = ""
            freeze_until = ""
        users.append(
            {
                "user_id": user_id,
                "failed_attempts": int(failed_attempts or 0),
                "last_auth_at": last_auth_at or "",
                "trusted_contact": trusted_contact,
                "freeze_until": freeze_until,
                "created_at": created_at or "",
            }
        )
    context = _admin_dashboard_context(request, lang=lang)
    context["users"] = users
    return templates.TemplateResponse(request, "users_list.html", context)


@app.get("/transactions/all")
def list_all_transactions(request: Request, lang: str = "en"):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    return list_transactions_by_kind(request, kind="all", lang=lang)


@app.get("/transactions/list/{kind}")
def list_transactions_by_kind(request: Request, kind: str, lang: str = "en"):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    title_key, where_sql, params = _transaction_list_filter(kind)
    rows = _fetch_transaction_rows(where_sql, params)
    items = _format_transaction_rows(rows, lang=lang)
    context = _admin_dashboard_context(request, lang=lang)
    context["transactions"] = items
    context["list_title"] = _bundle(lang).get(title_key, title_key)
    context["list_subtitle"] = _bundle(lang).get("list_subtitle", "")
    context["list_action"] = f"/transactions/list/{kind}"
    return templates.TemplateResponse(request, "transactions_list.html", context)


@app.get("/audit/events")
def list_audit_events(request: Request, lang: str = "en", event_type: str = ""):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    init_db(DEFAULT_DB)
    query = "SELECT created_at, log_id, event_type FROM audit_log"
    params = []
    if event_type:
        query += " WHERE event_type = ?"
        params.append(event_type)
    query += " ORDER BY created_at DESC LIMIT 200"
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
    events = [
        {"created_at": _friendly_time(ts), "log_id": log_id, "event_type": etype}
        for ts, log_id, etype in rows
    ]
    context = _admin_dashboard_context(request, lang=lang)
    context["events"] = events
    base_title = _bundle(lang).get("audit_events_title", "Audit Events")
    context["event_title"] = base_title if not event_type else f"{base_title}: {event_type}"
    return templates.TemplateResponse(request, "audit_events.html", context)


@app.get("/change-log")
def list_change_log(request: Request, lang: str = "en"):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    init_db(DEFAULT_DB)
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT created_at, entity_type, entity_id, field_name, old_value, new_value, actor, source
            FROM change_log
            ORDER BY created_at DESC
            LIMIT 200
            """
        )
        rows = cursor.fetchall()
    entries = [
        {
            "created_at": _friendly_time(ts),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "field_name": field_name,
            "old_value": old_value,
            "new_value": new_value,
            "actor": actor,
            "source": source,
        }
        for ts, entity_type, entity_id, field_name, old_value, new_value, actor, source in rows
    ]
    context = _admin_dashboard_context(request, lang=lang)
    context["entries"] = entries
    return templates.TemplateResponse(request, "change_log.html", context)


@app.post("/sync")
def do_sync(
    request: Request,
    server_url: str = Form(DEFAULT_SERVER_URL),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    try:
        sender = make_http_sender(server_url.strip())
        summary = sync_outbox(db_path=DEFAULT_DB, sender=sender)
        msg = (
            f"{_t(lang, 'sync_completed')}: "
            f"processed={summary.processed}, synced={summary.synced}, "
            f"duplicates={summary.duplicates}, retried={summary.retried}"
        )
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, message=msg, lang=lang))
    except Exception as exc:
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, error=str(exc), lang=lang), status_code=400
        )


@app.get("/sync/queue")
def view_sync_queue(request: Request, lang: str = "en"):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    # Visualize local outbox queue for offline-first demo.
    lang = _resolve_lang(lang)
    rows = _fetch_outbox_rows()
    context = _admin_dashboard_context(request, lang=lang)
    context["rows"] = rows
    context["stats"] = _outbox_stats(rows)
    return templates.TemplateResponse(request, "sync_queue.html", context)


@app.post("/sync/simulate")
def simulate_night_sync(request: Request, lang: str = Form(default="en")):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    # Demo-only action: mark pending outbox entries as synced.
    lang = _resolve_lang(lang)
    init_db(DEFAULT_DB)
    tx_ids: list[str] = []
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tx_id FROM outbox WHERE sync_state IN ('PENDING','RETRYING')"
        )
        tx_ids = [row[0] for row in cursor.fetchall()]
        cursor.execute(
            "UPDATE outbox SET sync_state = 'SYNCED', last_error = NULL, next_retry_at = NULL "
            "WHERE sync_state IN ('PENDING','RETRYING')"
        )
        if tx_ids:
            placeholders = ",".join(["?"] * len(tx_ids))
            cursor.execute(
                f"UPDATE transactions SET status = 'SYNCED' WHERE status = 'PENDING' AND tx_id IN ({placeholders})",
                tx_ids,
            )
        conn.commit()
    rows = _fetch_outbox_rows()
    context = _admin_dashboard_context(request, message=_t(lang, "night_sync_done").format(count=len(tx_ids)), lang=lang)
    context["rows"] = rows
    context["stats"] = _outbox_stats(rows)
    return templates.TemplateResponse(request, "sync_queue.html", context)


@app.get("/audit")
def audit_status(request: Request):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    result = verify_audit_chain(db_path=DEFAULT_DB)
    if result.is_valid:
        msg = f"{_t(lang, 'audit_valid')}. {_t(lang, 'entries_checked')}: {result.checked_entries}"
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, message=msg, lang=lang))

    err = f"{_t(lang, 'audit_invalid')}: {result.error}"
    return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, error=err, lang=lang), status_code=400
    )


@app.get("/reset")
def reset_to_home(request: Request):
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    role = request.cookies.get(ROLE_COOKIE, "")
    if role == "customer":
        return RedirectResponse(url=f"/dashboard/customer?lang={lang}", status_code=303)
    if role in {"admin", "bank"}:
        return RedirectResponse(url=f"/bank/dashboard?lang={lang}", status_code=303)
    return RedirectResponse(url=f"/?lang={lang}", status_code=303)


@app.post("/seed-demo")
def seed_demo_data(request: Request):
    """Insert a realistic demo user + transactions for live presentation."""
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(request.query_params.get("lang", "en"))
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

        msg = _t(lang, "demo_seeded")
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, message=msg, lang=lang))
    except Exception as exc:
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, error=str(exc), lang=lang), status_code=400
        )


@app.get("/export/report")
def export_report(request: Request):
    """Human-friendly security report page."""
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    stats = get_dashboard_stats(db_path=DEFAULT_DB)
    audit = verify_audit_chain(db_path=DEFAULT_DB)
    context = _admin_dashboard_context(request, lang=lang)
    context["report"] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "stats": stats,
        "audit": {
            "is_valid": audit.is_valid,
            "checked_entries": audit.checked_entries,
            "error": audit.error,
        },
    }
    return templates.TemplateResponse(request, "report_snapshot.html", context)


@app.get("/export/report.json")
def export_report_json(request: Request):
    guard = _require_role(request, "bank")
    if guard:
        return guard
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


@app.post("/export/change-log")
def export_change_log(request: Request, lang: str = Form(default="en")):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    init_db(DEFAULT_DB)
    export_dir = Path("data/exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    export_path = export_dir / f"change_log_{timestamp}.csv"

    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT created_at, entity_type, entity_id, field_name, old_value, new_value, actor, source
            FROM change_log
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()

    with export_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "created_at",
                "entity_type",
                "entity_id",
                "field_name",
                "old_value",
                "new_value",
                "actor",
                "source",
            ]
        )
        writer.writerows(rows)

    msg = f"{_t(lang, 'change_log_exported')} {export_path} ({len(rows)} records)."
    return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, message=msg, lang=lang))


@app.get("/report/impact")
def fraud_impact_report(request: Request):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    impact = _load_impact_report_data()
    context = _admin_dashboard_context(request, lang=lang)
    context["impact"] = impact
    return templates.TemplateResponse(request, "impact_report.html", context)


@app.post("/report/impact/seed")
def seed_impact_report(request: Request, lang: str = Form(default="en")):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    seed_user = "impact_demo"
    pin = "1234"
    create_user(
        user_id=seed_user,
        phone_number="+919333333333",
        pin=pin,
        db_path=DEFAULT_DB,
        replace_existing=True,
    )
    scenarios = ["scam_high_amount", "rapid_mule_burst", "account_takeover"]
    for scenario_id in scenarios:
        simulated = _simulate_scenario(scenario_id=scenario_id, user_id=seed_user, pin=pin)
        _record_scenario_run(scenario_id=scenario_id, user_id=seed_user, transactions=simulated)
    msg = "Impact report seeded with demo scenarios."
    context = _admin_dashboard_context(request, message=msg, lang=lang)
    context["impact"] = _load_impact_report_data()
    return templates.TemplateResponse(request, "impact_report.html", context)


@app.get("/demo/walkthrough")
def professor_walkthrough(request: Request):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    demo = _run_professor_walkthrough(lang=lang)
    context = _admin_dashboard_context(request, lang=lang)
    context["demo"] = demo
    return templates.TemplateResponse(request, "demo_walkthrough.html", context)


@app.get("/guide")
def demo_guide(request: Request):
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    context = _ctx(request, lang=lang)
    return templates.TemplateResponse(request, "guide.html", context)


@app.post("/simulate/scenario")
def run_scenario(
    request: Request,
    scenario_id: str = Form(...),
    user_id: str = Form(...),
    pin: str = Form(...),
    trusted_contact: str = Form(default=""),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    try:
        clean_user = user_id.strip()
        clean_pin = pin.strip()
        _ensure_user_for_scenario(user_id=clean_user, pin=clean_pin)

        if trusted_contact.strip():
            set_trusted_contact(
                user_id=clean_user,
                pin=clean_pin,
                trusted_contact=trusted_contact.strip(),
                db_path=DEFAULT_DB,
            )

        simulated = _simulate_scenario(
            scenario_id=scenario_id.strip(),
            user_id=clean_user,
            pin=clean_pin,
        )
        _record_scenario_run(
            scenario_id=scenario_id.strip(),
            user_id=clean_user,
            transactions=simulated,
        )
        summary = _scenario_result_message(scenario_id=scenario_id.strip(), transactions=simulated, lang=lang)
        voice_text = _build_voice_prompt(
            lang=lang,
            risk_level=simulated[-1].risk_level,
            action=simulated[-1].action_decision,
            guidance=list(simulated[-1].intervention_guidance),
        )
        return templates.TemplateResponse(request, "index.html",
            _admin_dashboard_context(request, message=summary, lang=lang, voice_text=voice_text),
        )
    except Exception as exc:
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, error=str(exc), lang=lang), status_code=400
        )


def _language_choices() -> list[dict]:
    return [
        {"code": "en", "label": "English"},
        {"code": "hi", "label": "हिंदी"},
        {"code": "or", "label": "ଓଡ଼ିଆ"},
        {"code": "gu", "label": "ગુજરાતી"},
        {"code": "de", "label": "Deutsch"},
    ]


def _scenario_choices(lang: str) -> list[dict]:
    options = {
        "en": [
            {"id": "scam_high_amount", "label": "Late-night high amount to unknown recipient"},
            {"id": "rapid_mule_burst", "label": "Rapid burst transfers (money mule pattern)"},
            {"id": "account_takeover", "label": "Account takeover after failed logins"},
        ],
        "hi": [
            {"id": "scam_high_amount", "label": "देर रात अज्ञात प्राप्तकर्ता को बड़ी राशि"},
            {"id": "rapid_mule_burst", "label": "तेज़ी से कई ट्रांसफर (मनी म्यूल पैटर्न)"},
            {"id": "account_takeover", "label": "असफल लॉगिन के बाद अकाउंट टेकओवर"},
        ],
        "or": [
            {"id": "scam_high_amount", "label": "ରାତିରେ ଅଜଣା ପ୍ରାପ୍ତକର୍ତ୍ତାଙ୍କୁ ବଡ଼ ରାଶି"},
            {"id": "rapid_mule_burst", "label": "ଦ୍ରୁତ ଅନେକ ଟ୍ରାନ୍ସଫର୍ (ମନି ମ୍ୟୁଲ୍ ପ୍ୟାଟର୍ନ)"},
            {"id": "account_takeover", "label": "ବିଫଳ ଲଗଇନ ପରେ ଆକାଉଣ୍ଟ ଟେକଓଭର୍"},
        ],
        "gu": [
            {"id": "scam_high_amount", "label": "મોડી રાતે અજાણ્યા પ્રાપ્તકર્તાને મોટી રકમ"},
            {"id": "rapid_mule_burst", "label": "ઝડપી ઘણા ટ્રાન્સફર (મની મ્યુલ પેટર્ન)"},
            {"id": "account_takeover", "label": "ઘણા નિષ્ફળ લોગિન પછી અકાઉન્ટ ટેકઓવર"},
        ],
        "de": [
            {"id": "scam_high_amount", "label": "Späte Nacht, hoher Betrag an unbekannten Empfänger"},
            {"id": "rapid_mule_burst", "label": "Schnelle Serienüberweisungen (Money-Mule-Muster)"},
            {"id": "account_takeover", "label": "Kontoübernahme nach fehlgeschlagenen Logins"},
        ],
    }
    return options.get(lang, options["en"])


def _ensure_user_for_scenario(user_id: str, pin: str) -> None:
    try:
        create_user(
            user_id=user_id,
            phone_number=f"+91{abs(hash(user_id)) % 10_000_000_000:010d}",
            pin=pin,
            db_path=DEFAULT_DB,
            replace_existing=False,
        )
    except ValueError as exc:
        if "already exists" not in str(exc).lower():
            raise


def _set_failed_attempts(user_id: str, attempts: int) -> None:
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET failed_attempts = ?, lockout_until = NULL WHERE user_id = ?",
            (attempts, user_id),
        )
        conn.commit()


def _simulate_scenario(scenario_id: str, user_id: str, pin: str):
    now = datetime.now(UTC)
    if scenario_id == "scam_high_amount":
        tx = create_secure_transaction(
            user_id=user_id,
            pin=pin,
            amount=7800.0,
            recipient="Unknown Agent",
            db_path=DEFAULT_DB,
            timestamp=now.replace(hour=23, minute=35, second=0, microsecond=0),
        )
        return [tx]

    if scenario_id == "rapid_mule_burst":
        start = now - timedelta(minutes=6)
        samples = [
            (420.0, "Local Friend A", start),
            (590.0, "Local Friend B", start + timedelta(minutes=2)),
            (640.0, "Local Friend C", start + timedelta(minutes=4)),
            (720.0, "Unknown Mule", start + timedelta(minutes=6)),
        ]
        generated = []
        for amount, recipient, when in samples:
            generated.append(
                create_secure_transaction(
                    user_id=user_id,
                    pin=pin,
                    amount=amount,
                    recipient=recipient,
                    db_path=DEFAULT_DB,
                    timestamp=when,
                )
            )
        return generated

    if scenario_id == "account_takeover":
        _set_failed_attempts(user_id=user_id, attempts=4)
        try:
            tx = create_secure_transaction(
                user_id=user_id,
                pin=pin,
                amount=6500.0,
                recipient="Emergency Receiver",
                db_path=DEFAULT_DB,
                timestamp=now,
            )
            return [tx]
        finally:
            _set_failed_attempts(user_id=user_id, attempts=0)

    raise ValueError("Unknown scenario selected")


def _scenario_result_message(scenario_id: str, transactions: list, lang: str) -> str:
    labels = {item["id"]: item["label"] for item in _scenario_choices(lang="en")}
    scenario_name = labels.get(scenario_id, scenario_id)
    latest = transactions[-1]
    reason_text = ", ".join(_friendly_reason(code, lang=lang) for code in latest.reason_codes) or _t(lang, "no_alert")
    summary = (
        f"{_t(lang, 'scenario_ran')}: {scenario_name}. "
        f"{_t(lang, 'created_count')}: {len(transactions)}. "
        f"{_t(lang, 'risk_label')} {_friendly_risk(latest.risk_level, lang=lang)} ({latest.risk_score}/100). "
        f"{_t(lang, 'decision_label')} {_friendly_action(latest.action_decision, lang=lang)}. "
        f"{_t(lang, 'status_label')} {_friendly_status(latest.status, lang=lang)}. "
        f"{_t(lang, 'reason_label')} {reason_text}."
    )
    if latest.approval_required:
        summary += f" {_t(lang, 'demo_code')}: {latest.approval_code_for_demo}"
    return summary


def _record_scenario_run(scenario_id: str, user_id: str, transactions: list) -> None:
    init_db(DEFAULT_DB)
    high_risk = sum(1 for tx in transactions if tx.risk_level == "HIGH" or tx.risk_score >= 70)
    held = sum(1 for tx in transactions if tx.status in {"HOLD_FOR_REVIEW", "AWAITING_TRUSTED_APPROVAL"})
    blocked = sum(1 for tx in transactions if tx.status.startswith("BLOCKED") or tx.status == "BLOCKED_LOCAL")
    avg_risk = sum(tx.risk_score for tx in transactions) / max(len(transactions), 1)
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO scenario_runs (
                run_id, scenario_id, user_id, tx_created, high_risk_count,
                held_count, blocked_count, avg_risk_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                scenario_id,
                user_id,
                len(transactions),
                high_risk,
                held,
                blocked,
                round(avg_risk, 2),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()


def _load_impact_report_data() -> dict:
    init_db(DEFAULT_DB)
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scenario_runs")
        total_runs = int(cursor.fetchone()[0])

        cursor.execute("SELECT COALESCE(SUM(tx_created), 0) FROM scenario_runs")
        total_txs = int(cursor.fetchone()[0])

        cursor.execute("SELECT COALESCE(SUM(high_risk_count), 0) FROM scenario_runs")
        high_risk_total = int(cursor.fetchone()[0])

        cursor.execute("SELECT COALESCE(SUM(held_count), 0) FROM scenario_runs")
        held_total = int(cursor.fetchone()[0])

        cursor.execute("SELECT COALESCE(SUM(blocked_count), 0) FROM scenario_runs")
        blocked_total = int(cursor.fetchone()[0])

        cursor.execute("SELECT COALESCE(AVG(avg_risk_score), 0) FROM scenario_runs")
        avg_risk = float(cursor.fetchone()[0] or 0.0)

        cursor.execute(
            """
            SELECT scenario_id, COUNT(*), COALESCE(AVG(avg_risk_score), 0),
                   COALESCE(SUM(high_risk_count), 0), COALESCE(SUM(held_count), 0), COALESCE(SUM(blocked_count), 0)
            FROM scenario_runs
            GROUP BY scenario_id
            ORDER BY COUNT(*) DESC
            """
        )
        by_scenario_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT created_at, scenario_id, user_id, tx_created, high_risk_count, held_count, blocked_count, avg_risk_score
            FROM scenario_runs
            ORDER BY created_at DESC
            LIMIT 10
            """
        )
        recent_rows = cursor.fetchall()

    scenario_labels = {item["id"]: item["label"] for item in _scenario_choices("en")}
    by_scenario = [
        {
            "scenario_id": scenario_id,
            "scenario_label": scenario_labels.get(scenario_id, scenario_id),
            "runs": runs,
            "avg_risk": round(float(avg), 2),
            "high_risk": int(high),
            "held": int(held),
            "blocked": int(blocked),
        }
        for scenario_id, runs, avg, high, held, blocked in by_scenario_rows
    ]
    recent_runs = [
        {
            "created_at": _friendly_time(str(created_at)),
            "scenario_id": scenario_id,
            "scenario_label": scenario_labels.get(scenario_id, scenario_id),
            "user_id": user_id,
            "tx_created": tx_created,
            "high_risk": high_risk,
            "held": held,
            "blocked": blocked,
            "avg_risk": round(float(avg_risk_score), 2),
        }
        for created_at, scenario_id, user_id, tx_created, high_risk, held, blocked, avg_risk_score in recent_rows
    ]

    protection_rate = 0.0
    if total_txs > 0:
        protection_rate = round(((held_total + blocked_total) / total_txs) * 100, 2)

    return {
        "total_runs": total_runs,
        "total_txs": total_txs,
        "high_risk_total": high_risk_total,
        "held_total": held_total,
        "blocked_total": blocked_total,
        "avg_risk": round(avg_risk, 2),
        "protection_rate": protection_rate,
        "by_scenario": by_scenario,
        "recent_runs": recent_runs,
    }


def _build_voice_prompt(lang: str, risk_level: str, action: str, guidance: list[str]) -> str:
    headline = {
        "en": f"Security alert. Risk is {_friendly_risk(risk_level, lang)}. Action: {_friendly_action(action, lang)}.",
        "hi": f"सुरक्षा अलर्ट। जोखिम स्तर {_friendly_risk(risk_level, lang)} है। कार्रवाई: {_friendly_action(action, lang)}।",
        "or": f"ସୁରକ୍ଷା ସତର୍କତା। ଝୁମ୍ପ ସ୍ତର {_friendly_risk(risk_level, lang)}। କାର୍ଯ୍ୟ: {_friendly_action(action, lang)}।",
        "gu": f"સુરક્ષા એલર્ટ. જોખમ સ્તર {_friendly_risk(risk_level, lang)} છે. ક્રિયા: {_friendly_action(action, lang)}.",
        "de": f"Sicherheitsalarm. Risiko ist {_friendly_risk(risk_level, lang)}. Aktion: {_friendly_action(action, lang)}.",
    }.get(lang, "")
    return " ".join([headline, *guidance]).strip()


def _transaction_list_filter(kind: str) -> tuple[str, str, list]:
    normalized = (kind or "all").lower()
    if normalized in {"pending", "pending-sync"}:
        return ("list_pending_title", "WHERE status = 'PENDING'", [])
    if normalized == "synced":
        return ("list_synced_title", "WHERE status = 'SYNCED'", [])
    if normalized == "held":
        return (
            "list_held_title",
            "WHERE status IN ('HOLD_FOR_REVIEW','AWAITING_TRUSTED_APPROVAL')",
            [],
        )
    if normalized == "blocked":
        return (
            "list_blocked_title",
            "WHERE status LIKE 'BLOCKED_%' OR status = 'BLOCKED_LOCAL' OR status = 'REJECTED_INTEGRITY_FAIL'",
            [],
        )
    if normalized in {"high-risk", "high_risk"}:
        return (
            "list_high_risk_title",
            "WHERE risk_level = 'HIGH' OR risk_score >= 70",
            [],
        )
    return ("list_all_title", "", [])


def _fetch_transaction_rows(where_sql: str, params: list) -> list[tuple]:
    init_db(DEFAULT_DB)
    query = (
        "SELECT tx_id, user_id, timestamp, risk_score, risk_level, status, action_decision "
        "FROM transactions "
    )
    if where_sql:
        query += f"{where_sql} "
    query += "ORDER BY timestamp DESC LIMIT 200"
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()


def _format_transaction_rows(rows: list[tuple], lang: str) -> list[dict]:
    items = []
    for tx_id, user_id, ts, risk_score, risk_level, status, action_decision in rows:
        items.append(
            {
                "tx_id": tx_id,
                "user_id": user_id,
                "timestamp": ts,
                "display_time": _friendly_time(ts),
                "display_risk": f"{_friendly_risk(risk_level, lang=lang)} ({risk_score}/100)",
                "display_status": _friendly_status(status, lang=lang),
                "display_action": _friendly_action(action_decision or "ALLOW", lang=lang),
            }
        )
    return items


def _load_recent_change_log(limit: int = 5) -> list[dict]:
    init_db(DEFAULT_DB)
    with sqlite3.connect(DEFAULT_DB) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT created_at, entity_type, entity_id, field_name, old_value, new_value
            FROM change_log
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
    return [
        {
            "created_at": _friendly_time(ts),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "field_name": field_name,
            "old_value": old_value,
            "new_value": new_value,
        }
        for ts, entity_type, entity_id, field_name, old_value, new_value in rows
    ]


def _run_professor_walkthrough(lang: str) -> dict:
    user_id = "prof_demo_user"
    pin = "1234"
    create_user(
        user_id=user_id,
        phone_number="+919222222222",
        pin=pin,
        db_path=DEFAULT_DB,
        replace_existing=True,
    )
    set_trusted_contact(
        user_id=user_id,
        pin=pin,
        trusted_contact="+919888888888",
        db_path=DEFAULT_DB,
    )

    step1 = create_secure_transaction(
        user_id=user_id,
        pin=pin,
        amount=420.0,
        recipient="Ration Shop",
        db_path=DEFAULT_DB,
    )
    late_time = datetime.now(UTC).replace(hour=23, minute=40, second=0, microsecond=0)
    step2 = create_secure_transaction(
        user_id=user_id,
        pin=pin,
        amount=7200.0,
        recipient="Unknown Agent",
        db_path=DEFAULT_DB,
        timestamp=late_time,
    )
    enable_panic_freeze(
        user_id=user_id,
        pin=pin,
        minutes=30,
        db_path=DEFAULT_DB,
    )
    step3 = create_secure_transaction(
        user_id=user_id,
        pin=pin,
        amount=900.0,
        recipient="Neighbor Transfer",
        db_path=DEFAULT_DB,
    )

    released = False
    if step2.approval_required and step2.approval_code_for_demo:
        released = release_held_transaction(
            tx_id=step2.tx_id,
            user_id=user_id,
            pin=pin,
            approval_code=step2.approval_code_for_demo,
            db_path=DEFAULT_DB,
        )

    latest = list_secure_transactions(user_id=user_id, pin=pin, db_path=DEFAULT_DB, limit=8)
    status_by_tx = {row["tx_id"]: row["status"] for row in latest}

    i18n = _bundle(lang)
    steps = [
        {
            "title": i18n.get("demo_step_a_title", "Step A"),
            "tx_id": step1.tx_id,
            "risk": f"{_friendly_risk(step1.risk_level, lang)} ({step1.risk_score}/100)",
            "action": _friendly_action(step1.action_decision, lang),
            "status": _friendly_status(status_by_tx.get(step1.tx_id, step1.status), lang),
            "why": ", ".join(_friendly_reason(code, lang) for code in step1.reason_codes) or _t(lang, "no_alert"),
        },
        {
            "title": i18n.get("demo_step_b_title", "Step B"),
            "tx_id": step2.tx_id,
            "risk": f"{_friendly_risk(step2.risk_level, lang)} ({step2.risk_score}/100)",
            "action": _friendly_action(step2.action_decision, lang),
            "status": _friendly_status(status_by_tx.get(step2.tx_id, step2.status), lang),
            "why": ", ".join(_friendly_reason(code, lang) for code in step2.reason_codes) or _t(lang, "no_alert"),
            "approval_code": step2.approval_code_for_demo,
        },
        {
            "title": i18n.get("demo_step_c_title", "Step C"),
            "tx_id": step3.tx_id,
            "risk": f"{_friendly_risk(step3.risk_level, lang)} ({step3.risk_score}/100)",
            "action": _friendly_action(step3.action_decision, lang),
            "status": _friendly_status(status_by_tx.get(step3.tx_id, step3.status), lang),
            "why": ", ".join(_friendly_reason(code, lang) for code in step3.reason_codes) or _t(lang, "no_alert"),
        },
    ]
    return {
        "user_id": user_id,
        "pin": pin,
        "trusted_contact_hint": "8888",
        "steps": steps,
        "released": released,
        "speaking_points": [
            i18n.get("demo_point_1", "Transaction data is encrypted and stored offline first."),
            i18n.get("demo_point_2", "Risk scoring flags suspicious patterns with explainable reasons."),
            i18n.get("demo_point_3", "High-risk flows are held or blocked before sync."),
            i18n.get("demo_point_4", "Trusted-contact approval and panic freeze prevent immediate fraud loss."),
            i18n.get("demo_point_5", "All decisions are visible in local UI for assisted rural operations."),
        ],
    }


@app.post("/transactions/release")
def release_transaction(
    request: Request,
    tx_id: str = Form(...),
    user_id: str = Form(...),
    pin: str = Form(...),
    approval_code: str = Form(default=""),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    try:
        released = release_held_transaction(
            tx_id=tx_id.strip(),
            user_id=user_id.strip(),
            pin=pin.strip(),
            approval_code=approval_code.strip(),
            db_path=DEFAULT_DB,
        )
        if released:
            return templates.TemplateResponse(request, "index.html",
                _admin_dashboard_context(request, message=_t(lang, "release_success"), lang=lang),
            )
        return templates.TemplateResponse(request, "index.html",
            _admin_dashboard_context(request, error=_t(lang, "release_failed"), lang=lang),
            status_code=400,
        )
    except Exception as exc:
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, error=str(exc), lang=lang), status_code=400
        )


@app.get("/transactions/release")
def release_transaction_help(request: Request):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    msg = "Use the Release Held Transaction form on the dashboard."
    return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, message=msg, lang=lang))


@app.post("/users/trusted-contact")
def update_trusted_contact(
    request: Request,
    user_id: str = Form(...),
    pin: str = Form(...),
    trusted_contact: str = Form(...),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    try:
        set_trusted_contact(
            user_id=user_id.strip(),
            pin=pin.strip(),
            trusted_contact=trusted_contact.strip(),
            db_path=DEFAULT_DB,
        )
        return templates.TemplateResponse(request, "index.html",
            _admin_dashboard_context(request, message=f"{_t(lang, 'trusted_updated')} {user_id.strip()}.", lang=lang),
        )
    except Exception as exc:
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, error=str(exc), lang=lang), status_code=400
        )


@app.post("/users/panic-freeze")
def panic_freeze(
    request: Request,
    user_id: str = Form(...),
    pin: str = Form(...),
    minutes: int = Form(60),
    lang: str = Form(default="en"),
):
    guard = _require_role(request, "bank")
    if guard:
        return guard
    lang = _resolve_lang(lang)
    try:
        freeze_until = enable_panic_freeze(
            user_id=user_id.strip(),
            pin=pin.strip(),
            minutes=minutes,
            db_path=DEFAULT_DB,
        )
        return templates.TemplateResponse(request, "index.html",
            _admin_dashboard_context(
                request,
                message=f"{_t(lang, 'freeze_enabled')} {freeze_until} ({user_id.strip()}).",
                lang=lang,
            ),
        )
    except Exception as exc:
        return templates.TemplateResponse(request, "index.html", _admin_dashboard_context(request, error=str(exc), lang=lang), status_code=400
        )


def _friendly_risk(level: str, lang: str = "en") -> str:
    mapping = {
        "en": {"LOW": "Low", "MEDIUM": "Medium", "HIGH": "High"},
        "hi": {"LOW": "कम", "MEDIUM": "मध्यम", "HIGH": "उच्च"},
        "or": {"LOW": "କମ୍", "MEDIUM": "ମଧ୍ୟମ", "HIGH": "ଉଚ୍ଚ"},
        "gu": {"LOW": "ઓછું", "MEDIUM": "મધ્યમ", "HIGH": "ઉચ્ચ"},
        "de": {"LOW": "Niedrig", "MEDIUM": "Mittel", "HIGH": "Hoch"},
    }.get(lang, {})
    return mapping.get(level, level.title())


def _friendly_status(status: str, lang: str = "en") -> str:
    mapping = {
        "en": {
            "PENDING": "Pending Sync",
            "SYNCED": "Synced to Server",
            "SYNCED_DUPLICATE_ACK": "Synced (Duplicate Acknowledged)",
            "RETRYING_SYNC": "Retrying Sync",
            "REJECTED_INTEGRITY_FAIL": "Blocked (Integrity Check Failed)",
            "AWAITING_TRUSTED_APPROVAL": "Awaiting Trusted Approval",
            "HOLD_FOR_REVIEW": "Hold for Review",
            "BLOCKED_PANIC_FREEZE": "Blocked (Panic Freeze Active)",
            "BLOCKED_APPROVAL_EXPIRED": "Blocked (Approval Expired)",
            "BLOCKED_TRUST_CHECK_FAILED": "Blocked (Approval Attempts Exceeded)",
        },
        "hi": {
            "PENDING": "सिंक लंबित",
            "SYNCED": "सर्वर पर सिंक",
            "SYNCED_DUPLICATE_ACK": "सिंक (डुप्लिकेट पुष्टि)",
            "RETRYING_SYNC": "सिंक पुनः प्रयास",
            "REJECTED_INTEGRITY_FAIL": "ब्लॉक (इंटीग्रिटी विफल)",
            "AWAITING_TRUSTED_APPROVAL": "विश्वसनीय स्वीकृति प्रतीक्षा",
            "HOLD_FOR_REVIEW": "समीक्षा हेतु रोक",
            "BLOCKED_PANIC_FREEZE": "ब्लॉक (पैनिक फ्रीज़ सक्रिय)",
            "BLOCKED_APPROVAL_EXPIRED": "ब्लॉक (स्वीकृति समय समाप्त)",
            "BLOCKED_TRUST_CHECK_FAILED": "ब्लॉक (स्वीकृति प्रयास सीमा)",
        },
        "or": {
            "PENDING": "ସିଙ୍କ ବାକୀ",
            "SYNCED": "ସର୍ଭରକୁ ସିଙ୍କ",
            "SYNCED_DUPLICATE_ACK": "ସିଙ୍କ (ଡୁପ୍ଲିକେଟ ସ୍ୱୀକୃତି)",
            "RETRYING_SYNC": "ପୁନଃ ସିଙ୍କ ଚେଷ୍ଟା",
            "REJECTED_INTEGRITY_FAIL": "ବ୍ଲକ୍ (ଅଖଣ୍ଡତା ବିଫଳ)",
            "AWAITING_TRUSTED_APPROVAL": "ଭରସାଯୋଗ୍ୟ ସ୍ୱୀକୃତି ପ୍ରତୀକ୍ଷା",
            "HOLD_FOR_REVIEW": "ସମୀକ୍ଷା ପାଇଁ ରୋକ",
            "BLOCKED_PANIC_FREEZE": "ବ୍ଲକ୍ (ପ୍ୟାନିକ ଫ୍ରିଜ ସକ୍ରିୟ)",
            "BLOCKED_APPROVAL_EXPIRED": "ବ୍ଲକ୍ (ସ୍ୱୀକୃତି ସମୟ ସମାପ୍ତ)",
            "BLOCKED_TRUST_CHECK_FAILED": "ବ୍ଲକ୍ (ସ୍ୱୀକୃତି ଚେଷ୍ଟା ସୀମା)",
        },
        "gu": {
            "PENDING": "સિંક બાકી",
            "SYNCED": "સર્વર પર સિંક",
            "SYNCED_DUPLICATE_ACK": "સિંક (ડુપ્લિકેટ સ્વીકૃતિ)",
            "RETRYING_SYNC": "પુનઃ સિંક પ્રયાસ",
            "REJECTED_INTEGRITY_FAIL": "બ્લોક (ઇન્ટેગ્રિટી નિષ્ફળ)",
            "AWAITING_TRUSTED_APPROVAL": "વિશ્વસનીય મંજૂરી માટે રાહ",
            "HOLD_FOR_REVIEW": "સમિક્ષા માટે રોકો",
            "BLOCKED_PANIC_FREEZE": "બ્લોક (પેનિક ફ્રીઝ સક્રિય)",
            "BLOCKED_APPROVAL_EXPIRED": "બ્લોક (મંજૂરી સમય સમાપ્ત)",
            "BLOCKED_TRUST_CHECK_FAILED": "બ્લોક (મંજૂરી પ્રયાસ મર્યાદા)",
        },
        "de": {
            "PENDING": "Synchronisierung ausstehend",
            "SYNCED": "Mit Server synchronisiert",
            "SYNCED_DUPLICATE_ACK": "Synchronisiert (Duplikat bestätigt)",
            "RETRYING_SYNC": "Synchronisierung erneut",
            "REJECTED_INTEGRITY_FAIL": "Blockiert (Integritätsprüfung fehlgeschlagen)",
            "AWAITING_TRUSTED_APPROVAL": "Warten auf Vertrauensfreigabe",
            "HOLD_FOR_REVIEW": "Zur Prüfung halten",
            "BLOCKED_PANIC_FREEZE": "Blockiert (Panik-Freeze aktiv)",
            "BLOCKED_APPROVAL_EXPIRED": "Blockiert (Freigabe abgelaufen)",
            "BLOCKED_TRUST_CHECK_FAILED": "Blockiert (Freigabeversuche überschritten)",
        },
    }.get(lang, {})
    return mapping.get(status, status.replace("_", " ").title())


def _friendly_reason(code: str, lang: str = "en") -> str:
    mapping = {
        "en": {
            "NEW_RECIPIENT": "New recipient not seen before",
            "HIGH_AMOUNT": "Unusually high amount",
            "ODD_HOUR": "Transaction at unusual hour",
            "RAPID_BURST": "Multiple rapid transactions",
            "AUTH_FAILURES": "Recent failed login attempts",
            "NEW_DEVICE": "New device detected for this account",
        },
        "hi": {
            "NEW_RECIPIENT": "नया प्राप्तकर्ता पहले नहीं देखा गया",
            "HIGH_AMOUNT": "राशि असामान्य रूप से अधिक है",
            "ODD_HOUR": "असामान्य समय पर लेनदेन",
            "RAPID_BURST": "कम समय में कई लेनदेन",
            "AUTH_FAILURES": "हाल में लॉगिन विफल प्रयास",
            "NEW_DEVICE": "इस खाते के लिए नया डिवाइस पाया गया",
        },
        "or": {
            "NEW_RECIPIENT": "ନୂତନ ପ୍ରାପ୍ତକର୍ତ୍ତା ପୂର୍ବରୁ ଦେଖାଯାଇନି",
            "HIGH_AMOUNT": "ରାଶି ଅସାମାନ୍ୟ ଭାବେ ଅଧିକ",
            "ODD_HOUR": "ଅସାମାନ୍ୟ ସମୟରେ ଟ୍ରାନ୍ଜାକ୍ସନ",
            "RAPID_BURST": "କମ୍ ସମୟରେ ଅନେକ ଟ୍ରାନ୍ଜାକ୍ସନ",
            "AUTH_FAILURES": "ସମ୍ପ୍ରତି ଲଗଇନ ବିଫଳ ପ୍ରୟାସ",
            "NEW_DEVICE": "ଏହି ଆକାଉଣ୍ଟ ପାଇଁ ନୂତନ ଡିଭାଇସ ଚିହ୍ନଟ",
        },
        "gu": {
            "NEW_RECIPIENT": "નવો પ્રાપ્તકર્તા અગાઉ જોયેલો નથી",
            "HIGH_AMOUNT": "અસામાન્ય રીતે વધારે રકમ",
            "ODD_HOUR": "અસામાન્ય સમયે ટ્રાન્ઝેક્શન",
            "RAPID_BURST": "ઓછા સમયમાં ઘણા ટ્રાન્ઝેક્શન",
            "AUTH_FAILURES": "તાજેતરના લોગિન નિષ્ફળ પ્રયાસો",
            "NEW_DEVICE": "આ ખાતા માટે નવું ડિવાઇસ મળ્યું",
        },
        "de": {
            "NEW_RECIPIENT": "Neuer Empfänger bisher unbekannt",
            "HIGH_AMOUNT": "Ungewöhnlich hoher Betrag",
            "ODD_HOUR": "Transaktion zu ungewöhnlicher Uhrzeit",
            "RAPID_BURST": "Viele schnelle Transaktionen",
            "AUTH_FAILURES": "Letzte fehlgeschlagene Logins",
            "NEW_DEVICE": "Neues Gerät für dieses Konto erkannt",
        },
    }.get(lang, {})
    return mapping.get(code, code.replace("_", " ").title())


def _friendly_time(iso_ts: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_ts)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return iso_ts


def _friendly_action(action: str, lang: str = "en") -> str:
    mapping = {
        "en": {
            "ALLOW": "Allow",
            "STEP_UP": "Step-up Verification",
            "HOLD": "Hold for Review",
            "BLOCK": "Block for Protection",
        },
        "hi": {
            "ALLOW": "अनुमति",
            "STEP_UP": "अतिरिक्त सत्यापन",
            "HOLD": "समीक्षा हेतु रोक",
            "BLOCK": "सुरक्षा हेतु ब्लॉक",
        },
        "or": {
            "ALLOW": "ଅନୁମତି",
            "STEP_UP": "ଅତିରିକ୍ତ ସତ୍ୟାପନ",
            "HOLD": "ସମୀକ୍ଷା ପାଇଁ ରୋକ",
            "BLOCK": "ସୁରକ୍ଷା ପାଇଁ ବ୍ଲକ୍",
        },
        "gu": {
            "ALLOW": "મંજૂરી",
            "STEP_UP": "વધારાની ચકાસણી",
            "HOLD": "સમિક્ષા માટે રોકો",
            "BLOCK": "સુરક્ષા માટે બ્લોક",
        },
        "de": {
            "ALLOW": "Zulassen",
            "STEP_UP": "Zusatzprüfung",
            "HOLD": "Zur Prüfung halten",
            "BLOCK": "Zum Schutz blockieren",
        },
    }.get(lang, {})
    return mapping.get(action, action.replace("_", " ").title())


def _safe_parse_reason_codes(raw: str | None) -> list[str]:
    # Local helper for UI-only displays (mini statement / alerts).
    if not raw:
        return []
    if isinstance(raw, dict):
        try:
            codes = raw.get("reason_codes", [])
            if isinstance(codes, list):
                return [str(x) for x in codes]
        except Exception:
            return []
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            codes = payload.get("reason_codes", [])
            if isinstance(codes, list):
                return [str(x) for x in codes]
        if isinstance(payload, list):
            return [str(x) for x in payload]
    except Exception:
        return []
    return []


def _resolve_lang(lang: str) -> str:
    cleaned = (lang or "en").strip().lower()
    return cleaned if cleaned in SUPPORTED_LANGS else "en"


def _bundle(lang: str) -> dict:
    bundles = {
        "en": {
            "lang_label": "Language",
            "language_label": "Language",
            "title": "RuralShield",
            "subtitle": "Offline-First Security Prototype for Rural Digital Banking",
            "page_title_login": "Login - RuralShield",
            "page_title_customer_dashboard": "Customer Portal - RuralShield",
            "page_title_customer_history": "Transaction History - RuralShield",
            "page_title_error": "Error - RuralShield",
            "page_title_dashboard": "RuralShield Demo",
            "page_title_users": "User List - RuralShield",
            "page_title_transactions": "Transactions - RuralShield",
            "page_title_transaction_list": "Transaction List - RuralShield",
            "page_title_change_log": "Change Log - RuralShield",
            "page_title_report": "Security Report - RuralShield",
            "page_title_impact": "Fraud Impact Report - RuralShield",
            "page_title_demo_guide": "Demo Guide - RuralShield",
            "page_title_demo_walkthrough": "Professor Demo Walkthrough - RuralShield",
            "page_title_agent": "Agent Mode - RuralShield",
            "page_title_audit": "Audit Events - RuralShield",
            "page_title_sync_queue": "Sync Queue - RuralShield",
            "login_eyebrow": "Secure Entry",
            "login_title": "Choose Your Secure Portal",
            "login_subtitle": "Separate customer banking actions from bank-side fraud monitoring and controls.",
            "customer_portal_eyebrow": "Customer Portal",
            "customer_portal_title": "Customer Banking Portal",
            "customer_portal_subtitle": "Login with your user ID, PIN, and a face verification check.",
            "customer_register_title": "Customer Registration",
            "customer_register_subtitle": "Create your local account offline, then enroll face + device for safer banking.",
            "customer_welcome": "Logged in as",
            "customer_tx_title": "Create Secure Transaction",
            "customer_safety_title": "Safety Controls",
            "customer_history_title": "Personal Transaction History",
            # Customer home (after-midsem customer portal)
            "cust_account_overview": "Account Overview",
            "cust_balance_demo_label": "Balance (Demo)",
            "cust_offline_first_note": "Offline-first: transactions are stored safely on your phone first and synced later when internet is available.",
            "cust_quick_actions": "Quick Actions",
            "cust_send_money": "Send Money",
            "cust_view_transactions": "View Transactions",
            "cust_safety_settings": "Safety Settings",
            "cust_alerts": "Alerts",
            "cust_notifications": "Notifications",
            "cust_no_notifications": "No notifications yet.",
            "cust_alert_new_device_title": "New device detected:",
            "cust_alert_new_device_body": "Some transactions may be held for review.",
            "cust_alert_held_title": "Transactions held:",
            "cust_alert_held_body": "{count} transaction(s) are waiting for review or trusted contact approval.",
            "cust_alert_pending_title": "Pending sync:",
            "cust_alert_pending_body": "{count} transaction(s) will sync when internet is available.",
            "cust_alert_clear_title": "All clear:",
            "cust_alert_clear_body": "No urgent security alerts right now.",
            "cust_mini_statement": "Mini Statement (Last 5)",
            "cust_mini_statement_note": "Privacy-first: amounts and recipients stay encrypted unless you unlock details with PIN.",
            "cust_no_transactions": "No transactions yet.",
            "cust_sync_status": "Sync Status",
            "cust_last_sync": "Last Sync",
            "cust_offline_mode": "Working Offline: transactions will be queued and synced later.",
            "cust_send_money_offline": "Send Money (Offline-First)",
            "cust_send_result_note": "Result will show: Allowed, Held (under review), or Blocked (suspicious).",
            "cust_tx_history": "Transaction History",
            "cust_history_privacy_note": "For privacy, enter PIN to view decrypted history.",
            "cust_open_history": "Open Transaction History",
            "cust_history_pin_note": "PIN is required to decrypt amounts and recipients.",
            "cust_unlock_history": "Unlock Your History",
            "cust_view_history": "View History",
            "cust_history_table_title": "Decrypted Transactions",
            "cust_use_history": "Use Customer History to view your transactions.",
            "cust_risk_safe": "Safe",
            "cust_risk_warning": "Warning",
            "cust_user_risk_score": "User Risk",
            "cust_avg_amount": "Avg Amount",
            "cust_preferred_hours": "Preferred Hours",
            "cust_details": "Details",
            "cust_view": "View",
            "cust_tx_details": "Transaction Details",
            "cust_unlock": "Unlock Details",
            "cust_enter_pin_to_view": "Enter your PIN to view the decrypted amount and recipient.",
            "cust_why_title": "Why this status",
            "admin_portal_eyebrow": "Bank/Admin Portal",
            "admin_portal_title": "Bank/Admin Security Portal",
            "admin_portal_subtitle": "Central controls for fraud review, sync monitoring, and audit visibility.",
            "customer_login_cta": "Enter Customer Portal",
            "admin_login_cta": "Enter Admin Portal",
            "customer_register_cta": "Create Account",
            "customer_register_link": "New here? Create an offline account",
            "login_credentials_title": "Login Credentials",
            "login_credentials_body": "Enter your secure credentials first, then complete the face capture on the right.",
            "admin_username": "Admin username",
            "admin_password": "Admin password",
            "face_verified_label": "Face verified",
            "device_trust_label": "Device trust",
            "device_trusted": "Trusted",
            "device_untrusted": "New device",
            "face_placeholder_title": "Live Face Capture Security Step",
            "face_placeholder_body": "This login flow now requires a real webcam capture before entry. The image is stored locally on the device for demo traceability and can later be replaced by full biometric matching.",
            "face_capture_title": "Capture Face Before Login",
            "face_capture_body": "Start the camera, look at the screen, and capture a photo to continue.",
            "face_start": "Start Camera",
            "face_capture": "Capture Face",
            "face_not_captured": "No face captured yet.",
            "face_camera_ready": "Camera is ready. Capture the face to continue.",
            "face_camera_error": "Camera access failed. Please allow camera permission and try again.",
            "face_camera_wait": "Camera is loading. Please wait a moment and try again.",
            "face_captured_ok": "Face captured successfully. You can now log in.",
            "face_mismatch": "Face verification failed. Please try again in good lighting and face the camera.",
            "device_required": "Device verification is required. Please refresh and try again.",
            "login_switch_title": "Portal Access",
            "login_switch_body": "Use separate links for the customer and bank/admin sides of the system.",
            "customer_scope_error": "Customer portal can only open the logged-in user's transaction history.",
            "cust_safety_settings_title": "Safety Settings",
            "cust_trusted_current": "Trusted contact:",
            "cust_freeze_until": "Freeze until:",
            "back_to_dashboard": "Back to Dashboard",
            "back_to_home": "Back to Home",
            "logout": "Logout",
            # Admin portal (local analytics)
            "admin_overview_title": "Admin Overview (Local Offline Data)",
            "admin_overview_hint": "These panels are computed from the offline SQLite store (works even with no internet).",
            "admin_allowed": "Allowed",
            "admin_risk_distribution": "Risk Distribution Summary",
            "admin_risk_distribution_hint": "How many users currently fall into low/medium/high risk buckets (based on behavior + past transactions).",
            "admin_top_fraud_reasons": "Top Fraud Reasons",
            "admin_top_fraud_reasons_hint": "Most common explainable reasons produced by the fraud engine.",
            "admin_no_top_reasons": "No fraud reasons recorded yet.",
            "admin_fraud_trends": "Fraud Trends (Local)",
            "admin_fraud_trends_hint": "Daily alerts and high-risk transactions, plus the most common alert types.",
            "admin_day": "Day",
            "admin_alerts": "Alerts",
            "admin_high_risk_txs": "High-Risk Tx",
            "admin_top_types": "Top Types",
            "admin_no_trends": "No trend data yet.",
            "admin_high_risk_users": "High-Risk Users",
            "admin_user": "User",
            "admin_user_risk": "User Risk",
            "admin_last_activity": "Last Activity",
            "admin_tx_count": "Tx Count",
            "admin_avg_amount": "Avg Amount",
            "admin_no_high_risk_users": "No high-risk users yet.",
            "admin_user_controls": "User Controls",
            "admin_freeze_60": "Freeze 60m",
            "admin_unfreeze": "Unfreeze",
            "admin_suspicious_alerts": "Suspicious Pattern Alerts",
            "admin_alert_type": "Alert Type",
            "admin_severity": "Severity",
            "admin_message": "Message",
            "admin_no_alerts": "No alerts yet.",
            "admin_device_monitoring": "Device Monitoring",
            "admin_device_id": "Device ID",
            "admin_trusted": "Trusted",
            "admin_first_seen": "First Seen",
            "admin_last_seen": "Last Seen",
            "admin_seen_count": "Seen",
            "admin_no_devices": "No devices recorded yet.",
            "admin_notifications": "Admin Notifications",
            "admin_no_notifications": "No admin notifications yet.",
            "admin_transaction_monitoring": "Transaction Monitoring (Local)",
            "admin_view_all": "View All",
            "admin_tx_note": "Amounts/recipients are shown from the local change-log (demo visibility). Encrypted storage remains in the transactions table.",
            "admin_no_transactions": "No transactions yet.",
            "admin_approve": "Approve",
            "admin_reject": "Reject",
            "error_title": "Something went wrong",
            "error_subtitle": "The portal hit an unexpected error. Use the links below to continue.",
            "error_hint": "If this repeats, restart the server and re-open the Customer Portal from Home.",
            "nav_monitoring": "Monitoring",
            "nav_operations": "Operations",
            "nav_admin": "Administration",
            "nav_tools": "Tools",
            # Admin dashboard navigation (cleaner IA for first-time users)
            "nav_overview": "Overview",
            "nav_transactions": "Transactions",
            "nav_users": "Users",
            "nav_alerts": "Alerts",
            "nav_devices": "Devices",
            "nav_reports": "Reports",
            "nav_utilities": "Utilities",
            "utilities_hint": "Sync, audit trail, and demo utilities. In a real deployment these are staff-only tools.",
            "admin_advanced_tools": "Demo Utilities (Optional)",
            "admin_advanced_tools_hint": "Use these only for demo seeding/testing. They modify local SQLite data.",
            "server_ops_title": "Central Server View (PostgreSQL) (Optional)",
            "server_ops_hint": "If the central server is running, this section shows the live Postgres view using JWT + RBAC. It is optional for offline-first demos.",
            "server_ops_legacy_inbox": "Legacy Inbox",
            "server_ops_sync_queue": "Sync Queue",
            "server_ops_sync_logs": "Sync Logs",
            "server_ops_no_server_txs": "No server transactions yet. Use the customer portal to create some.",
            "server_ops_fraud_logs": "Fraud Logs (Explainable)",
            "server_ops_no_fraud_logs": "No fraud logs yet.",
            "server_ops_not_connected": "Server view not connected. Start the Server API at",
            "help_button": "How to Use",
            "help_title": "Admin Demo Guide (Quick)",
            "help_intro": "This dashboard is designed for rural banking security monitoring. It works offline using local SQLite and can also sync with the central server when internet is available.",
            "help_steps_title": "Recommended demo flow",
            "help_step_1": "Start at Overview: show risk distribution and top fraud reasons (explainable engine).",
            "help_step_2": "Open Transactions: filter HELD and approve/reject one held transaction.",
            "help_step_3": "Open Users: highlight behavior profiling (avg amount, tx count) and freeze/unfreeze a user.",
            "help_step_4": "Open Alerts: show suspicious pattern alerts (rapid transactions / failed logins / repeated high risk).",
            "help_step_5": "Open Devices: show trusted vs untrusted devices (device binding).",
            "help_note": "Tip: if data looks empty, use Utilities > Demo Utilities to seed demo data.",
            "help_open_full": "Open Full Guide",
            "help_close": "Close",
            "users": "Users",
            "transactions": "Transactions",
            "pending_sync": "Pending Sync",
            "synced": "Synced",
            "held": "Held",
            "blocked": "Blocked",
            "released": "Released",
            "high_risk": "High Risk",
            "risk_low": "Low",
            "risk_medium": "Medium",
            "risk_high": "High",
            "audit_events": "Audit Events",
            "audit_events_title": "Audit Events",
            "sync_queue_title": "Offline Sync Queue",
            "sync_queue_subtitle": "Pending local transactions waiting for night sync",
            "section_1": "1. Register / Replace User",
            "section_2": "2. Create Secure Transaction",
            "section_3": "3. View Transactions",
            "section_4": "4. Sync and Audit",
            "section_5": "5. Fraud Scenario Simulator",
            "agent_title": "Agent/Kiosk Assisted Mode",
            "agent_subtitle": "Single-screen assisted transaction flow for business correspondents",
            "agent_user": "User ID",
            "agent_phone": "Phone number",
            "agent_pin": "PIN",
            "agent_amount": "Amount",
            "agent_recipient": "Recipient",
            "agent_trusted": "Trusted contact (optional)",
            "agent_submit": "Run Secure Assisted Transaction",
            "agent_result": "Assisted Transaction Result",
            "voice_play": "Read Safety Guidance Aloud",
            "report_title": "Fraud Impact Report",
            "report_subtitle": "Measured simulator outcomes for anti-fraud controls",
            "report_runs": "Scenario Runs",
            "report_txs": "Simulated Transactions",
            "report_protection": "Protection Rate",
            "report_avg_risk": "Average Risk Score",
            "report_recent": "Recent Simulation Runs",
            "report_breakdown": "Scenario Breakdown",
            "scenario_user": "Simulation User ID",
            "scenario_pin": "Simulation PIN",
            "scenario_contact": "Trusted Contact (optional)",
            "scenario_choice": "Scenario",
            "run_scenario_btn": "Run Scenario",
            "save_user": "Save User",
            "set_trusted": "Set Trusted Contact",
            "enable_freeze": "Enable Panic Freeze",
            "create_tx": "Create Transaction",
            "open_tx_list": "Open Transaction List",
            "sync_pending": "Sync Pending Transactions",
            "release_held": "Release Held Transaction",
            "check_audit": "Check Audit Integrity",
            "seed_demo": "Seed Demo Data",
            "export_report": "Export Security Report",
            "export_change_log": "Export Change Log (CSV)",
            "agent_mode": "Open Agent/Kiosk Mode",
            "impact_report": "Fraud Impact Report",
            "demo_walkthrough": "Run Professor Demo Walkthrough",
            "demo_guide": "Demo Guide",
            "clear_messages": "Clear Messages",
            "sync_queue_open": "Open Sync Queue",
            "more_tools": "More Tools",
            "replace_user": "Replace existing user",
            "ph_user_id_example": "User ID (e.g., u1)",
            "ph_phone_example": "Phone (e.g., +919999999999)",
            "ph_pin_4digit": "4-digit PIN",
            "ph_user_id_trusted": "User ID for trusted contact",
            "ph_pin": "PIN",
            "ph_trusted_contact": "Trusted contact phone or ID",
            "ph_user_id_freeze": "User ID for panic freeze",
            "ph_freeze_minutes": "Freeze minutes",
            "ph_user_id": "User ID",
            "ph_amount": "Amount",
            "ph_recipient_name": "Recipient name",
            "ph_limit": "Limit",
            "ph_server_url": DEFAULT_SERVER_URL,
            "ph_held_tx_id": "Held Transaction ID",
            "ph_approval_code": "Trusted approval code (if required)",
            "tx_list_title": "Transaction List",
            "user_label": "User",
            "time": "Time",
            "tx_id": "Tx ID",
            "amount": "Amount",
            "recipient": "Recipient",
            "risk": "Risk",
            "action": "Action",
            "reasons": "Reasons",
            "guidance": "Guidance",
            "approval": "Approval",
            "status": "Status",
            "back_dashboard": "Back to Dashboard",
            "retrying": "Retrying",
            "sync_state": "Sync State",
            "retry_count": "Retry Count",
            "next_retry": "Next Retry",
            "last_error": "Last Error",
            "outbox_id": "Outbox ID",
            "simulate_night_sync": "Simulate Night Sync",
            "failed_attempts": "Failed Attempts",
            "last_auth": "Last Auth",
            "trusted_contact": "Trusted Contact",
            "freeze_until": "Freeze Until",
            "created_at": "Created At",
            "required": "Required",
            "demo_code": "Demo approval code",
            "how_read_title": "How To Read This",
            "how_read_pending": "Pending Sync means safely stored locally and waiting for server sync.",
            "how_read_blocked": "Blocked means risk policy prevented this transaction.",
            "how_read_risk": "Risk and action explain what safety step is required.",
            "recent_change_log": "Recent Change Log",
            "change_entity": "Entity",
            "change_field": "Field",
            "change_old": "Old",
            "change_new": "New",
            "change_log_full": "Open Full Change Log",
            "list_all_title": "All Transactions",
            "list_pending_title": "Pending Sync Transactions",
            "list_synced_title": "Synced Transactions",
            "list_held_title": "Held Transactions",
            "list_blocked_title": "Blocked Transactions",
            "list_high_risk_title": "High Risk Transactions",
            "list_subtitle": "Local transaction metadata (amounts encrypted)",
            "users_list_title": "User List",
            "transactions_meta_note": "Amounts and recipients are encrypted locally and only visible via user PIN.",
            "audit_events_subtitle": "Append-only audit chain log",
            "audit_event_type": "Event Type",
            "audit_log_id": "Log ID",
            "change_log_title": "Change Log",
            "change_log_subtitle": "Local edits with old/new values",
            "change_actor": "Actor",
            "change_source": "Source",
            "report_snapshot_title": "Security Report",
            "report_snapshot_subtitle": "Local snapshot with audit integrity",
            "report_generated_at": "Generated At",
            "report_audit_valid": "Audit Valid",
            "report_entries_checked": "Entries Checked",
            "report_audit_error": "Audit Error",
            "report_download_json": "Download JSON",
            "report_no_data": "No simulator data yet. Click below to seed demo scenarios.",
            "report_seed_demo": "Seed Impact Demo",
            "demo_walkthrough_title": "Professor Demo Walkthrough",
            "demo_walkthrough_subtitle": "Deterministic end-to-end story for presentation",
            "demo_user_id": "User ID",
            "demo_pin": "PIN",
            "demo_trusted_hint": "Trusted contact hint",
            "demo_release_done": "Trusted release completed",
            "demo_yes": "Yes",
            "demo_no": "No",
            "demo_script_title": "What To Say (Quick Script)",
            "demo_step_a_title": "Step A: Normal low-risk payment",
            "demo_step_b_title": "Step B: Scam-like transfer to unknown receiver",
            "demo_step_c_title": "Step C: Panic freeze blocks outgoing transfer",
            "demo_point_1": "Transaction data is encrypted and stored offline first.",
            "demo_point_2": "Risk scoring flags suspicious patterns with explainable reasons.",
            "demo_point_3": "High-risk flows are held or blocked before sync.",
            "demo_point_4": "Trusted-contact approval and panic freeze prevent immediate fraud loss.",
            "demo_point_5": "All decisions are visible in local UI for assisted rural operations.",
            "demo_guide_title": "Demo Guide",
            "demo_guide_subtitle": "Everything you need to explain the portal clearly",
            "demo_about_title": "What This Portal Is",
            "demo_about_body": "RuralShield is an offline-first cybersecurity framework for rural digital banking. It keeps data safe on-device, detects risky patterns locally, and syncs securely when network is available.",
            "demo_features_title": "Core Features",
            "demo_feature_1": "Encrypted local storage (SQLite) for users and transactions.",
            "demo_feature_2": "Fraud risk scoring with explainable reasons.",
            "demo_feature_3": "Safety interventions: allow, step-up, hold, or block.",
            "demo_feature_4": "Trusted-contact approvals for risky transfers.",
            "demo_feature_5": "Panic freeze to block outgoing transfers during suspected fraud.",
            "demo_feature_6": "Audit chain for tamper evidence.",
            "demo_feature_7": "Offline outbox + secure sync.",
            "demo_steps_title": "How To Demo (Quick Steps)",
            "demo_step_1": "Seed demo data from the dashboard if needed.",
            "demo_step_2": "Create a normal transaction to show low-risk flow.",
            "demo_step_3": "Create a high-amount new-recipient transaction to show hold/block.",
            "demo_step_4": "Use Release Held Transaction with trusted approval code.",
            "demo_step_5": "Open Fraud Impact Report to show simulator metrics.",
            "demo_step_6": "Open Professor Walkthrough for scripted demo.",
            "demo_data_title": "Where Data Is Stored",
            "demo_data_1": "Primary storage: local SQLite database.",
            "demo_data_2": "Change log: old/new values stored locally and exportable to CSV.",
            "demo_data_3": "Sync happens later when network is safe.",
            "demo_pages_title": "Pages You Can Open",
            "demo_page_1": "Dashboard: main actions and statistics.",
            "demo_page_2": "Agent/Kiosk Mode: single assisted workflow.",
            "demo_page_3": "Fraud Impact Report: simulator outcomes.",
            "demo_page_4": "Professor Walkthrough: scripted demo story.",
            "demo_page_5": "Change Log: old/new values for edits.",
        },
        "hi": {
            "lang_label": "भाषा",
            "language_label": "भाषा",
            "title": "RuralShield",
            "subtitle": "ग्रामीण डिजिटल बैंकिंग के लिए ऑफलाइन-प्रथम सुरक्षा प्रोटोटाइप",
            "page_title_customer_dashboard": "ग्राहक पोर्टल - RuralShield",
            "page_title_customer_history": "लेन-देन इतिहास - RuralShield",
            "cust_open_history": "लेन-देन इतिहास खोलें",
            "cust_history_pin_note": "राशि और प्राप्तकर्ता देखने के लिए PIN आवश्यक है।",
            "cust_unlock_history": "इतिहास अनलॉक करें",
            "cust_view_history": "इतिहास देखें",
            "cust_history_table_title": "डिक्रिप्टेड लेन-देन",
            "cust_use_history": "अपने लेन-देन देखने के लिए Customer History उपयोग करें।",
            "cust_safety_settings_title": "सुरक्षा सेटिंग्स",
            "cust_trusted_current": "विश्वसनीय संपर्क:",
            "cust_freeze_until": "फ्रीज़ तक:",
            "back_to_dashboard": "डैशबोर्ड पर वापस",
            "page_title_dashboard": "RuralShield डेमो",
            "page_title_users": "उपयोगकर्ता सूची - RuralShield",
            "page_title_transactions": "लेनदेन - RuralShield",
            "page_title_transaction_list": "लेनदेन सूची - RuralShield",
            "page_title_change_log": "चेंज लॉग - RuralShield",
            "page_title_report": "सुरक्षा रिपोर्ट - RuralShield",
            "page_title_impact": "फ्रॉड प्रभाव रिपोर्ट - RuralShield",
            "page_title_demo_guide": "डेमो गाइड - RuralShield",
            "page_title_demo_walkthrough": "प्रोफेसर डेमो वॉकथ्रू - RuralShield",
            "page_title_agent": "एजेंट मोड - RuralShield",
            "page_title_audit": "ऑडिट इवेंट्स - RuralShield",
            "page_title_sync_queue": "सिंक कतार - RuralShield",
            "users": "उपयोगकर्ता",
            "transactions": "लेनदेन",
            "pending_sync": "सिंक लंबित",
            "synced": "सिंक पूर्ण",
            "held": "रुके हुए",
            "blocked": "ब्लॉक",
            "released": "रिलीज़",
            "high_risk": "उच्च जोखिम",
            "audit_events": "ऑडिट घटनाएँ",
            "section_1": "1. उपयोगकर्ता पंजीकरण / अपडेट",
            "section_2": "2. सुरक्षित लेनदेन बनाएं",
            "section_3": "3. लेनदेन सूची देखें",
            "section_4": "4. सिंक और ऑडिट",
            "section_5": "5. फ्रॉड सीनारियो सिम्युलेटर",
            "agent_title": "एजेंट/कियोस्क असिस्टेड मोड",
            "agent_subtitle": "बिजनेस कॉरेस्पॉन्डेंट के लिए एक-स्क्रीन सुरक्षित लेनदेन प्रवाह",
            "agent_user": "उपयोगकर्ता ID",
            "agent_phone": "फोन नंबर",
            "agent_pin": "PIN",
            "agent_amount": "राशि",
            "agent_recipient": "प्राप्तकर्ता",
            "agent_trusted": "विश्वसनीय संपर्क (वैकल्पिक)",
            "agent_submit": "सुरक्षित असिस्टेड लेनदेन चलाएं",
            "agent_result": "असिस्टेड लेनदेन परिणाम",
            "voice_play": "सुरक्षा सलाह आवाज़ में चलाएं",
            "report_title": "फ्रॉड प्रभाव रिपोर्ट",
            "report_subtitle": "एंटी-फ्रॉड नियंत्रणों के मापे गए सिम्युलेशन परिणाम",
            "report_runs": "सीनारियो रन",
            "report_txs": "सिम्युलेटेड लेनदेन",
            "report_protection": "प्रोटेक्शन रेट",
            "report_avg_risk": "औसत जोखिम स्कोर",
            "report_recent": "हाल के सिम्युलेशन रन",
            "report_breakdown": "सीनारियो ब्रेकडाउन",
            "scenario_user": "सिम्युलेशन उपयोगकर्ता ID",
            "scenario_pin": "सिम्युलेशन PIN",
            "scenario_contact": "विश्वसनीय संपर्क (वैकल्पिक)",
            "scenario_choice": "सीनारियो",
            "run_scenario_btn": "सीनारियो चलाएं",
            "save_user": "उपयोगकर्ता सहेजें",
            "set_trusted": "विश्वसनीय संपर्क सेट करें",
            "enable_freeze": "पैनिक फ्रीज़ चालू करें",
            "create_tx": "लेनदेन बनाएं",
            "open_tx_list": "लेनदेन सूची खोलें",
            "sync_pending": "लंबित लेनदेन सिंक करें",
            "release_held": "रुका हुआ लेनदेन रिलीज़ करें",
            "check_audit": "ऑडिट अखंडता जांचें",
            "seed_demo": "डेमो डेटा बनाएं",
            "export_report": "सुरक्षा रिपोर्ट निर्यात करें",
            "export_change_log": "चेंज लॉग निर्यात करें (CSV)",
            "agent_mode": "एजेंट/कियोस्क मोड खोलें",
            "impact_report": "फ्रॉड प्रभाव रिपोर्ट",
            "demo_walkthrough": "प्रोफेसर डेमो वॉकथ्रू चलाएं",
            "demo_guide": "डेमो गाइड",
            "clear_messages": "संदेश साफ करें",
            "sync_queue_open": "सिंक कतार खोलें",
            "more_tools": "और टूल्स",
            "replace_user": "मौजूदा उपयोगकर्ता बदलें",
            "ph_user_id_example": "उपयोगकर्ता ID (जैसे, u1)",
            "ph_phone_example": "फोन (जैसे, +919999999999)",
            "ph_pin_4digit": "4-अंकों का PIN",
            "ph_user_id_trusted": "विश्वसनीय संपर्क के लिए उपयोगकर्ता ID",
            "ph_pin": "PIN",
            "ph_trusted_contact": "विश्वसनीय संपर्क फोन या ID",
            "ph_user_id_freeze": "पैनिक फ्रीज़ के लिए उपयोगकर्ता ID",
            "ph_freeze_minutes": "फ्रीज़ मिनट",
            "ph_user_id": "उपयोगकर्ता ID",
            "ph_amount": "राशि",
            "ph_recipient_name": "प्राप्तकर्ता का नाम",
            "ph_limit": "सीमा",
            "ph_server_url": DEFAULT_SERVER_URL,
            "ph_held_tx_id": "रुका हुआ ट्रांजैक्शन ID",
            "ph_approval_code": "विश्वसनीय स्वीकृति कोड (यदि आवश्यक)",
            "tx_list_title": "लेनदेन सूची",
            "user_label": "उपयोगकर्ता",
            "time": "समय",
            "tx_id": "ट्रांजैक्शन ID",
            "amount": "राशि",
            "recipient": "प्राप्तकर्ता",
            "risk": "रिस्क",
            "action": "कार्रवाई",
            "reasons": "कारण",
            "guidance": "सलाह",
            "approval": "स्वीकृति",
            "status": "स्थिति",
            "back_dashboard": "डैशबोर्ड पर वापस",
            "retrying": "पुनः प्रयास",
            "sync_state": "सिंक स्थिति",
            "retry_count": "रीट्राई संख्या",
            "next_retry": "अगला रीट्राई",
            "last_error": "अंतिम त्रुटि",
            "outbox_id": "आउटबॉक्स ID",
            "simulate_night_sync": "नाइट सिंक सिम्युलेट करें",
            "failed_attempts": "विफल प्रयास",
            "last_auth": "अंतिम प्रमाणीकरण",
            "trusted_contact": "विश्वसनीय संपर्क",
            "freeze_until": "फ्रीज़ तक",
            "created_at": "निर्मित समय",
            "required": "आवश्यक",
            "demo_code": "डेमो स्वीकृति कोड",
            "how_read_title": "इसे कैसे पढ़ें",
            "how_read_pending": "सिंक लंबित का अर्थ है डेटा सुरक्षित रूप से लोकल में है और सर्वर सिंक का इंतजार कर रहा है।",
            "how_read_blocked": "ब्लॉक का अर्थ है जोखिम नीति ने इस लेनदेन को रोका।",
            "how_read_risk": "रिस्क और एक्शन बताते हैं कि कौन सा सुरक्षा कदम जरूरी है।",
            "recent_change_log": "हालिया चेंज लॉग",
            "change_entity": "एंटिटी",
            "change_field": "फ़ील्ड",
            "change_old": "पुराना",
            "change_new": "नया",
            "change_log_full": "पूरा चेंज लॉग खोलें",
            "list_all_title": "सभी लेनदेन",
            "list_pending_title": "सिंक लंबित लेनदेन",
            "list_synced_title": "सिंक किए गए लेनदेन",
            "list_held_title": "रुके हुए लेनदेन",
            "list_blocked_title": "ब्लॉक किए गए लेनदेन",
            "list_high_risk_title": "उच्च जोखिम लेनदेन",
            "list_subtitle": "स्थानीय लेनदेन मेटाडेटा (राशि एन्क्रिप्टेड)",
            "users_list_title": "उपयोगकर्ता सूची",
            "transactions_meta_note": "राशि और प्राप्तकर्ता स्थानीय रूप से एन्क्रिप्टेड हैं और केवल PIN से दिखते हैं।",
            "audit_events_subtitle": "एपेंड-ओनली ऑडिट चेन लॉग",
            "audit_event_type": "इवेंट प्रकार",
            "audit_log_id": "लॉग ID",
            "audit_events_title": "ऑडिट इवेंट्स",
            "change_log_title": "चेंज लॉग",
            "change_log_subtitle": "स्थानीय बदलाव पुराने/नए मानों के साथ",
            "change_actor": "अभिनेता",
            "change_source": "स्रोत",
            "report_snapshot_title": "सुरक्षा रिपोर्ट",
            "report_snapshot_subtitle": "ऑडिट अखंडता के साथ स्थानीय स्नैपशॉट",
            "report_generated_at": "निर्मित समय",
            "report_audit_valid": "ऑडिट वैध",
            "report_entries_checked": "जाँची गई प्रविष्टियाँ",
            "report_audit_error": "ऑडिट त्रुटि",
            "report_download_json": "JSON डाउनलोड करें",
            "report_no_data": "अभी कोई सिम्युलेटर डेटा नहीं। नीचे क्लिक करके डेमो सिड करें।",
            "report_seed_demo": "इम्पैक्ट डेमो सिड करें",
            "demo_walkthrough_title": "प्रोफेसर डेमो वॉकथ्रू",
            "demo_walkthrough_subtitle": "प्रस्तुति के लिए निश्चित एंड-टू-एंड कहानी",
            "demo_user_id": "उपयोगकर्ता ID",
            "demo_pin": "PIN",
            "demo_trusted_hint": "विश्वसनीय संपर्क संकेत",
            "demo_release_done": "विश्वसनीय रिलीज़ पूर्ण",
            "demo_yes": "हाँ",
            "demo_no": "नहीं",
            "demo_script_title": "क्या कहना है (त्वरित स्क्रिप्ट)",
            "demo_step_a_title": "चरण A: सामान्य कम-जोखिम भुगतान",
            "demo_step_b_title": "चरण B: अज्ञात प्राप्तकर्ता को स्कैम-जैसा ट्रांसफर",
            "demo_step_c_title": "चरण C: पैनिक फ्रीज़ आउटगोइंग ट्रांसफर रोकता है",
            "demo_point_1": "लेनदेन डेटा एन्क्रिप्टेड है और पहले ऑफलाइन स्टोर होता है।",
            "demo_point_2": "रिस्क स्कोरिंग संदिग्ध पैटर्न को कारणों सहित दर्शाती है।",
            "demo_point_3": "उच्च जोखिम वाले फ्लो सिंक से पहले होल्ड या ब्लॉक होते हैं।",
            "demo_point_4": "विश्वसनीय संपर्क स्वीकृति और पैनिक फ्रीज़ तत्काल धोखाधड़ी नुकसान रोकते हैं।",
            "demo_point_5": "सभी निर्णय स्थानीय UI में सहायक ग्रामीण संचालन के लिए दिखाई देते हैं।",
            "demo_guide_title": "डेमो गाइड",
            "demo_guide_subtitle": "पोर्टल स्पष्ट रूप से समझाने के लिए सब कुछ",
            "demo_about_title": "यह पेज क्या है",
            "demo_about_body": "RuralShield ग्रामीण डिजिटल बैंकिंग के लिए ऑफलाइन-प्रथम साइबरसुरक्षा फ्रेमवर्क है। यह डेटा डिवाइस पर सुरक्षित रखता है, स्थानीय रूप से जोखिम पहचानता है, और नेटवर्क उपलब्ध होने पर सुरक्षित रूप से सिंक करता है।",
            "demo_features_title": "मुख्य विशेषताएँ",
            "demo_feature_1": "उपयोगकर्ता और लेनदेन के लिए एन्क्रिप्टेड लोकल स्टोरेज (SQLite)।",
            "demo_feature_2": "समझने योग्य कारणों के साथ फ्रॉड जोखिम स्कोरिंग।",
            "demo_feature_3": "सुरक्षा हस्तक्षेप: अनुमति, स्टेप-अप, होल्ड या ब्लॉक।",
            "demo_feature_4": "जोखिमभरे ट्रांसफर के लिए विश्वसनीय संपर्क अनुमोदन।",
            "demo_feature_5": "संदिग्ध फ्रॉड पर आउटगोइंग ट्रांसफर रोकने के लिए पैनिक फ्रीज़।",
            "demo_feature_6": "छेड़छाड़ प्रमाण के लिए ऑडिट चेन।",
            "demo_feature_7": "ऑफलाइन आउटबॉक्स और सुरक्षित सिंक।",
            "demo_steps_title": "डेमो कैसे दिखाएँ (त्वरित चरण)",
            "demo_step_1": "आवश्यक हो तो डैशबोर्ड से डेमो डेटा सिड करें।",
            "demo_step_2": "लो-रिस्क फ्लो दिखाने के लिए सामान्य लेनदेन बनाएं।",
            "demo_step_3": "होल्ड/ब्लॉक दिखाने के लिए बड़े अमाउंट वाला नया प्राप्तकर्ता लेनदेन बनाएं।",
            "demo_step_4": "विश्वसनीय मंजूरी कोड के साथ Held Transaction रिलीज़ करें।",
            "demo_step_5": "सिम्युलेटर मेट्रिक्स दिखाने के लिए Fraud Impact Report खोलें।",
            "demo_step_6": "स्क्रिप्टेड डेमो के लिए Professor Walkthrough खोलें।",
            "demo_data_title": "डेटा कहाँ संग्रहीत है",
            "demo_data_1": "प्राथमिक स्टोरेज: लोकल SQLite डेटाबेस।",
            "demo_data_2": "चेंज लॉग: पुराने/नए मान स्थानीय रूप से, CSV के रूप में निर्यात योग्य।",
            "demo_data_3": "नेटवर्क सुरक्षित होने पर बाद में सिंक होता है।",
            "demo_pages_title": "खोले जा सकने वाले पेज",
            "demo_page_1": "डैशबोर्ड: मुख्य एक्शन और आँकड़े।",
            "demo_page_2": "Agent/Kiosk Mode: एकल असिस्टेड वर्कफ़्लो।",
            "demo_page_3": "Fraud Impact Report: सिम्युलेटर परिणाम।",
            "demo_page_4": "Professor Walkthrough: स्क्रिप्टेड डेमो स्टोरी।",
            "demo_page_5": "Change Log: बदलाव के पुराने/नए मान।",
            "sync_queue_title": "ऑफलाइन सिंक कतार",
            "sync_queue_subtitle": "स्थानीय लंबित लेनदेन जो नाइट सिंक की प्रतीक्षा में हैं",
        },
        "or": {
            "lang_label": "ଭାଷା",
            "language_label": "ଭାଷା",
            "title": "RuralShield",
            "subtitle": "ଗ୍ରାମୀଣ ଡିଜିଟାଲ ବ୍ୟାଙ୍କିଙ୍ଗ ପାଇଁ ଅଫଲାଇନ-ପ୍ରଥମ ସୁରକ୍ଷା ପ୍ରଟୋଟାଇପ",
            "page_title_customer_dashboard": "ଗ୍ରାହକ ପୋର୍ଟାଲ - RuralShield",
            "page_title_customer_history": "ଲେନଦେନ ଇତିହାସ - RuralShield",
            "cust_open_history": "ଲେନଦେନ ଇତିହାସ ଖୋଲନ୍ତୁ",
            "cust_history_pin_note": "ରାଶି ଏବଂ ପ୍ରାପ୍ତକର୍ତ୍ତା ଦେଖିବାକୁ PIN ଆବଶ୍ୟକ।",
            "cust_unlock_history": "ଇତିହାସ ଅନଲକ୍ କରନ୍ତୁ",
            "cust_view_history": "ଇତିହାସ ଦେଖନ୍ତୁ",
            "cust_history_table_title": "ଡିକ୍ରିପ୍ଟେଡ୍ ଲେନଦେନ",
            "cust_use_history": "ଆପଣଙ୍କ ଲେନଦେନ ଦେଖିବାକୁ Customer History ବ୍ୟବହାର କରନ୍ତୁ।",
            "cust_safety_settings_title": "ସୁରକ୍ଷା ସେଟିଂସ୍",
            "cust_trusted_current": "ଭରସାଯୋଗ୍ୟ ସମ୍ପର୍କ:",
            "cust_freeze_until": "ଫ୍ରିଜ୍ ପର୍ଯ୍ୟନ୍ତ:",
            "back_to_dashboard": "ଡ୍ୟାଶବୋର୍ଡକୁ ଫେରନ୍ତୁ",
            "page_title_dashboard": "RuralShield ଡେମୋ",
            "page_title_users": "ବ୍ୟବହାରକାରୀ ତାଲିକା - RuralShield",
            "page_title_transactions": "ଟ୍ରାନ୍ଜାକ୍ସନ - RuralShield",
            "page_title_transaction_list": "ଟ୍ରାନ୍ଜାକ୍ସନ ତାଲିକା - RuralShield",
            "page_title_change_log": "ଚେଞ୍ଜ ଲଗ୍ - RuralShield",
            "page_title_report": "ସୁରକ୍ଷା ରିପୋର୍ଟ - RuralShield",
            "page_title_impact": "ଠକେଇ ପ୍ରଭାବ ରିପୋର୍ଟ - RuralShield",
            "page_title_demo_guide": "ଡେମୋ ଗାଇଡ୍ - RuralShield",
            "page_title_demo_walkthrough": "ପ୍ରୋଫେସର ଡେମୋ ଓକ୍ଥ୍ରୁ - RuralShield",
            "page_title_agent": "ଏଜେଣ୍ଟ ମୋଡ୍ - RuralShield",
            "page_title_audit": "ଅଡିଟ୍ ଘଟଣା - RuralShield",
            "page_title_sync_queue": "ସିଙ୍କ କ୍ୟୁ - RuralShield",
            "users": "ବ୍ୟବହାରକାରୀ",
            "transactions": "ଟ୍ରାନ୍ଜାକ୍ସନ",
            "pending_sync": "ସିଙ୍କ ବାକୀ",
            "synced": "ସିଙ୍କ ସମାପ୍ତ",
            "held": "ରୋକାଯାଇଥିବା",
            "blocked": "ବ୍ଲକ୍",
            "released": "ମୁକ୍ତ",
            "high_risk": "ଉଚ୍ଚ ଝୁମ୍ପ",
            "audit_events": "ଅଡିଟ୍ ଘଟଣା",
            "section_1": "1. ବ୍ୟବହାରକାରୀ ରେଜିଷ୍ଟର / ବଦଳ",
            "section_2": "2. ସୁରକ୍ଷିତ ଟ୍ରାନ୍ଜାକ୍ସନ ସୃଷ୍ଟି",
            "section_3": "3. ଟ୍ରାନ୍ଜାକ୍ସନ ତାଲିକା ଦେଖନ୍ତୁ",
            "section_4": "4. ସିଙ୍କ ଏବଂ ଅଡିଟ୍",
            "section_5": "5. ଠକେଇ ପରିସ୍ଥିତି ସିମ୍ୟୁଲେଟର୍",
            "agent_title": "ଏଜେଣ୍ଟ/କିଓସ୍କ ସହାୟିତ ମୋଡ୍",
            "agent_subtitle": "ବିଜନେସ୍ କରେସ୍ପୋଣ୍ଡେଣ୍ଟ ପାଇଁ ଏକ-ସ୍କ୍ରିନ୍ ସୁରକ୍ଷିତ ଟ୍ରାନ୍ଜାକ୍ସନ ଫ୍ଲୋ",
            "agent_user": "ବ୍ୟବହାରକାରୀ ID",
            "agent_phone": "ଫୋନ୍ ନମ୍ବର",
            "agent_pin": "PIN",
            "agent_amount": "ରାଶି",
            "agent_recipient": "ପ୍ରାପ୍ତକର୍ତ୍ତା",
            "agent_trusted": "ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ (ଇଚ୍ଛାଧୀନ)",
            "agent_submit": "ସୁରକ୍ଷିତ ସହାୟିତ ଟ୍ରାନ୍ଜାକ୍ସନ ଚାଲାନ୍ତୁ",
            "agent_result": "ସହାୟିତ ଟ୍ରାନ୍ଜାକ୍ସନ ଫଳାଫଳ",
            "voice_play": "ସୁରକ୍ଷା ପରାମର୍ଶ ଶୁଣନ୍ତୁ",
            "report_title": "ଠକେଇ ପ୍ରଭାବ ରିପୋର୍ଟ",
            "report_subtitle": "ଆଣ୍ଟି-ଫ୍ରଡ୍ କନ୍ଟ୍ରୋଲ୍ ପାଇଁ ମାପିତ ସିମ୍ୟୁଲେସନ୍ ଫଳାଫଳ",
            "report_runs": "ପରିସ୍ଥିତି ଚାଳନ",
            "report_txs": "ସିମ୍ୟୁଲେଟେଡ୍ ଟ୍ରାନ୍ଜାକ୍ସନ",
            "report_protection": "ସୁରକ୍ଷା ହାର",
            "report_avg_risk": "ସର୍ବମୋଟ ଝୁମ୍ପ ସ୍କୋର",
            "report_recent": "ସମ୍ପ୍ରତି ସିମ୍ୟୁଲେସନ୍ ଚାଳନ",
            "report_breakdown": "ପରିସ୍ଥିତି ଭିତ୍ତିକ ବିଭାଜନ",
            "scenario_user": "ସିମ୍ୟୁଲେସନ୍ ୟୁଜର୍ ID",
            "scenario_pin": "ସିମ୍ୟୁଲେସନ୍ PIN",
            "scenario_contact": "ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ (ଇଚ୍ଛାଧୀନ)",
            "scenario_choice": "ପରିସ୍ଥିତି",
            "run_scenario_btn": "ପରିସ୍ଥିତି ଚାଲାନ୍ତୁ",
            "save_user": "ବ୍ୟବହାରକାରୀ ସେଭ୍ କରନ୍ତୁ",
            "set_trusted": "ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ ସେଟ୍ କରନ୍ତୁ",
            "enable_freeze": "ପ୍ୟାନିକ ଫ୍ରିଜ୍ ଚାଲୁ କରନ୍ତୁ",
            "create_tx": "ଟ୍ରାନ୍ଜାକ୍ସନ ସୃଷ୍ଟି",
            "open_tx_list": "ଟ୍ରାନ୍ଜାକ୍ସନ ତାଲିକା ଖୋଲନ୍ତୁ",
            "sync_pending": "ବାକୀ ଟ୍ରାନ୍ଜାକ୍ସନ ସିଙ୍କ କରନ୍ତୁ",
            "release_held": "ରୋକାଯାଇଥିବା ଟ୍ରାନ୍ଜାକ୍ସନ ମୁକ୍ତ କରନ୍ତୁ",
            "check_audit": "ଅଡିଟ୍ ଅଖଣ୍ଡତା ଯାଞ୍ଚ",
            "seed_demo": "ଡେମୋ ତଥ୍ୟ ତିଆରି",
            "export_report": "ସୁରକ୍ଷା ରିପୋର୍ଟ ନିର୍ଯାତ",
            "export_change_log": "ଚେଞ୍ଜ ଲଗ୍ ନିର୍ଯାତ (CSV)",
            "agent_mode": "ଏଜେଣ୍ଟ/କିଓସ୍କ ମୋଡ୍ ଖୋଲନ୍ତୁ",
            "impact_report": "ଠକେଇ ପ୍ରଭାବ ରିପୋର୍ଟ",
            "demo_walkthrough": "ପ୍ରୋଫେସର ଡେମୋ ଚଲାନ୍ତୁ",
            "demo_guide": "ଡେମୋ ଗାଇଡ୍",
            "clear_messages": "ସନ୍ଦେଶ ସଫା କରନ୍ତୁ",
            "sync_queue_open": "ସିଙ୍କ କ୍ୟୁ ଖୋଲନ୍ତୁ",
            "more_tools": "ଅଧିକ ଟୁଲ୍ସ",
            "replace_user": "ପୂର୍ବରୁ ଥିବା ବ୍ୟବହାରକାରୀକୁ ବଦଳନ୍ତୁ",
            "ph_user_id_example": "ବ୍ୟବହାରକାରୀ ID (ଯେପରି, u1)",
            "ph_phone_example": "ଫୋନ୍ (ଯେପରି, +919999999999)",
            "ph_pin_4digit": "4-ଡିଜିଟ୍ PIN",
            "ph_user_id_trusted": "ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ ପାଇଁ ବ୍ୟବହାରକାରୀ ID",
            "ph_pin": "PIN",
            "ph_trusted_contact": "ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ ଫୋନ୍ କିମ୍ବା ID",
            "ph_user_id_freeze": "ପ୍ୟାନିକ୍ ଫ୍ରିଜ୍ ପାଇଁ ବ୍ୟବହାରକାରୀ ID",
            "ph_freeze_minutes": "ଫ୍ରିଜ୍ ମିନିଟ୍",
            "ph_user_id": "ବ୍ୟବହାରକାରୀ ID",
            "ph_amount": "ରାଶି",
            "ph_recipient_name": "ପ୍ରାପ୍ତକର୍ତ୍ତା ନାମ",
            "ph_limit": "ସୀମା",
            "ph_server_url": DEFAULT_SERVER_URL,
            "ph_held_tx_id": "ରୋକାଯାଇଥିବା ଟ୍ରାନ୍ଜାକ୍ସନ ID",
            "ph_approval_code": "ଭରସାଯୋଗ୍ୟ ସ୍ୱୀକୃତି କୋଡ୍ (ଆବଶ୍ୟକ ହେଲେ)",
            "tx_list_title": "ଟ୍ରାନ୍ଜାକ୍ସନ ତାଲିକା",
            "user_label": "ବ୍ୟବହାରକାରୀ",
            "time": "ସମୟ",
            "tx_id": "ଟ୍ରାନ୍ଜାକ୍ସନ ID",
            "amount": "ରାଶି",
            "recipient": "ପ୍ରାପ୍ତକର୍ତ୍ତା",
            "risk": "ଝୁମ୍ପ",
            "action": "କାର୍ଯ୍ୟ",
            "reasons": "କାରଣ",
            "guidance": "ପରାମର୍ଶ",
            "approval": "ସ୍ୱୀକୃତି",
            "status": "ସ୍ଥିତି",
            "back_dashboard": "ଡ୍ୟାଶବୋର୍ଡକୁ ଫେରନ୍ତୁ",
            "retrying": "ପୁନଃଚେଷ୍ଟା",
            "sync_state": "ସିଙ୍କ ସ୍ଥିତି",
            "retry_count": "ପୁନଃଚେଷ୍ଟା ସଂଖ୍ୟା",
            "next_retry": "ପରବର୍ତ୍ତୀ ପୁନଃଚେଷ୍ଟା",
            "last_error": "ଶେଷ ତ୍ରୁଟି",
            "outbox_id": "ଆଉଟବକ୍ସ ID",
            "simulate_night_sync": "ନାଇଟ୍ ସିଙ୍କ ସିମ୍ୟୁଲେଟ୍",
            "failed_attempts": "ବିଫଳ ପ୍ରୟାସ",
            "last_auth": "ଶେଷ ଅଥେଣ୍ଟିକେସନ୍",
            "trusted_contact": "ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ",
            "freeze_until": "ଫ୍ରିଜ୍ ପର୍ଯ୍ୟନ୍ତ",
            "created_at": "ତିଆରି ସମୟ",
            "required": "ଆବଶ୍ୟକ",
            "demo_code": "ଡେମୋ ସ୍ୱୀକୃତି କୋଡ୍",
            "how_read_title": "ଏହାକୁ କିପରି ବୁଝିବେ",
            "how_read_pending": "ସିଙ୍କ ବାକୀ ଅର୍ଥ ତଥ୍ୟ ଲୋକାଲରେ ସୁରକ୍ଷିତ ରହିଛି ଏବଂ ସର୍ଭର ସିଙ୍କ ପ୍ରତୀକ୍ଷାରେ।",
            "how_read_blocked": "ବ୍ଲକ୍ ଅର୍ଥ ଝୁମ୍ପ ନୀତି ଏହି ଟ୍ରାନ୍ଜାକ୍ସନକୁ ରୋକିଛି।",
            "how_read_risk": "ଝୁମ୍ପ ଓ ଆକ୍ସନ୍ କହେ କେଉଁ ସୁରକ୍ଷା ପଦକ୍ଷେପ ଆବଶ୍ୟକ।",
            "recent_change_log": "ସମ୍ପ୍ରତି ଚେଞ୍ଜ ଲଗ୍",
            "change_entity": "ଏଣ୍ଟିଟି",
            "change_field": "ଫିଲ୍ଡ୍",
            "change_old": "ପୁରୁଣା",
            "change_new": "ନୂତନ",
            "change_log_full": "ପୂର୍ଣ୍ଣ ଚେଞ୍ଜ ଲଗ୍ ଖୋଲନ୍ତୁ",
            "list_all_title": "ସମସ୍ତ ଟ୍ରାନ୍ଜାକ୍ସନ",
            "list_pending_title": "ସିଙ୍କ ବାକୀ ଟ୍ରାନ୍ଜାକ୍ସନ",
            "list_synced_title": "ସିଙ୍କ ହୋଇଥିବା ଟ୍ରାନ୍ଜାକ୍ସନ",
            "list_held_title": "ରୋକାଯାଇଥିବା ଟ୍ରାନ୍ଜାକ୍ସନ",
            "list_blocked_title": "ବ୍ଲକ୍ ହୋଇଥିବା ଟ୍ରାନ୍ଜାକ୍ସନ",
            "list_high_risk_title": "ଉଚ୍ଚ ଝୁମ୍ପ ଟ୍ରାନ୍ଜାକ୍ସନ",
            "list_subtitle": "ସ୍ଥାନୀୟ ଟ୍ରାନ୍ଜାକ୍ସନ ମେଟାଡାଟା (ରାଶି ଏନକ୍ରିପ୍ଟେଡ୍)",
            "users_list_title": "ବ୍ୟବହାରକାରୀ ତାଲିକା",
            "transactions_meta_note": "ରାଶି ଏବଂ ପ୍ରାପ୍ତକର୍ତ୍ତା ସ୍ଥାନୀୟ ଭାବେ ଏନକ୍ରିପ୍ଟେଡ୍ ଏବଂ କେବଳ PIN ଦ୍ୱାରା ଦେଖାଯାଏ।",
            "audit_events_subtitle": "ଅପେଣ୍ଡ-ଓନ୍ଲି ଅଡିଟ୍ ଚେନ୍ ଲଗ୍",
            "audit_event_type": "ଇଭେଣ୍ଟ ପ୍ରକାର",
            "audit_log_id": "ଲଗ୍ ID",
            "audit_events_title": "ଅଡିଟ୍ ଘଟଣା",
            "change_log_title": "ଚେଞ୍ଜ ଲଗ୍",
            "change_log_subtitle": "ସ୍ଥାନୀୟ ପରିବର୍ତ୍ତନ ପୁରୁଣା/ନୂତନ ମୂଲ୍ୟ ସହିତ",
            "change_actor": "ଅଭିନୟକର୍ତ୍ତା",
            "change_source": "ସ୍ରୋତ",
            "report_snapshot_title": "ସୁରକ୍ଷା ରିପୋର୍ଟ",
            "report_snapshot_subtitle": "ଅଡିଟ୍ ଅଖଣ୍ଡତା ସହିତ ସ୍ଥାନୀୟ ସ୍ନାପଶଟ୍",
            "report_generated_at": "ତିଆରି ସମୟ",
            "report_audit_valid": "ଅଡିଟ୍ ଠିକ୍",
            "report_entries_checked": "ଯାଞ୍ଚ ଏଣ୍ଟ୍ରି",
            "report_audit_error": "ଅଡିଟ୍ ତ୍ରୁଟି",
            "report_download_json": "JSON ଡାଉନଲୋଡ୍ କରନ୍ତୁ",
            "report_no_data": "ଏପର୍ଯ୍ୟନ୍ତ ସିମ୍ୟୁଲେଟର୍ ଡେଟା ନାହିଁ। ତଳେ କ୍ଲିକ୍ କରି ଡେମୋ ସିଡ୍ କରନ୍ତୁ।",
            "report_seed_demo": "ଇମ୍ପାକ୍ଟ ଡେମୋ ସିଡ୍ କରନ୍ତୁ",
            "demo_walkthrough_title": "ପ୍ରୋଫେସର ଡେମୋ ଓକ୍ଥ୍ରୁ",
            "demo_walkthrough_subtitle": "ପ୍ରସ୍ତୁତି ପାଇଁ ନିଶ୍ଚିତ ଏଣ୍ଡ-ଟୁ-ଏଣ୍ଡ କଥା",
            "demo_user_id": "ବ୍ୟବହାରକାରୀ ID",
            "demo_pin": "PIN",
            "demo_trusted_hint": "ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ ସୂଚନା",
            "demo_release_done": "ଭରସାଯୋଗ୍ୟ ମୁକ୍ତି ସମାପ୍ତ",
            "demo_yes": "ହଁ",
            "demo_no": "ନା",
            "demo_script_title": "କଣ କହିବେ (ତ୍ୱରିତ ସ୍କ୍ରିପ୍ଟ)",
            "demo_step_a_title": "ପଦକ୍ଷେପ A: ସାଧାରଣ କମ୍-ଝୁମ୍ପ ପେମେଣ୍ଟ",
            "demo_step_b_title": "ପଦକ୍ଷେପ B: ଅଜଣା ପ୍ରାପ୍ତକର୍ତ୍ତାକୁ ଠକେଇ-ସଦୃଶ ଟ୍ରାନ୍ସଫର୍",
            "demo_step_c_title": "ପଦକ୍ଷେପ C: ପ୍ୟାନିକ୍ ଫ୍ରିଜ୍ ଆଉଟଗୋଇଂ ଟ୍ରାନ୍ସଫର୍ ରୋକେ",
            "demo_point_1": "ଟ୍ରାନ୍ଜାକ୍ସନ ତଥ୍ୟ ଏନକ୍ରିପ୍ଟେଡ୍ ଏବଂ ପ୍ରଥମେ ଅଫଲାଇନ ରଖାଯାଏ।",
            "demo_point_2": "ଝୁମ୍ପ ସ୍କୋରିଂ କାରଣ ସହିତ ସନ୍ଦେହଜନକ ପ୍ୟାଟର୍ନ ଚିହ୍ନଟ କରେ।",
            "demo_point_3": "ଉଚ୍ଚ ଝୁମ୍ପ ଫ୍ଲୋ ସିଙ୍କ ପୂର୍ବରୁ ହୋଲ୍ଡ କିମ୍ବା ବ୍ଲକ୍ ହୁଏ।",
            "demo_point_4": "ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ ଅନୁମୋଦନ ଏବଂ ପ୍ୟାନିକ୍ ଫ୍ରିଜ୍ ତୁରନ୍ତ ଠକେଇ ହାନି ରୋକେ।",
            "demo_point_5": "ସମସ୍ତ ନିଷ୍ପତ୍ତି ସ୍ଥାନୀୟ UI ରେ ସହାୟିତ ଗ୍ରାମୀଣ ଅପରେସନ ପାଇଁ ଦେଖାଯାଏ।",
            "demo_guide_title": "ଡେମୋ ଗାଇଡ୍",
            "demo_guide_subtitle": "ପୋର୍ଟାଲ୍ ବୁଝାଇବା ପାଇଁ ସବୁକିଛି",
            "demo_about_title": "ଏହି ପୋର୍ଟାଲ୍ କଣ",
            "demo_about_body": "RuralShield ଗ୍ରାମୀଣ ଡିଜିଟାଲ ବ୍ୟାଙ୍କିଙ୍ଗ ପାଇଁ ଅଫଲାଇନ-ପ୍ରଥମ ସାଇବର ସୁରକ୍ଷା ଫ୍ରେମୱର୍କ। ଏହା ତଥ୍ୟକୁ ଡିଭାଇସରେ ସୁରକ୍ଷିତ ରଖେ, ସ୍ଥାନୀୟ ଭାବରେ ଝୁମ୍ପ ଚିହ୍ନଟ କରେ, ଏବଂ ନେଟୱର୍କ ଉପଲବ୍ଧ ହେଲେ ସୁରକ୍ଷିତ ସିଙ୍କ କରେ।",
            "demo_features_title": "ମୁଖ୍ୟ ବୈଶିଷ୍ଟ୍ୟ",
            "demo_feature_1": "ବ୍ୟବହାରକାରୀ ଓ ଟ୍ରାନ୍ଜାକ୍ସନ ପାଇଁ ଏନକ୍ରିପ୍ଟେଡ୍ ଲୋକାଲ୍ ଷ୍ଟୋରେଜ୍ (SQLite)।",
            "demo_feature_2": "ବ୍ୟାଖ୍ୟାସହିତ ଫ୍ରଡ୍ ଝୁମ୍ପ ସ୍କୋରିଂ।",
            "demo_feature_3": "ସୁରକ୍ଷା ହସ୍ତକ୍ଷେପ: ଅନୁମତି, ଷ୍ଟେପ୍-ଅପ୍, ହୋଲ୍ଡ କିମ୍ବା ବ୍ଲକ୍।",
            "demo_feature_4": "ଝୁମ୍ପ ଟ୍ରାନ୍ସଫର୍ ପାଇଁ ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ ଅନୁମୋଦନ।",
            "demo_feature_5": "ସନ୍ଦେହଜନକ ଠକେଇ ହେଲେ ବାହାରୁଥିବା ଟ୍ରାନ୍ସଫର୍ ରୋକିବା ପାଇଁ ପ୍ୟାନିକ୍ ଫ୍ରିଜ୍।",
            "demo_feature_6": "ଛେଡ଼ାଖାନି ପ୍ରମାଣ ପାଇଁ ଅଡିଟ୍ ଚେନ୍।",
            "demo_feature_7": "ଅଫଲାଇନ ଆଉଟବକ୍ସ ଏବଂ ସୁରକ୍ଷିତ ସିଙ୍କ।",
            "demo_steps_title": "ଡେମୋ କିପରି ଦେଖାଇବେ (ତ୍ୱରିତ ପଦକ୍ଷେପ)",
            "demo_step_1": "ଦରକାର ହେଲେ ଡ୍ୟାଶବୋର୍ଡରୁ ଡେମୋ ଡାଟା ସିଡ୍ କରନ୍ତୁ।",
            "demo_step_2": "ଲୋ-ରିସ୍କ ଫ୍ଲୋ ଦେଖାଇବା ପାଇଁ ସାଧାରଣ ଟ୍ରାନ୍ଜାକ୍ସନ କରନ୍ତୁ।",
            "demo_step_3": "ହୋଲ୍ଡ/ବ୍ଲକ୍ ଦେଖାଇବା ପାଇଁ ବଡ଼ ରାଶି ଓ ନୂତନ ପ୍ରାପ୍ତକର୍ତ୍ତା ସହ ଟ୍ରାନ୍ଜାକ୍ସନ କରନ୍ତୁ।",
            "demo_step_4": "ଭରସାଯୋଗ୍ୟ ଅନୁମୋଦନ କୋଡ୍ ସହିତ Held Transaction ମୁକ୍ତ କରନ୍ତୁ।",
            "demo_step_5": "ସିମ୍ୟୁଲେଟର୍ ମେଟ୍ରିକ୍ସ ଦେଖାଇବା ପାଇଁ Fraud Impact Report ଖୋଲନ୍ତୁ।",
            "demo_step_6": "ସ୍କ୍ରିପ୍ଟେଡ୍ ଡେମୋ ପାଇଁ Professor Walkthrough ଖୋଲନ୍ତୁ।",
            "demo_data_title": "ଡାଟା କେଉଁଠି ସଂରକ୍ଷିତ",
            "demo_data_1": "ମୁଖ୍ୟ ସଂରକ୍ଷଣ: ଲୋକାଲ୍ SQLite ଡାଟାବେସ୍।",
            "demo_data_2": "ଚେଞ୍ଜ ଲଗ୍: ପୁରୁଣା/ନୂତନ ମୂଲ୍ୟ ସ୍ଥାନୀୟ ଭାବରେ, CSV ଭାବେ ନିର୍ଯାତଯୋଗ୍ୟ।",
            "demo_data_3": "ନେଟୱର୍କ ସୁରକ୍ଷିତ ହେଲେ ପରେ ସିଙ୍କ ହୁଏ।",
            "demo_pages_title": "ଖୋଲିପାରିବା ପୃଷ୍ଠାଗୁଡ଼ିକ",
            "demo_page_1": "ଡ୍ୟାଶବୋର୍ଡ: ମୁଖ୍ୟ କାର୍ଯ୍ୟ ଏବଂ ଆଙ୍କଡା।",
            "demo_page_2": "Agent/Kiosk Mode: ଏକକ ଅସିଷ୍ଟେଡ୍ ୱର୍କଫ୍ଲୋ।",
            "demo_page_3": "Fraud Impact Report: ସିମ୍ୟୁଲେଟର୍ ଫଳାଫଳ।",
            "demo_page_4": "Professor Walkthrough: ସ୍କ୍ରିପ୍ଟେଡ୍ ଡେମୋ କଥା।",
            "demo_page_5": "Change Log: ପରିବର୍ତ୍ତନ ପାଇଁ ପୁରୁଣା/ନୂତନ ମୂଲ୍ୟ।",
            "sync_queue_title": "ଅଫଲାଇନ ସିଙ୍କ କ୍ୟୁ",
            "sync_queue_subtitle": "ରାତି ସିଙ୍କ ପାଇଁ ପ୍ରତୀକ୍ଷା କରୁଥିବା ସ୍ଥାନୀୟ ଟ୍ରାନ୍ଜାକ୍ସନ",
        },
        "gu": {
            "lang_label": "ભાષા",
            "language_label": "ભાષા",
            "title": "RuralShield",
            "subtitle": "ગ્રામિણ ડિજિટલ બેંકિંગ માટે ઑફલાઇન-ફર્સ્ટ સુરક્ષા પ્રોટોટાઇપ",
            "page_title_customer_dashboard": "ગ્રાહક પોર્ટલ - RuralShield",
            "page_title_customer_history": "લેન્દેન ઇતિહાસ - RuralShield",
            "cust_open_history": "લેન્દેન ઇતિહાસ ખોલો",
            "cust_history_pin_note": "રકમ અને પ્રાપ્તકર્તા જોવા માટે PIN જરૂરી છે.",
            "cust_unlock_history": "ઇતિહાસ અનલોક કરો",
            "cust_view_history": "ઇતિહાસ જુઓ",
            "cust_history_table_title": "ડિક્રિપ્ટેડ લેન્દેન",
            "cust_use_history": "તમારા લેન્દેન જોવા માટે Customer History નો ઉપયોગ કરો.",
            "cust_safety_settings_title": "સેફ્ટી સેટિંગ્સ",
            "cust_trusted_current": "ટ્રસ્ટેડ કોન્ટેક્ટ:",
            "cust_freeze_until": "ફ્રીઝ સુધી:",
            "back_to_dashboard": "ડેશબોર્ડ પર પાછા",
            "page_title_dashboard": "RuralShield ડેમો",
            "page_title_users": "વપરાશકર્તા યાદી - RuralShield",
            "page_title_transactions": "લેનદેન - RuralShield",
            "page_title_transaction_list": "લેનદેન યાદી - RuralShield",
            "page_title_change_log": "ચેન્જ લોગ - RuralShield",
            "page_title_report": "સિક્યોરિટી રિપોર્ટ - RuralShield",
            "page_title_impact": "ઠગાઇ પ્રભાવ રિપોર્ટ - RuralShield",
            "page_title_demo_guide": "ડેમો ગાઇડ - RuralShield",
            "page_title_demo_walkthrough": "પ્રોફેસર ડેમો વોકથ્રૂ - RuralShield",
            "page_title_agent": "એજન્ટ મોડ - RuralShield",
            "page_title_audit": "ઑડિટ ઇવેન્ટ્સ - RuralShield",
            "page_title_sync_queue": "સિંક કતાર - RuralShield",
            "users": "વપરાશકર્તાઓ",
            "transactions": "લેનદેન",
            "pending_sync": "સિંક બાકી",
            "synced": "સિંક થયું",
            "held": "રોકાયેલ",
            "blocked": "બ્લોક્ડ",
            "released": "રિલીઝ થયેલ",
            "high_risk": "ઉચ્ચ જોખમ",
            "audit_events": "ઑડિટ ઇવેન્ટ્સ",
            "audit_events_title": "ઑડિટ ઇવેન્ટ્સ",
            "section_1": "1. વપરાશકર્તા નોંધણી / બદલી",
            "section_2": "2. સુરક્ષિત લેનદેન બનાવો",
            "section_3": "3. લેનદેન યાદી જુઓ",
            "section_4": "4. સિંક અને ઑડિટ",
            "section_5": "5. ફ્રોડ સીનારિયો સિમ્યુલેટર",
            "agent_title": "એજન્ટ/કિયોસ્ક સહાયિત મોડ",
            "agent_subtitle": "બિઝનેસ કરસ્પોન્ડન્ટ માટે એક-સ્ક્રીન સહાયિત ટ્રાન્ઝેક્શન ફ્લો",
            "agent_user": "વપરાશકર્તા ID",
            "agent_phone": "ફોન નંબર",
            "agent_pin": "PIN",
            "agent_amount": "રકમ",
            "agent_recipient": "પ્રાપ્તકર્તા",
            "agent_trusted": "વિશ્વસનીય સંપર્ક (વૈકલ્પિક)",
            "agent_submit": "સુરક્ષિત સહાયિત ટ્રાન્ઝેક્શન ચલાવો",
            "agent_result": "સહાયિત ટ્રાન્ઝેક્શન પરિણામ",
            "voice_play": "સલામતી માર્ગદર્શન ઊંચે વાંચો",
            "report_title": "ઠગાઇ પ્રભાવ રિપોર્ટ",
            "report_subtitle": "એન્ટી-ફ્રોડ નિયંત્રણ માટે સિમ્યુલેટર પરિણામો",
            "report_runs": "સીનારિયો રન",
            "report_txs": "સિમ્યુલેટેડ ટ્રાન્ઝેક્શન",
            "report_protection": "સુરક્ષા દર",
            "report_avg_risk": "સરેરાશ જોખમ સ્કોર",
            "report_recent": "તાજેતરના સિમ્યુલેશન રન",
            "report_breakdown": "સીનારિયો બ્રેકડાઉન",
            "scenario_user": "સિમ્યુલેશન વપરાશકર્તા ID",
            "scenario_pin": "સિમ્યુલેશન PIN",
            "scenario_contact": "વિશ્વસનીય સંપર્ક (વૈકલ્પિક)",
            "scenario_choice": "સીનારિયો",
            "run_scenario_btn": "સીનારિયો ચલાવો",
            "save_user": "વપરાશકર્તા સંગ્રહો",
            "set_trusted": "વિશ્વસનીય સંપર્ક સેટ કરો",
            "enable_freeze": "પેનિક ફ્રીઝ સક્રિય કરો",
            "create_tx": "લેનદેન બનાવો",
            "open_tx_list": "લેનદેન યાદી ખોલો",
            "sync_pending": "બાકી લેનદેન સિંક કરો",
            "release_held": "રોકાયેલ લેનદેન રિલીઝ કરો",
            "check_audit": "ઑડિટ તપાસો",
            "seed_demo": "ડેમો ડેટા ભરો",
            "export_report": "સિક્યોરિટી રિપોર્ટ નિકાસ કરો",
            "export_change_log": "ચેન્જ લોગ નિકાસ કરો (CSV)",
            "agent_mode": "એજન્ટ/કિયોસ્ક મોડ ખોલો",
            "impact_report": "ઠગાઇ પ્રભાવ રિપોર્ટ",
            "demo_walkthrough": "પ્રોફેસર ડેમો વોકથ્રૂ ચલાવો",
            "demo_guide": "ડેમો ગાઇડ",
            "clear_messages": "સંદેશો સાફ કરો",
            "sync_queue_open": "સિંક કતાર ખોલો",
            "more_tools": "વધુ ટૂલ્સ",
            "replace_user": "હાજર વપરાશકર્તા બદલો",
            "ph_user_id_example": "વપરાશકર્તા ID (ઉદાહરણ, u1)",
            "ph_phone_example": "ફોન (ઉદાહરણ, +919999999999)",
            "ph_pin_4digit": "4-અંકનો PIN",
            "ph_user_id_trusted": "વિશ્વસનીય સંપર્ક માટે વપરાશકર્તા ID",
            "ph_pin": "PIN",
            "ph_trusted_contact": "વિશ્વસનીય સંપર્ક ફોન અથવા ID",
            "ph_user_id_freeze": "પેનિક ફ્રીઝ માટે વપરાશકર્તા ID",
            "ph_freeze_minutes": "ફ્રીઝ મિનિટ્સ",
            "ph_user_id": "વપરાશકર્તા ID",
            "ph_amount": "રકમ",
            "ph_recipient_name": "પ્રાપ્તકર્તાનું નામ",
            "ph_limit": "મર્યાદા",
            "ph_server_url": DEFAULT_SERVER_URL,
            "ph_held_tx_id": "રોકાયેલ ટ્રાન્ઝેક્શન ID",
            "ph_approval_code": "વિશ્વસનીય મંજૂરી કોડ (જરૂર હોય તો)",
            "tx_list_title": "લેનદેન યાદી",
            "user_label": "વપરાશકર્તા",
            "time": "સમય",
            "tx_id": "ટ્રાન્ઝેક્શન ID",
            "amount": "રકમ",
            "recipient": "પ્રાપ્તકર્તા",
            "risk": "જોખમ",
            "action": "ક્રિયા",
            "reasons": "કારણો",
            "guidance": "માર્ગદર્શન",
            "approval": "મંજૂરી",
            "status": "સ્થિતિ",
            "back_dashboard": "ડેશબોર્ડ પર પાછા",
            "retrying": "પુનઃપ્રયાસ",
            "sync_state": "સિંક સ્થિતિ",
            "retry_count": "રીટ્રાઈ સંખ્યા",
            "next_retry": "આગલું રીટ્રાઈ",
            "last_error": "છેલ્લી ભૂલ",
            "outbox_id": "આઉટબોક્સ ID",
            "simulate_night_sync": "નાઇટ સિંક સિમ્યુલેટ કરો",
            "failed_attempts": "નિષ્ફળ પ્રયાસો",
            "last_auth": "છેલ્લું પ્રમાણીકરણ",
            "trusted_contact": "વિશ્વસનીય સંપર્ક",
            "freeze_until": "ફ્રીઝ સુધી",
            "created_at": "બનાવ્યા નો સમય",
            "required": "આવશ્યક",
            "demo_code": "ડેમો મંજૂરી કોડ",
            "how_read_title": "આને કેવી રીતે વાંચવું",
            "how_read_pending": "સિંક બાકી એટલે ડેટા લોકલમાં સુરક્ષિત છે અને સર્વર સિંકની રાહ જોઈ રહ્યું છે.",
            "how_read_blocked": "બ્લોક્ડ એટલે જોખમ નીતિએ આ ટ્રાન્ઝેક્શન રોક્યું છે.",
            "how_read_risk": "જોખમ અને ક્રિયા જણાવે છે કે કયા સલામતી પગલાં જોઈએ.",
            "recent_change_log": "તાજેતરના ચેન્જ લોગ",
            "change_entity": "એન્ટિટી",
            "change_field": "ફીલ્ડ",
            "change_old": "જૂનું",
            "change_new": "નવું",
            "change_log_full": "પૂર્ણ ચેન્જ લોગ ખોલો",
            "list_all_title": "બધા લેનદેન",
            "list_pending_title": "સિંક બાકી લેનદેન",
            "list_synced_title": "સિંક થયેલ લેનદેન",
            "list_held_title": "રોકાયેલ લેનદેન",
            "list_blocked_title": "બ્લોક્ડ લેનદેન",
            "list_high_risk_title": "ઉચ્ચ જોખમ લેનદેન",
            "list_subtitle": "સ્થાનિક લેનદેન મેટાડેટા (રકમ એન્ક્રિપ્ટેડ)",
            "users_list_title": "વપરાશકર્તા યાદી",
            "transactions_meta_note": "રકમ અને પ્રાપ્તકર્તા લોકલમાં એન્ક્રિપ્ટેડ છે અને ફક્ત PINથી દેખાય છે.",
            "audit_events_subtitle": "એપેન્ડ-ઓનલી ઑડિટ ચેઇન લોગ",
            "audit_event_type": "ઇવેન્ટ પ્રકાર",
            "audit_log_id": "લૉગ ID",
            "change_log_title": "ચેન્જ લોગ",
            "change_log_subtitle": "સ્થાનિક ફેરફાર જૂના/નવા મૂલ્યો સાથે",
            "change_actor": "અભિનયકર્તા",
            "change_source": "સ્ત્રોત",
            "report_snapshot_title": "સિક્યોરિટી રિપોર્ટ",
            "report_snapshot_subtitle": "ઑડિટ ઈન્ટેગ્રિટી સાથે લોકલ સ્નૅપશોટ",
            "report_generated_at": "બનાવ્યાનો સમય",
            "report_audit_valid": "ઑડિટ માન્ય",
            "report_entries_checked": "ચકાસેલી એન્ટ્રીઓ",
            "report_audit_error": "ઑડિટ ભૂલ",
            "report_download_json": "JSON ડાઉનલોડ કરો",
            "report_no_data": "હાલે કોઈ સિમ્યુલેટર ડેટા નથી. નીચે ક્લિક કરીને ડેમો સીડ કરો.",
            "report_seed_demo": "ઇમ્પેક્ટ ડેમો સીડ કરો",
            "demo_walkthrough_title": "પ્રોફેસર ડેમો વોકથ્રૂ",
            "demo_walkthrough_subtitle": "પ્રસ્તુતિ માટે નિશ્ચિત સ્ટેપ-બાય-સ્ટેપ સ્ટોરી",
            "demo_user_id": "વપરાશકર્તા ID",
            "demo_pin": "PIN",
            "demo_trusted_hint": "વિશ્વસનીય સંપર્ક સંકેત",
            "demo_release_done": "વિશ્વસનીય રિલીઝ પૂર્ણ",
            "demo_yes": "હા",
            "demo_no": "ના",
            "demo_script_title": "શું કહેવું (ઝડપી સ્ક્રિપ્ટ)",
            "demo_step_a_title": "પગલું A: સામાન્ય ઓછા જોખમનું ચુકવણી",
            "demo_step_b_title": "પગલું B: અજાણ્યા પ્રાપ્તકર્તાને સ્કેમ જેવી ટ્રાન્સફર",
            "demo_step_c_title": "પગલું C: પેનિક ફ્રીઝ આઉટગોઇંગ ટ્રાન્સફર રોકે છે",
            "demo_point_1": "ટ્રાન્ઝેક્શન ડેટા એન્ક્રિપ્ટેડ છે અને પહેલે ઓફલાઇન સંગ્રહાય છે.",
            "demo_point_2": "જોખમ સ્કોરિંગ સમજાય એવા કારણો સાથે શંકાસ્પદ પેટર્ન દર્શાવે છે.",
            "demo_point_3": "ઉચ્ચ જોખમનાં ફ્લો સિંક પહેલાં હોલ્ડ અથવા બ્લોક થાય છે.",
            "demo_point_4": "વિશ્વસનીય સંપર્ક મંજૂરી અને પેનિક ફ્રીઝ તાત્કાલિક ઠગાઇ નુકસાન અટકાવે છે.",
            "demo_point_5": "બધા નિર્ણય સ્થાનિક UI માં સહાયક ગ્રામ્ય ઓપરેશન માટે દેખાય છે.",
            "demo_guide_title": "ડેમો ગાઇડ",
            "demo_guide_subtitle": "પોર્ટલ સમજાવવા માટે જરૂરી દરેક બાબત",
            "demo_about_title": "આ પોર્ટલ શું છે",
            "demo_about_body": "RuralShield ગ્રામિણ ડિજિટલ બેંકિંગ માટે ઑફલાઇન-ફર્સ્ટ સાયબરસિક્યોરિટી ફ્રેમવર્ક છે. તે ડેટા ઉપકરણ પર સુરક્ષિત રાખે છે, સ્થાનિક રીતે જોખમ ઓળખે છે અને નેટવર્ક ઉપલબ્ધ હોય ત્યારે સુરક્ષિત રીતે સિંક કરે છે.",
            "demo_features_title": "મુખ્ય વિશેષતાઓ",
            "demo_feature_1": "વપરાશકર્તા અને લેનદેન માટે એન્ક્રિપ્ટેડ લોકલ સ્ટોરેજ (SQLite).",
            "demo_feature_2": "સમજાય એવા કારણો સાથે ફ્રોડ જોખમ સ્કોરિંગ.",
            "demo_feature_3": "સેફટી પગલાં: મંજૂરી, સ્ટેપ-અપ, હોલ્ડ અથવા બ્લોક.",
            "demo_feature_4": "જોખમી ટ્રાન્સફર માટે વિશ્વસનીય સંપર્ક મંજૂરી.",
            "demo_feature_5": "શંકાસ્પદ ફ્રોડ વખતે બહાર જતી ટ્રાન્ઝેક્શન રોકવા પેનિક ફ્રીઝ.",
            "demo_feature_6": "ટેમ્પર પુરાવા માટે ઑડિટ ચેઇન.",
            "demo_feature_7": "ઑફલાઇન આઉટબોક્સ અને સુરક્ષિત સિંક.",
            "demo_steps_title": "ડેમો કેવી રીતે બતાવવો (ઝડપી પગલાં)",
            "demo_step_1": "જરૂર હોય તો ડેશબોર્ડમાંથી ડેમો ડેટા સીડ કરો.",
            "demo_step_2": "લો-રિસ્ક ફ્લો બતાવવા સામાન્ય ટ્રાન્ઝેક્શન બનાવો.",
            "demo_step_3": "હોલ્ડ/બ્લોક બતાવવા મોટા રકમનું નવા પ્રાપ્તકર્તાનું ટ્રાન્ઝેક્શન બનાવો.",
            "demo_step_4": "વિશ્વસનીય મંજૂરી કોડ સાથે Release Held Transaction ઉપયોગ કરો.",
            "demo_step_5": "સિમ્યુલેટર માપદંડ બતાવવા Fraud Impact Report ખોલો.",
            "demo_step_6": "સ્ક્રિપ્ટેડ ડેમો માટે Professor Walkthrough ખોલો.",
            "demo_data_title": "ડેટા ક્યાં સંગ્રહાય છે",
            "demo_data_1": "પ્રાથમિક સંગ્રહ: લોકલ SQLite ડેટાબેઝ.",
            "demo_data_2": "ચેન્જ લોગ: જૂના/નવા મૂલ્યો લોકલમાં સંગ્રહાય છે અને CSV તરીકે નિકાસ કરી શકાય છે.",
            "demo_data_3": "નેટવર્ક સુરક્ષિત હોય ત્યારે સિંક થાય છે.",
            "demo_pages_title": "તમે કયા પેજ ખોલી શકો",
            "demo_page_1": "ડેશબોર્ડ: મુખ્ય એક્શન અને આંકડા.",
            "demo_page_2": "Agent/Kiosk Mode: સિંગલ અસિસ્ટેડ વર્કફ્લો.",
            "demo_page_3": "Fraud Impact Report: સિમ્યુલેટર પરિણામો.",
            "demo_page_4": "Professor Walkthrough: સ્ક્રિપ્ટેડ ડેમો સ્ટોરી.",
            "demo_page_5": "Change Log: ફેરફારો માટે જૂના/નવા મૂલ્યો.",
            "sync_queue_title": "ઓફલાઇન સિંક કતાર",
            "sync_queue_subtitle": "રાત્રે સિંક માટે રાહ જોતા લોકલ ટ્રાન્ઝેક્શન",
        },
        "de": {
            "lang_label": "Sprache",
            "language_label": "Sprache",
            "title": "RuralShield",
            "subtitle": "Offline-First-Sicherheitsprototyp für ländliches digitales Banking",
            "page_title_customer_dashboard": "Kundenportal - RuralShield",
            "page_title_customer_history": "Transaktionsverlauf - RuralShield",
            "cust_open_history": "Transaktionsverlauf öffnen",
            "cust_history_pin_note": "PIN wird benötigt, um Beträge und Empfänger zu entschlüsseln.",
            "cust_unlock_history": "Verlauf entsperren",
            "cust_view_history": "Verlauf ansehen",
            "cust_history_table_title": "Entschlüsselte Transaktionen",
            "cust_use_history": "Nutze Customer History, um deine Transaktionen zu sehen.",
            "cust_safety_settings_title": "Sicherheitseinstellungen",
            "cust_trusted_current": "Vertrauensperson:",
            "cust_freeze_until": "Gesperrt bis:",
            "back_to_dashboard": "Zurück zum Dashboard",
            "page_title_dashboard": "RuralShield Demo",
            "page_title_users": "Benutzerliste - RuralShield",
            "page_title_transactions": "Transaktionen - RuralShield",
            "page_title_transaction_list": "Transaktionsliste - RuralShield",
            "page_title_change_log": "Änderungsprotokoll - RuralShield",
            "page_title_report": "Sicherheitsbericht - RuralShield",
            "page_title_impact": "Betrugswirkungsbericht - RuralShield",
            "page_title_demo_guide": "Demo-Leitfaden - RuralShield",
            "page_title_demo_walkthrough": "Professor-Demo-Walkthrough - RuralShield",
            "page_title_agent": "Agentenmodus - RuralShield",
            "page_title_audit": "Audit-Ereignisse - RuralShield",
            "page_title_sync_queue": "Sync-Warteschlange - RuralShield",
            "users": "Benutzer",
            "transactions": "Transaktionen",
            "pending_sync": "Ausstehende Synchronisierung",
            "synced": "Synchronisiert",
            "held": "Zur Prüfung gehalten",
            "blocked": "Blockiert",
            "released": "Freigegeben",
            "high_risk": "Hohes Risiko",
            "audit_events": "Audit-Ereignisse",
            "audit_events_title": "Audit-Ereignisse",
            "section_1": "1. Benutzer registrieren / ersetzen",
            "section_2": "2. Sichere Transaktion erstellen",
            "section_3": "3. Transaktionen ansehen",
            "section_4": "4. Synchronisieren und Audit",
            "section_5": "5. Betrugsszenario-Simulator",
            "agent_title": "Agent/Kiosk-Assistentenmodus",
            "agent_subtitle": "Einzelbildschirm-Workflow für Geschäftskorrespondenten",
            "agent_user": "Benutzer-ID",
            "agent_phone": "Telefonnummer",
            "agent_pin": "PIN",
            "agent_amount": "Betrag",
            "agent_recipient": "Empfänger",
            "agent_trusted": "Vertrauenskontakt (optional)",
            "agent_submit": "Sichere Assisted-Transaktion starten",
            "agent_result": "Ergebnis der Assisted-Transaktion",
            "voice_play": "Sicherheitsanleitung vorlesen",
            "report_title": "Betrugswirkungsbericht",
            "report_subtitle": "Gemessene Simulatorergebnisse für Anti-Betrugs-Kontrollen",
            "report_runs": "Szenario-Läufe",
            "report_txs": "Simulierte Transaktionen",
            "report_protection": "Schutzrate",
            "report_avg_risk": "Durchschnittlicher Risikoscore",
            "report_recent": "Letzte Simulationen",
            "report_breakdown": "Szenario-Aufschlüsselung",
            "scenario_user": "Simulations-Benutzer-ID",
            "scenario_pin": "Simulations-PIN",
            "scenario_contact": "Vertrauenskontakt (optional)",
            "scenario_choice": "Szenario",
            "run_scenario_btn": "Szenario ausführen",
            "save_user": "Benutzer speichern",
            "set_trusted": "Vertrauenskontakt festlegen",
            "enable_freeze": "Panik-Sperre aktivieren",
            "create_tx": "Transaktion erstellen",
            "open_tx_list": "Transaktionsliste öffnen",
            "sync_pending": "Ausstehende Transaktionen synchronisieren",
            "release_held": "Gehaltene Transaktion freigeben",
            "check_audit": "Audit prüfen",
            "seed_demo": "Demo-Daten erzeugen",
            "export_report": "Sicherheitsbericht exportieren",
            "export_change_log": "Änderungsprotokoll exportieren (CSV)",
            "agent_mode": "Agent/Kiosk-Modus öffnen",
            "impact_report": "Betrugswirkungsbericht",
            "demo_walkthrough": "Professor-Demo-Walkthrough starten",
            "demo_guide": "Demo-Leitfaden",
            "clear_messages": "Nachrichten löschen",
            "sync_queue_open": "Sync-Warteschlange öffnen",
            "more_tools": "Weitere Tools",
            "replace_user": "Bestehenden Benutzer ersetzen",
            "ph_user_id_example": "Benutzer-ID (z. B. u1)",
            "ph_phone_example": "Telefon (z. B. +919999999999)",
            "ph_pin_4digit": "4-stellige PIN",
            "ph_user_id_trusted": "Benutzer-ID für Vertrauenskontakt",
            "ph_pin": "PIN",
            "ph_trusted_contact": "Telefon oder ID des Vertrauenskontakts",
            "ph_user_id_freeze": "Benutzer-ID für Panik-Freeze",
            "ph_freeze_minutes": "Freeze-Minuten",
            "ph_user_id": "Benutzer-ID",
            "ph_amount": "Betrag",
            "ph_recipient_name": "Name des Empfängers",
            "ph_limit": "Limit",
            "ph_server_url": DEFAULT_SERVER_URL,
            "ph_held_tx_id": "Gehaltene Transaktions-ID",
            "ph_approval_code": "Vertrauenskode (falls erforderlich)",
            "tx_list_title": "Transaktionsliste",
            "user_label": "Benutzer",
            "time": "Zeit",
            "tx_id": "Transaktions-ID",
            "amount": "Betrag",
            "recipient": "Empfänger",
            "risk": "Risiko",
            "action": "Aktion",
            "reasons": "Gründe",
            "guidance": "Hinweise",
            "approval": "Freigabe",
            "status": "Status",
            "back_dashboard": "Zurück zum Dashboard",
            "retrying": "Erneuter Versuch",
            "sync_state": "Sync-Status",
            "retry_count": "Anzahl Versuche",
            "next_retry": "Nächster Versuch",
            "last_error": "Letzter Fehler",
            "outbox_id": "Outbox-ID",
            "simulate_night_sync": "Nachtsync simulieren",
            "failed_attempts": "Fehlgeschlagene Versuche",
            "last_auth": "Letzte Authentifizierung",
            "trusted_contact": "Vertrauenskontakt",
            "freeze_until": "Sperre bis",
            "created_at": "Erstellt am",
            "required": "Erforderlich",
            "demo_code": "Demo-Freigabecode",
            "how_read_title": "So lesen Sie das",
            "how_read_pending": "Pending Sync bedeutet lokal gespeichert und wartet auf Server-Sync.",
            "how_read_blocked": "Blockiert bedeutet, dass die Richtlinie die Transaktion verhindert hat.",
            "how_read_risk": "Risiko und Aktion erklären den nötigen Sicherheitsschritt.",
            "recent_change_log": "Aktuelles Änderungsprotokoll",
            "change_entity": "Objekt",
            "change_field": "Feld",
            "change_old": "Alt",
            "change_new": "Neu",
            "change_log_full": "Vollständiges Änderungsprotokoll öffnen",
            "list_all_title": "Alle Transaktionen",
            "list_pending_title": "Ausstehende Synchronisierungen",
            "list_synced_title": "Synchronisierte Transaktionen",
            "list_held_title": "Gehaltene Transaktionen",
            "list_blocked_title": "Blockierte Transaktionen",
            "list_high_risk_title": "Transaktionen mit hohem Risiko",
            "list_subtitle": "Lokale Transaktionsmetadaten (Beträge verschlüsselt)",
            "users_list_title": "Benutzerliste",
            "transactions_meta_note": "Beträge und Empfänger sind lokal verschlüsselt und nur mit PIN sichtbar.",
            "audit_events_subtitle": "Append-only Audit-Chain-Protokoll",
            "audit_event_type": "Ereignistyp",
            "audit_log_id": "Log-ID",
            "change_log_title": "Änderungsprotokoll",
            "change_log_subtitle": "Lokale Änderungen mit alten/neuen Werten",
            "change_actor": "Akteur",
            "change_source": "Quelle",
            "report_snapshot_title": "Sicherheitsbericht",
            "report_snapshot_subtitle": "Lokaler Snapshot mit Audit-Integrität",
            "report_generated_at": "Erstellt am",
            "report_audit_valid": "Audit gültig",
            "report_entries_checked": "Geprüfte Einträge",
            "report_audit_error": "Audit-Fehler",
            "report_download_json": "JSON herunterladen",
            "report_no_data": "Noch keine Simulatordaten. Unten klicken, um Demo zu erzeugen.",
            "report_seed_demo": "Impact-Demo erzeugen",
            "demo_walkthrough_title": "Professor-Demo-Walkthrough",
            "demo_walkthrough_subtitle": "Deterministische Schritt-für-Schritt-Story für die Präsentation",
            "demo_user_id": "Benutzer-ID",
            "demo_pin": "PIN",
            "demo_trusted_hint": "Hinweis Vertrauenskontakt",
            "demo_release_done": "Vertrauensfreigabe abgeschlossen",
            "demo_yes": "Ja",
            "demo_no": "Nein",
            "demo_script_title": "Was sagen (Kurzskript)",
            "demo_step_a_title": "Schritt A: Normale Transaktion mit geringem Risiko",
            "demo_step_b_title": "Schritt B: Scam-ähnliche Überweisung an unbekannten Empfänger",
            "demo_step_c_title": "Schritt C: Panik-Freeze blockiert ausgehende Überweisung",
            "demo_point_1": "Transaktionsdaten sind verschlüsselt und werden zuerst offline gespeichert.",
            "demo_point_2": "Risikobewertung kennzeichnet verdächtige Muster mit erklärbaren Gründen.",
            "demo_point_3": "Hochrisiko-Flows werden vor der Synchronisierung gehalten oder blockiert.",
            "demo_point_4": "Vertrauenskontakt-Freigabe und Panik-Freeze verhindern sofortigen Betrugsverlust.",
            "demo_point_5": "Alle Entscheidungen sind in der lokalen UI für assistierte ländliche Abläufe sichtbar.",
            "demo_guide_title": "Demo-Leitfaden",
            "demo_guide_subtitle": "Alles, was Sie brauchen, um das Portal klar zu erklären",
            "demo_about_title": "Worum es im Portal geht",
            "demo_about_body": "RuralShield ist ein Offline-First-Cybersicherheitsframework für ländliches digitales Banking. Es schützt Daten auf dem Gerät, erkennt Risiken lokal und synchronisiert sicher bei verfügbarer Verbindung.",
            "demo_features_title": "Kernfunktionen",
            "demo_feature_1": "Verschlüsselte lokale Speicherung (SQLite) für Benutzer und Transaktionen.",
            "demo_feature_2": "Betrugsrisiko-Scoring mit erklärbaren Gründen.",
            "demo_feature_3": "Sicherheitsmaßnahmen: erlauben, Step-up, halten oder blockieren.",
            "demo_feature_4": "Freigabe durch Vertrauenskontakt für riskante Überweisungen.",
            "demo_feature_5": "Panik-Sperre blockiert ausgehende Transfers bei Verdacht.",
            "demo_feature_6": "Audit-Chain für Manipulationsnachweis.",
            "demo_feature_7": "Offline-Outbox und sichere Synchronisierung.",
            "demo_steps_title": "So demoen (Kurzschritte)",
            "demo_step_1": "Falls nötig, Demo-Daten im Dashboard erzeugen.",
            "demo_step_2": "Normale Transaktion erstellen, um den Low-Risk-Flow zu zeigen.",
            "demo_step_3": "Hoher Betrag + neuer Empfänger, um Hold/Block zu zeigen.",
            "demo_step_4": "Held Transaction mit Freigabecode freigeben.",
            "demo_step_5": "Fraud Impact Report öffnen, um Metriken zu zeigen.",
            "demo_step_6": "Professor Walkthrough öffnen für das Skript.",
            "demo_data_title": "Wo die Daten gespeichert sind",
            "demo_data_1": "Primärspeicher: lokale SQLite-Datenbank.",
            "demo_data_2": "Änderungsprotokoll: alte/neue Werte lokal, exportierbar als CSV.",
            "demo_data_3": "Synchronisierung erfolgt später bei sicherer Verbindung.",
            "demo_pages_title": "Seiten, die Sie öffnen können",
            "demo_page_1": "Dashboard: Hauptaktionen und Statistiken.",
            "demo_page_2": "Agent/Kiosk-Modus: Assisted-Workflow.",
            "demo_page_3": "Fraud Impact Report: Simulator-Ergebnisse.",
            "demo_page_4": "Professor Walkthrough: Skripted Demo-Story.",
            "demo_page_5": "Change Log: alte/neue Werte für Änderungen.",
            "sync_queue_title": "Offline-Sync-Warteschlange",
            "sync_queue_subtitle": "Lokale Transaktionen warten auf den Nachtsync",
        },
    }
    base = bundles["en"]
    localized = bundles.get(lang, {})
    return {**base, **localized}


def _t(lang: str, key: str) -> str:
    dictionary = {
        "en": {
            "no_alert": "No alert triggers",
            "tx_saved": "Secure transaction saved successfully.",
            "risk_label": "Risk:",
            "decision_label": "Decision:",
            "status_label": "Status:",
            "reason_label": "Reason:",
            "guidance_label": "Guidance:",
            "scenario_ran": "Scenario executed",
            "created_count": "Transactions generated",
            "agent_done": "Assisted transaction processed.",
            "change_log_exported": "Change log exported to",
            "failed_attempts": "Failed Attempts",
            "last_auth": "Last Auth",
            "trusted_contact": "Trusted Contact",
            "freeze_until": "Freeze Until",
            "created_at": "Created At",
            "trusted_required": "Trusted approval required",
            "contact_ending": "contact ending",
            "demo_code": "Demo approval code",
            "required": "Required",
            "not_required": "Not required",
            "sync_completed": "Sync completed",
            "audit_valid": "Audit chain valid",
            "entries_checked": "Entries checked",
            "audit_invalid": "Audit chain invalid",
            "demo_seeded": "Demo data seeded. Use user_id=demo_user and pin=1234.",
            "release_success": "Held transaction released and queued for sync.",
            "release_failed": "Release failed: transaction not found, not in HOLD state, or approval invalid.",
            "trusted_updated": "Trusted contact updated for user",
            "freeze_enabled": "Panic freeze enabled until",
            "invalid_pin_existing": "Invalid PIN for existing user.",
            "night_sync_done": "Night sync simulated: {count} transactions marked synced.",
            "face_required": "Face verification is required before login.",
            "customer_login_failed": "Customer login failed. Check user ID or PIN.",
            "admin_login_failed": "Admin login failed. Check username or password.",
            "invalid_role": "Invalid login role selected.",
            "not_logged_in": "Session expired. Please log in again.",
        },
        "hi": {
            "no_alert": "कोई अलर्ट ट्रिगर नहीं",
            "tx_saved": "सुरक्षित लेनदेन सफलतापूर्वक सहेजा गया।",
            "risk_label": "रिस्क:",
            "decision_label": "निर्णय:",
            "status_label": "स्थिति:",
            "reason_label": "कारण:",
            "guidance_label": "सलाह:",
            "scenario_ran": "सीनारियो चलाया गया",
            "created_count": "निर्मित लेनदेन",
            "agent_done": "असिस्टेड लेनदेन प्रोसेस हुआ।",
            "change_log_exported": "चेंज लॉग निर्यात हुआ",
            "failed_attempts": "विफल प्रयास",
            "last_auth": "अंतिम लॉगिन",
            "trusted_contact": "विश्वसनीय संपर्क",
            "freeze_until": "फ्रीज़ समय तक",
            "created_at": "निर्मित समय",
            "trusted_required": "विश्वसनीय स्वीकृति आवश्यक",
            "contact_ending": "अंतिम अंक",
            "demo_code": "डेमो स्वीकृति कोड",
            "required": "आवश्यक",
            "not_required": "आवश्यक नहीं",
            "sync_completed": "सिंक पूर्ण",
            "audit_valid": "ऑडिट चेन वैध",
            "entries_checked": "जाँची गई प्रविष्टियाँ",
            "audit_invalid": "ऑडिट चेन अमान्य",
            "demo_seeded": "डेमो डेटा तैयार। user_id=demo_user और pin=1234 उपयोग करें।",
            "release_success": "रुका हुआ लेनदेन जारी कर दिया गया और सिंक कतार में भेजा गया।",
            "release_failed": "रिलीज़ विफल: लेनदेन नहीं मिला, HOLD में नहीं है, या स्वीकृति गलत है।",
            "trusted_updated": "उपयोगकर्ता के लिए विश्वसनीय संपर्क अपडेट किया गया",
            "freeze_enabled": "पैनिक फ्रीज़ सक्रिय, समय तक",
            "invalid_pin_existing": "मौजूदा उपयोगकर्ता के लिए PIN अमान्य है।",
            "night_sync_done": "नाइट सिंक सिम्युलेट हुआ: {count} लेनदेन सिंक चिह्नित।",
            "cust_account_overview": "खाता सारांश",
            "cust_balance_demo_label": "बैलेंस (डेमो)",
            "cust_offline_first_note": "ऑफलाइन-फर्स्ट: लेनदेन पहले फोन में सुरक्षित सहेजे जाते हैं और इंटरनेट मिलने पर सिंक होते हैं।",
            "cust_quick_actions": "त्वरित कार्य",
            "cust_send_money": "पैसे भेजें",
            "cust_view_transactions": "लेनदेन देखें",
            "cust_safety_settings": "सुरक्षा सेटिंग्स",
            "cust_alerts": "अलर्ट",
            "cust_alert_new_device_title": "नया डिवाइस मिला:",
            "cust_alert_new_device_body": "कुछ लेनदेन समीक्षा के लिए रोके जा सकते हैं।",
            "cust_alert_held_title": "रोके गए लेनदेन:",
            "cust_alert_held_body": "{count} लेनदेन समीक्षा/विश्वसनीय स्वीकृति के लिए प्रतीक्षा में है।",
            "cust_alert_pending_title": "सिंक लंबित:",
            "cust_alert_pending_body": "{count} लेनदेन इंटरनेट मिलने पर सिंक होंगे।",
            "cust_alert_clear_title": "सब ठीक:",
            "cust_alert_clear_body": "अभी कोई तात्कालिक सुरक्षा अलर्ट नहीं।",
            "cust_mini_statement": "मिनी स्टेटमेंट (अंतिम 5)",
            "cust_mini_statement_note": "गोपनीयता: PIN के बिना राशि/प्राप्तकर्ता डिक्रिप्ट नहीं दिखते।",
            "cust_no_transactions": "अभी कोई लेनदेन नहीं।",
            "cust_sync_status": "सिंक स्थिति",
            "cust_last_sync": "अंतिम सिंक",
            "cust_offline_mode": "ऑफलाइन मोड: लेनदेन कतार में रहेगा और बाद में सिंक होगा।",
            "cust_send_money_offline": "पैसे भेजें (ऑफलाइन-फर्स्ट)",
            "cust_send_result_note": "परिणाम: अनुमति, समीक्षा हेतु रोक, या सुरक्षा हेतु ब्लॉक।",
            "cust_tx_history": "लेनदेन इतिहास",
            "cust_history_privacy_note": "गोपनीयता के लिए, PIN डालकर डिक्रिप्टेड इतिहास देखें।",
            "cust_risk_safe": "सुरक्षित",
            "cust_risk_warning": "चेतावनी",
            "cust_details": "विवरण",
            "cust_view": "देखें",
            "cust_tx_details": "लेनदेन विवरण",
            "cust_unlock": "विवरण खोलें",
            "cust_enter_pin_to_view": "राशि और प्राप्तकर्ता देखने के लिए PIN डालें।",
            "cust_why_title": "स्थिति का कारण",
        },
        "or": {
            "no_alert": "କୌଣସି ଆଲର୍ଟ ଟ୍ରିଗର ହୋଇନି",
            "tx_saved": "ସୁରକ୍ଷିତ ଟ୍ରାନ୍ଜାକ୍ସନ ସଫଳତାର ସହିତ ସେଭ୍ ହେଲା।",
            "risk_label": "ଝୁମ୍ପ:",
            "decision_label": "ନିଷ୍ପତ୍ତି:",
            "status_label": "ସ୍ଥିତି:",
            "reason_label": "କାରଣ:",
            "guidance_label": "ପରାମର୍ଶ:",
            "scenario_ran": "ପରିସ୍ଥିତି ଚାଲିଲା",
            "created_count": "ସୃଷ୍ଟି ହୋଇଥିବା ଟ୍ରାନ୍ଜାକ୍ସନ",
            "agent_done": "ସହାୟିତ ଟ୍ରାନ୍ଜାକ୍ସନ ପ୍ରସେସ୍ ହେଲା।",
            "change_log_exported": "ଚେଞ୍ଜ ଲଗ୍ ନିର୍ଯାତ ହେଲା",
            "failed_attempts": "ବିଫଳ ପ୍ରୟାସ",
            "last_auth": "ଶେଷ ଲଗଇନ",
            "trusted_contact": "ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ",
            "freeze_until": "ଫ୍ରିଜ୍ ସମୟ",
            "created_at": "ସୃଷ୍ଟି ସମୟ",
            "trusted_required": "ଭରସାଯୋଗ୍ୟ ସ୍ୱୀକୃତି ଆବଶ୍ୟକ",
            "contact_ending": "ଶେଷ ଅଙ୍କ",
            "demo_code": "ଡେମୋ ସ୍ୱୀକୃତି କୋଡ୍",
            "required": "ଆବଶ୍ୟକ",
            "not_required": "ଆବଶ୍ୟକ ନୁହେଁ",
            "sync_completed": "ସିଙ୍କ ସମାପ୍ତ",
            "audit_valid": "ଅଡିଟ୍ ଚେନ୍ ବୈଧ",
            "entries_checked": "ଯାଞ୍ଚିତ ଏଣ୍ଟ୍ରି",
            "audit_invalid": "ଅଡିଟ୍ ଚେନ୍ ଅବୈଧ",
            "demo_seeded": "ଡେମୋ ଡାଟା ପ୍ରସ୍ତୁତ। user_id=demo_user ଏବଂ pin=1234 ବ୍ୟବହାର କରନ୍ତୁ।",
            "release_success": "ହୋଲ୍ଡ ଟ୍ରାନ୍ଜାକ୍ସନ ରିଲିଜ୍ ହେଲା ଏବଂ ସିଙ୍କ ପାଇଁ ପଠାଗଲା।",
            "release_failed": "ରିଲିଜ୍ ବିଫଳ: ଟ୍ରାନ୍ଜାକ୍ସନ ମିଳିଲା ନାହିଁ, HOLD ନୁହେଁ, କିମ୍ବା ସ୍ୱୀକୃତି ଭୁଲ।",
            "trusted_updated": "ଉପଯୋଗକର୍ତ୍ତା ପାଇଁ ଭରସାଯୋଗ୍ୟ ସଂଯୋଗ ଅଦ୍ୟତନ",
            "freeze_enabled": "ପ୍ୟାନିକ ଫ୍ରିଜ୍ ସକ୍ରିୟ, ସମୟ ପର୍ଯ୍ୟନ୍ତ",
            "invalid_pin_existing": "ପୂର୍ବରୁ ଥିବା ବ୍ୟବହାରକାରୀ ପାଇଁ PIN ଅବୈଧ।",
            "night_sync_done": "ନାଇଟ୍ ସିଙ୍କ ସିମ୍ୟୁଲେଟ୍: {count} ଟ୍ରାନ୍ଜାକ୍ସନ ସିଙ୍କ ଚିହ୍ନିତ।",
            "cust_account_overview": "ଆକାଉଣ୍ଟ ସାରାଂଶ",
            "cust_balance_demo_label": "ବ୍ୟାଲାନ୍ସ (ଡେମୋ)",
            "cust_offline_first_note": "ଅଫଲାଇନ-ଫର୍ଷ୍ଟ: ଟ୍ରାନ୍ଜାକ୍ସନ ପ୍ରଥମେ ଫୋନରେ ସୁରକ୍ଷିତ ସେଭ୍ ହୁଏ, ପରେ ଇଣ୍ଟରନେଟ ମିଳିଲେ ସିଙ୍କ ହୁଏ।",
            "cust_quick_actions": "ତ୍ୱରିତ କାର୍ଯ୍ୟ",
            "cust_send_money": "ଟଙ୍କା ପଠାନ୍ତୁ",
            "cust_view_transactions": "ଟ୍ରାନ୍ଜାକ୍ସନ ଦେଖନ୍ତୁ",
            "cust_safety_settings": "ସୁରକ୍ଷା ସେଟିଙ୍ଗ୍ସ",
            "cust_alerts": "ଆଲର୍ଟ",
            "cust_alert_new_device_title": "ନୂଆ ଡିଭାଇସ ଚିହ୍ନଟ:",
            "cust_alert_new_device_body": "କିଛି ଟ୍ରାନ୍ଜାକ୍ସନ ସମୀକ୍ଷା ପାଇଁ ରୋକାଯାଇପାରେ।",
            "cust_alert_held_title": "ହେଲ୍ଡ ଟ୍ରାନ୍ଜାକ୍ସନ:",
            "cust_alert_held_body": "{count} ଟ୍ରାନ୍ଜାକ୍ସନ ସମୀକ୍ଷା/ଭରସାଯୋଗ୍ୟ ଅନୁମୋଦନ ପାଇଁ ଅପେକ୍ଷାରତ।",
            "cust_alert_pending_title": "ସିଙ୍କ ଅପେକ୍ଷାରତ:",
            "cust_alert_pending_body": "{count} ଟ୍ରାନ୍ଜାକ୍ସନ ଇଣ୍ଟରନେଟ ମିଳିଲେ ସିଙ୍କ ହେବ।",
            "cust_alert_clear_title": "ସବୁ ଠିକ୍:",
            "cust_alert_clear_body": "ବର୍ତ୍ତମାନ କୌଣସି ତ୍ୱରିତ ସୁରକ୍ଷା ଆଲର୍ଟ ନାହିଁ।",
            "cust_mini_statement": "ମିନି ଷ୍ଟେଟମେଣ୍ଟ (ଶେଷ 5)",
            "cust_mini_statement_note": "ଗୋପନୀୟତା: PIN ବିନା ରାଶି/ପ୍ରାପ୍ତକର୍ତ୍ତା ଡିକ୍ରିପ୍ଟ ହେବ ନାହିଁ।",
            "cust_no_transactions": "ଏଯାବତ କୌଣସି ଟ୍ରାନ୍ଜାକ୍ସନ ନାହିଁ।",
            "cust_sync_status": "ସିଙ୍କ ସ୍ଥିତି",
            "cust_last_sync": "ଶେଷ ସିଙ୍କ",
            "cust_offline_mode": "ଅଫଲାଇନ ମୋଡ୍: ଟ୍ରାନ୍ଜାକ୍ସନ କ୍ୟୁ ହେବ ଏବଂ ପରେ ସିଙ୍କ ହେବ।",
            "cust_send_money_offline": "ଟଙ୍କା ପଠାନ୍ତୁ (ଅଫଲାଇନ-ଫର୍ଷ୍ଟ)",
            "cust_send_result_note": "ପରିଣାମ: ଅନୁମତି, ସମୀକ୍ଷା ପାଇଁ ରୋକ, କିମ୍ବା ସୁରକ୍ଷା ପାଇଁ ବ୍ଲକ୍।",
            "cust_tx_history": "ଟ୍ରାନ୍ଜାକ୍ସନ ଇତିହାସ",
            "cust_history_privacy_note": "ଗୋପନୀୟତା ପାଇଁ, PIN ଦେଇ ଡିକ୍ରିପ୍ଟ ଇତିହାସ ଦେଖନ୍ତୁ।",
            "cust_risk_safe": "ସୁରକ୍ଷିତ",
            "cust_risk_warning": "ସତର୍କ",
            "cust_details": "ବିବରଣୀ",
            "cust_view": "ଦେଖନ୍ତୁ",
            "cust_tx_details": "ଟ୍ରାନ୍ଜାକ୍ସନ ବିବରଣୀ",
            "cust_unlock": "ବିବରଣୀ ଅନଲକ୍ କରନ୍ତୁ",
            "cust_enter_pin_to_view": "ରାଶି ଏବଂ ପ୍ରାପ୍ତକର୍ତ୍ତା ଦେଖିବା ପାଇଁ PIN ଦିଅନ୍ତୁ।",
            "cust_why_title": "ଏହି ସ୍ଥିତି କାହିଁକି",
        },
        "gu": {
            "no_alert": "કોઈ એલર્ટ ટ્રિગર નથી",
            "tx_saved": "સુરક્ષિત ટ્રાન્ઝેક્શન સફળતાપૂર્વક સંગ્રહાયું.",
            "risk_label": "જોખમ:",
            "decision_label": "નિર્ણય:",
            "status_label": "સ્થિતિ:",
            "reason_label": "કારણ:",
            "guidance_label": "માર્ગદર્શન:",
            "scenario_ran": "સીનારિયો ચાલ્યું",
            "created_count": "બનાવેલા ટ્રાન્ઝેક્શન્સ",
            "agent_done": "સહાયિત ટ્રાન્ઝેક્શન પ્રક્રિયા થયું.",
            "change_log_exported": "ચેન્જ લોગ નિકાસ થયો",
            "failed_attempts": "નિષ્ફળ પ્રયાસો",
            "last_auth": "છેલ્લું પ્રમાણીકરણ",
            "trusted_contact": "વિશ્વસનીય સંપર્ક",
            "freeze_until": "ફ્રીઝ સુધી",
            "created_at": "બનાવ્યા નો સમય",
            "trusted_required": "વિશ્વસનીય મંજૂરી જરૂરી",
            "contact_ending": "અંતિમ અંક",
            "demo_code": "ડેમો મંજૂરી કોડ",
            "required": "આવશ્યક",
            "not_required": "આવશ્યક નથી",
            "sync_completed": "સિંક પૂર્ણ",
            "audit_valid": "ઑડિટ ચેઇન માન્ય",
            "entries_checked": "ચકાસેલી એન્ટ્રીઓ",
            "audit_invalid": "ઑડિટ ચેઇન અમાન્ય",
            "demo_seeded": "ડેમો ડેટા સીડ થયું. user_id=demo_user અને pin=1234 વાપરો.",
            "release_success": "રોકાયેલ ટ્રાન્ઝેક્શન રિલીઝ થયું અને સિંક માટે કતારબદ્ધ છે.",
            "release_failed": "રિલીઝ નિષ્ફળ: ટ્રાન્ઝેક્શન મળ્યું નહીં, HOLD સ્થિતિમાં નથી, અથવા મંજૂરી અમાન્ય.",
            "trusted_updated": "વપરાશકર્તા માટે વિશ્વસનીય સંપર્ક અપડેટ થયો",
            "freeze_enabled": "પેનિક ફ્રીઝ સક્રિય થયું જ્યાં સુધી",
            "invalid_pin_existing": "હાજર વપરાશકર્તા માટે PIN અમાન્ય છે.",
            "night_sync_done": "નાઇટ સિંક સિમ્યુલેટ થયું: {count} ટ્રાન્ઝેક્શન સિંક તરીકે ચિહ્નિત.",
            "cust_account_overview": "ખાતાનું સારાંશ",
            "cust_balance_demo_label": "બેલેન્સ (ડેમો)",
            "cust_offline_first_note": "ઓફલાઇન-ફર્સ્ટ: લેનદેન પહેલા ફોનમાં સુરક્ષિત સંગ્રહાય છે અને ઇન્ટરનેટ મળતા જ સિંક થાય છે.",
            "cust_quick_actions": "ઝડપી ક્રિયાઓ",
            "cust_send_money": "પૈસા મોકલો",
            "cust_view_transactions": "લેનદેન જુઓ",
            "cust_safety_settings": "સેફ્ટી સેટિંગ્સ",
            "cust_alerts": "અલર્ટ્સ",
            "cust_alert_new_device_title": "નવું ડિવાઇસ મળ્યું:",
            "cust_alert_new_device_body": "કેટલાંક લેનદેન સમીક્ષા માટે રોકાઈ શકે છે.",
            "cust_alert_held_title": "રોકાયેલ લેનદેન:",
            "cust_alert_held_body": "{count} લેનદેન સમીક્ષા/વિશ્વસનીય મંજૂરી માટે રાહ જોઈ રહ્યું છે.",
            "cust_alert_pending_title": "સિંક બાકી:",
            "cust_alert_pending_body": "{count} લેનદેન ઇન્ટરનેટ મળતા જ સિંક થશે.",
            "cust_alert_clear_title": "બધું ઠીક:",
            "cust_alert_clear_body": "હમણાં કોઈ તાત્કાલિક સુરક્ષા અલર્ટ નથી.",
            "cust_mini_statement": "મિની સ્ટેટમેન્ટ (છેલ્લા 5)",
            "cust_mini_statement_note": "પ્રાઈવસી: PIN વગર રકમ/પ્રાપ્તકર્તા ડિક્રિપ્ટ દેખાતું નથી.",
            "cust_no_transactions": "હજી કોઈ લેનદેન નથી.",
            "cust_sync_status": "સિંક સ્થિતિ",
            "cust_last_sync": "છેલ્લો સિંક",
            "cust_offline_mode": "ઓફલાઇન: લેનદેન કતારમાં રહેશે અને પછી સિંક થશે.",
            "cust_send_money_offline": "પૈસા મોકલો (ઓફલાઇન-ફર્સ્ટ)",
            "cust_send_result_note": "પરિણામ: મંજૂરી, સમીક્ષા માટે રોકો, અથવા સુરક્ષા માટે બ્લોક.",
            "cust_tx_history": "લેનદેન ઇતિહાસ",
            "cust_history_privacy_note": "પ્રાઈવસી માટે, PIN નાખીને ડિક્રિપ્ટેડ ઇતિહાસ જુઓ.",
            "cust_risk_safe": "સુરક્ષિત",
            "cust_risk_warning": "ચેતવણી",
            "cust_details": "વિગતો",
            "cust_view": "જુઓ",
            "cust_tx_details": "ટ્રાન્ઝેક્શન વિગતો",
            "cust_unlock": "વિગતો અનલોક",
            "cust_enter_pin_to_view": "રકમ અને પ્રાપ્તકર્તા જોવા માટે PIN નાખો.",
            "cust_why_title": "આ સ્થિતિ કેમ",
        },
        "de": {
            "no_alert": "Keine Alarme ausgelöst",
            "tx_saved": "Sichere Transaktion erfolgreich gespeichert.",
            "risk_label": "Risiko:",
            "decision_label": "Entscheidung:",
            "status_label": "Status:",
            "reason_label": "Grund:",
            "guidance_label": "Hinweis:",
            "scenario_ran": "Szenario ausgeführt",
            "created_count": "Erzeugte Transaktionen",
            "agent_done": "Assisted-Transaktion verarbeitet.",
            "change_log_exported": "Änderungsprotokoll exportiert nach",
            "failed_attempts": "Fehlgeschlagene Versuche",
            "last_auth": "Letzte Authentifizierung",
            "trusted_contact": "Vertrauenskontakt",
            "freeze_until": "Sperre bis",
            "created_at": "Erstellt am",
            "trusted_required": "Vertrauenskontakt-Freigabe erforderlich",
            "contact_ending": "Kontakt endet mit",
            "demo_code": "Demo-Freigabecode",
            "required": "Erforderlich",
            "not_required": "Nicht erforderlich",
            "sync_completed": "Synchronisierung abgeschlossen",
            "audit_valid": "Audit-Chain gültig",
            "entries_checked": "Geprüfte Einträge",
            "audit_invalid": "Audit-Chain ungültig",
            "demo_seeded": "Demo-Daten erzeugt. user_id=demo_user und pin=1234 verwenden.",
            "release_success": "Gehaltene Transaktion freigegeben und für Sync vorgemerkt.",
            "release_failed": "Freigabe fehlgeschlagen: Transaktion nicht gefunden, nicht im HOLD-Status oder Freigabe ungültig.",
            "trusted_updated": "Vertrauenskontakt aktualisiert für Benutzer",
            "freeze_enabled": "Panik-Freeze aktiv bis",
            "invalid_pin_existing": "Ungültige PIN für bestehenden Benutzer.",
            "night_sync_done": "Nachtsync simuliert: {count} Transaktionen als synchronisiert markiert.",
            "cust_account_overview": "Kontoübersicht",
            "cust_balance_demo_label": "Kontostand (Demo)",
            "cust_offline_first_note": "Offline-first: Transaktionen werden zuerst sicher auf dem Gerät gespeichert und später synchronisiert, wenn Internet verfügbar ist.",
            "cust_quick_actions": "Schnellaktionen",
            "cust_send_money": "Geld senden",
            "cust_view_transactions": "Transaktionen ansehen",
            "cust_safety_settings": "Sicherheitseinstellungen",
            "cust_alerts": "Warnungen",
            "cust_alert_new_device_title": "Neues Gerät erkannt:",
            "cust_alert_new_device_body": "Einige Transaktionen können zur Prüfung gehalten werden.",
            "cust_alert_held_title": "Gehaltene Transaktionen:",
            "cust_alert_held_body": "{count} Transaktion(en) warten auf Prüfung oder Vertrauensfreigabe.",
            "cust_alert_pending_title": "Sync ausstehend:",
            "cust_alert_pending_body": "{count} Transaktion(en) werden synchronisiert, sobald Internet verfügbar ist.",
            "cust_alert_clear_title": "Alles ok:",
            "cust_alert_clear_body": "Derzeit keine dringenden Sicherheitswarnungen.",
            "cust_mini_statement": "Mini-Auszug (letzte 5)",
            "cust_mini_statement_note": "Datenschutz: Betrag/Empfänger bleiben verschlüsselt, bis du mit PIN entsperrst.",
            "cust_no_transactions": "Noch keine Transaktionen.",
            "cust_sync_status": "Sync-Status",
            "cust_last_sync": "Letzter Sync",
            "cust_offline_mode": "Offline-Modus: Transaktionen werden zwischengespeichert und später synchronisiert.",
            "cust_send_money_offline": "Geld senden (Offline-First)",
            "cust_send_result_note": "Ergebnis: erlaubt, gehalten (Prüfung) oder blockiert (verdächtig).",
            "cust_tx_history": "Transaktionsverlauf",
            "cust_history_privacy_note": "Aus Datenschutzgründen PIN eingeben, um den Verlauf zu entschlüsseln.",
            "cust_risk_safe": "Sicher",
            "cust_risk_warning": "Warnung",
            "cust_details": "Details",
            "cust_view": "Ansehen",
            "cust_tx_details": "Transaktionsdetails",
            "cust_unlock": "Details entsperren",
            "cust_enter_pin_to_view": "PIN eingeben, um Betrag und Empfänger zu entschlüsseln.",
            "cust_why_title": "Warum dieser Status",
        },
    }
    base = dictionary["en"]
    localized = dictionary.get(lang, {})
    return {**base, **localized}.get(key, key)
