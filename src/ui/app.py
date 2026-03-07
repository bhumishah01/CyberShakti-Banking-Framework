"""Web UI for RuralShield runtime demo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.audit.chain import verify_audit_chain
from src.auth.service import create_user, enable_panic_freeze, set_trusted_contact
from src.database.init_db import init_db
from src.database.transaction_store import (
    create_secure_transaction,
    get_dashboard_stats,
    list_secure_transactions,
    release_held_transaction,
)
from src.sync.client import make_http_sender
from src.sync.manager import sync_outbox


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB = Path("data/ruralshield.db")
SUPPORTED_LANGS = {"en", "hi", "or"}

app = FastAPI(title="RuralShield UI", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _ctx(request: Request, message: str = "", error: str = "", lang: str = "en") -> dict:
    stats = get_dashboard_stats(db_path=DEFAULT_DB)
    i18n = _bundle(lang)
    return {
        "request": request,
        "message": message,
        "error": error,
        "db_path": str(DEFAULT_DB),
        "stats": stats,
        "lang": lang,
        "i18n": i18n,
        "langs": _language_choices(),
    }


@app.get("/")
def index(request: Request):
    init_db(DEFAULT_DB)
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    return templates.TemplateResponse("index.html", _ctx(request, lang=lang))


@app.post("/users")
def add_user(
    request: Request,
    user_id: str = Form(...),
    phone: str = Form(...),
    pin: str = Form(...),
    replace: str | None = Form(default=None),
    lang: str = Form(default="en"),
):
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
        return templates.TemplateResponse("index.html", _ctx(request, message=msg, lang=lang))
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html", _ctx(request, error=str(exc), lang=lang), status_code=400
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
        return templates.TemplateResponse("index.html", _ctx(request, message=msg, lang=lang))
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html", _ctx(request, error=str(exc), lang=lang), status_code=400
        )


@app.get("/transactions")
def list_transactions(request: Request, user_id: str, pin: str, limit: int = 10, lang: str = "en"):
    lang = _resolve_lang(lang)
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

        context = _ctx(request, lang=lang)
        context["transactions"] = formatted
        context["active_user"] = user_id.strip()
        return templates.TemplateResponse("transactions.html", context)
    except Exception as exc:
        context = _ctx(request, error=str(exc), lang=lang)
        context["transactions"] = []
        context["active_user"] = user_id.strip()
        return templates.TemplateResponse("transactions.html", context, status_code=400)


@app.post("/sync")
def do_sync(
    request: Request,
    server_url: str = Form("http://localhost:8000"),
    lang: str = Form(default="en"),
):
    lang = _resolve_lang(lang)
    try:
        sender = make_http_sender(server_url.strip())
        summary = sync_outbox(db_path=DEFAULT_DB, sender=sender)
        msg = (
            f"{_t(lang, 'sync_completed')}: "
            f"processed={summary.processed}, synced={summary.synced}, "
            f"duplicates={summary.duplicates}, retried={summary.retried}"
        )
        return templates.TemplateResponse("index.html", _ctx(request, message=msg, lang=lang))
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html", _ctx(request, error=str(exc), lang=lang), status_code=400
        )


@app.get("/audit")
def audit_status(request: Request):
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    result = verify_audit_chain(db_path=DEFAULT_DB)
    if result.is_valid:
        msg = f"{_t(lang, 'audit_valid')}. {_t(lang, 'entries_checked')}: {result.checked_entries}"
        return templates.TemplateResponse("index.html", _ctx(request, message=msg, lang=lang))

    err = f"{_t(lang, 'audit_invalid')}: {result.error}"
    return templates.TemplateResponse(
        "index.html", _ctx(request, error=err, lang=lang), status_code=400
    )


@app.get("/reset")
def reset_to_home(request: Request):
    lang = _resolve_lang(request.query_params.get("lang", "en"))
    return RedirectResponse(url=f"/?lang={lang}", status_code=303)


@app.post("/seed-demo")
def seed_demo_data(request: Request):
    """Insert a realistic demo user + transactions for live presentation."""
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
        return templates.TemplateResponse("index.html", _ctx(request, message=msg, lang=lang))
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html", _ctx(request, error=str(exc), lang=lang), status_code=400
        )


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


def _language_choices() -> list[dict]:
    return [
        {"code": "en", "label": "English"},
        {"code": "hi", "label": "हिंदी"},
        {"code": "or", "label": "ଓଡ଼ିଆ"},
    ]


@app.post("/transactions/release")
def release_transaction(
    request: Request,
    tx_id: str = Form(...),
    user_id: str = Form(...),
    pin: str = Form(...),
    approval_code: str = Form(default=""),
    lang: str = Form(default="en"),
):
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
            return templates.TemplateResponse(
                "index.html",
                _ctx(request, message=_t(lang, "release_success"), lang=lang),
            )
        return templates.TemplateResponse(
            "index.html",
            _ctx(request, error=_t(lang, "release_failed"), lang=lang),
            status_code=400,
        )
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html", _ctx(request, error=str(exc), lang=lang), status_code=400
        )


@app.post("/users/trusted-contact")
def update_trusted_contact(
    request: Request,
    user_id: str = Form(...),
    pin: str = Form(...),
    trusted_contact: str = Form(...),
    lang: str = Form(default="en"),
):
    lang = _resolve_lang(lang)
    try:
        set_trusted_contact(
            user_id=user_id.strip(),
            pin=pin.strip(),
            trusted_contact=trusted_contact.strip(),
            db_path=DEFAULT_DB,
        )
        return templates.TemplateResponse(
            "index.html",
            _ctx(request, message=f"{_t(lang, 'trusted_updated')} {user_id.strip()}.", lang=lang),
        )
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html", _ctx(request, error=str(exc), lang=lang), status_code=400
        )


@app.post("/users/panic-freeze")
def panic_freeze(
    request: Request,
    user_id: str = Form(...),
    pin: str = Form(...),
    minutes: int = Form(60),
    lang: str = Form(default="en"),
):
    lang = _resolve_lang(lang)
    try:
        freeze_until = enable_panic_freeze(
            user_id=user_id.strip(),
            pin=pin.strip(),
            minutes=minutes,
            db_path=DEFAULT_DB,
        )
        return templates.TemplateResponse(
            "index.html",
            _ctx(
                request,
                message=f"{_t(lang, 'freeze_enabled')} {freeze_until} ({user_id.strip()}).",
                lang=lang,
            ),
        )
    except Exception as exc:
        return templates.TemplateResponse(
            "index.html", _ctx(request, error=str(exc), lang=lang), status_code=400
        )


def _friendly_risk(level: str, lang: str = "en") -> str:
    mapping = {
        "en": {"LOW": "Low", "MEDIUM": "Medium", "HIGH": "High"},
        "hi": {"LOW": "कम", "MEDIUM": "मध्यम", "HIGH": "उच्च"},
        "or": {"LOW": "କମ୍", "MEDIUM": "ମଧ୍ୟମ", "HIGH": "ଉଚ୍ଚ"},
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
        },
        "hi": {
            "NEW_RECIPIENT": "नया प्राप्तकर्ता पहले नहीं देखा गया",
            "HIGH_AMOUNT": "राशि असामान्य रूप से अधिक है",
            "ODD_HOUR": "असामान्य समय पर लेनदेन",
            "RAPID_BURST": "कम समय में कई लेनदेन",
            "AUTH_FAILURES": "हाल में लॉगिन विफल प्रयास",
        },
        "or": {
            "NEW_RECIPIENT": "ନୂତନ ପ୍ରାପ୍ତକର୍ତ୍ତା ପୂର୍ବରୁ ଦେଖାଯାଇନି",
            "HIGH_AMOUNT": "ରାଶି ଅସାମାନ୍ୟ ଭାବେ ଅଧିକ",
            "ODD_HOUR": "ଅସାମାନ୍ୟ ସମୟରେ ଟ୍ରାନ୍ଜାକ୍ସନ",
            "RAPID_BURST": "କମ୍ ସମୟରେ ଅନେକ ଟ୍ରାନ୍ଜାକ୍ସନ",
            "AUTH_FAILURES": "ସମ୍ପ୍ରତି ଲଗଇନ ବିଫଳ ପ୍ରୟାସ",
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
    }.get(lang, {})
    return mapping.get(action, action.replace("_", " ").title())


def _resolve_lang(lang: str) -> str:
    cleaned = (lang or "en").strip().lower()
    return cleaned if cleaned in SUPPORTED_LANGS else "en"


def _bundle(lang: str) -> dict:
    bundles = {
        "en": {
            "lang_label": "Language",
            "title": "RuralShield",
            "subtitle": "Offline-First Security Prototype for Rural Digital Banking",
            "users": "Users",
            "transactions": "Transactions",
            "pending_sync": "Pending Sync",
            "synced": "Synced",
            "held": "Held",
            "blocked": "Blocked",
            "released": "Released",
            "high_risk": "High Risk",
            "audit_events": "Audit Events",
            "section_1": "1. Register / Replace User",
            "section_2": "2. Create Secure Transaction",
            "section_3": "3. View Transactions",
            "section_4": "4. Sync and Audit",
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
            "clear_messages": "Clear Messages",
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
            "how_read_title": "How To Read This",
            "how_read_pending": "Pending Sync means safely stored locally and waiting for server sync.",
            "how_read_blocked": "Blocked means risk policy prevented this transaction.",
            "how_read_risk": "Risk and action explain what safety step is required.",
        },
        "hi": {
            "lang_label": "भाषा",
            "title": "RuralShield",
            "subtitle": "ग्रामीण डिजिटल बैंकिंग के लिए ऑफलाइन-प्रथम सुरक्षा प्रोटोटाइप",
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
            "clear_messages": "संदेश साफ करें",
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
            "how_read_title": "इसे कैसे पढ़ें",
            "how_read_pending": "सिंक लंबित का अर्थ है डेटा सुरक्षित रूप से लोकल में है और सर्वर सिंक का इंतजार कर रहा है।",
            "how_read_blocked": "ब्लॉक का अर्थ है जोखिम नीति ने इस लेनदेन को रोका।",
            "how_read_risk": "रिस्क और एक्शन बताते हैं कि कौन सा सुरक्षा कदम जरूरी है।",
        },
        "or": {
            "lang_label": "ଭାଷା",
            "title": "RuralShield",
            "subtitle": "ଗ୍ରାମୀଣ ଡିଜିଟାଲ ବ୍ୟାଙ୍କିଙ୍ଗ ପାଇଁ ଅଫଲାଇନ-ପ୍ରଥମ ସୁରକ୍ଷା ପ୍ରଟୋଟାଇପ",
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
            "clear_messages": "ସନ୍ଦେଶ ସଫା କରନ୍ତୁ",
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
            "how_read_title": "ଏହାକୁ କିପରି ବୁଝିବେ",
            "how_read_pending": "ସିଙ୍କ ବାକୀ ଅର୍ଥ ତଥ୍ୟ ଲୋକାଲରେ ସୁରକ୍ଷିତ ରହିଛି ଏବଂ ସର୍ଭର ସିଙ୍କ ପ୍ରତୀକ୍ଷାରେ।",
            "how_read_blocked": "ବ୍ଲକ୍ ଅର୍ଥ ଝୁମ୍ପ ନୀତି ଏହି ଟ୍ରାନ୍ଜାକ୍ସନକୁ ରୋକିଛି।",
            "how_read_risk": "ଝୁମ୍ପ ଓ ଆକ୍ସନ୍ କହେ କେଉଁ ସୁରକ୍ଷା ପଦକ୍ଷେପ ଆବଶ୍ୟକ।",
        },
    }
    return bundles.get(lang, bundles["en"])


def _t(lang: str, key: str) -> str:
    dictionary = {
        "en": {
            "no_alert": "No alert triggers",
            "tx_saved": "Secure transaction saved successfully.",
            "risk_label": "Risk:",
            "decision_label": "Decision:",
            "reason_label": "Reason:",
            "guidance_label": "Guidance:",
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
        },
        "hi": {
            "no_alert": "कोई अलर्ट ट्रिगर नहीं",
            "tx_saved": "सुरक्षित लेनदेन सफलतापूर्वक सहेजा गया।",
            "risk_label": "रिस्क:",
            "decision_label": "निर्णय:",
            "reason_label": "कारण:",
            "guidance_label": "सलाह:",
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
        },
        "or": {
            "no_alert": "କୌଣସି ଆଲର୍ଟ ଟ୍ରିଗର ହୋଇନି",
            "tx_saved": "ସୁରକ୍ଷିତ ଟ୍ରାନ୍ଜାକ୍ସନ ସଫଳତାର ସହିତ ସେଭ୍ ହେଲା।",
            "risk_label": "ଝୁମ୍ପ:",
            "decision_label": "ନିଷ୍ପତ୍ତି:",
            "reason_label": "କାରଣ:",
            "guidance_label": "ପରାମର୍ଶ:",
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
        },
    }
    return dictionary.get(lang, dictionary["en"]).get(key, key)
