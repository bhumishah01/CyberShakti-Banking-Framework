# AFTER MIDSEM: Stepwise Progress (Last 7 Days)

This file is the "single narrative" of what we built **after midsem**, in the exact order we progressed.
It’s written so a new evaluator (or a new teammate) can understand what changed and why.

Project working name: **RuralShield**

## Core Problem Statement (Why We Started)
Smart India Hackathon PS 25205:
- Rural digital banking needs secure transactions under low-end devices and limited internet.
- Must focus on fraud detection + user authentication.
- Offline-first storage and later sync is acceptable (and preferred for rural connectivity).

After midsem, we upgraded the prototype to feel closer to a real system:
- more stable UX (no random 500s)
- admin “control room” clarity
- customer flows that feel like a real banking app (send money, safety, history)
- better explainability (why held/blocked)
- voice support (input + output) for low-literacy use

---

## Step-by-step Timeline

### Step A: Admin Portal Cleanup + Analytics Separation
Goal: keep the **dashboard simple** and push deep intelligence into **Analytics**.

What we did:
- Dashboard focused on monitoring + operations.
- Analytics page added: fraud trends, high-risk users, device monitoring, alerts, risk distribution.
- Added demo helpers (Demo Map / Guide) so professor sees a “story”, not random buttons.

Where it shows in demo:
- Bank login: `/bank`
- Dashboard: `/bank/dashboard`
- Analytics: `/bank/analytics`

Reference docs:
- `docs/STEPWISE PROGRESS/AFTER_MIDSEMS/STEPWISE PROGRESS/STEP_23_ADMIN_PORTAL_REBUILD.md`

---

### Step B: Offline Sync Queue (Outbox) + Manual Controls
Goal: demonstrate the **offline-first queue** and give staff practical control:
- sync all
- sync one
- sync selected
- release held transactions before syncing

What we did:
- Added `/sync/queue` page that reads SQLite outbox + joins transaction metadata.
- Added “Sync Selected” checkboxes for syncing only some rows.
- Remembered `server_url` to reduce retyping.
- Fixed alignment (short IDs with tooltips, stable columns).

Where it shows:
- Sync Queue: `/sync/queue`

Reference docs:
- `docs/STEPWISE PROGRESS/AFTER_MIDSEMS/STEPWISE PROGRESS/STEP_24_OFFLINE_SYNC_ENGINE_UI.md`

---

### Step C: Full Language Switching (i18n) Across All Pages
Goal: if language changes, it should apply everywhere:
- headings
- buttons
- alerts
- subpages (history, analytics, sync queue)

What we did:
- Centralized bundle-based translations and made templates use `i18n.<key>`.
- Persisted language choice via cookie so new pages remain translated.

Reference docs:
- `docs/STEPWISE PROGRESS/AFTER_MIDSEMS/STEPWISE PROGRESS/STEP_25_FULL_I18N_ACROSS_PAGES.md`

---

### Step D: Customer Portal Core Banking Flows
Goal: make customer portal complete enough to feel like a real product:
- dashboard + balance demo
- send money
- history (PIN unlock)
- safety settings
- offline indicators

What we did:
- Send money via AJAX (no redirect to error pages).
- Mini-statement, notifications, and “last transaction” decision panel.
- Safety: trusted contacts + panic freeze.

Reference docs:
- `docs/STEPWISE PROGRESS/AFTER_MIDSEMS/STEPWISE PROGRESS/STEP_26_CUSTOMER_PORTAL_CORE_FLOWS.md`

---

### Step E: Voice Assist (Input + Output)
Goal: rural usability:
- voice input parsing ("Send 500 to Ramesh")
- voice output feedback ("Success", "Under review", "Blocked")

What we did:
- Voice input:
  - typed command parsing
  - optional mic record (SpeechRecognition, browser-dependent)
- Voice output:
  - customer gets “Voice Feedback” after transaction with simple sentences
  - reasons + short safety guidance can be read aloud

Reference docs:
- `docs/STEPWISE PROGRESS/AFTER_MIDSEMS/STEPWISE PROGRESS/STEP_27_VOICE_ASSIST_INPUT_AND_OUTPUT.md`

---

### Step F: Reliability Hardening (No More Random Internal Server Errors)
Goal: demo stability.

What we fixed:
- Template rendering fallback bug that caused `'dict' object has no attribute 'split'`.
- Transaction history amount formatting issues.
- Defensive datetime parsing.
- Error logging to `data/ui_errors.log` for quick debugging.

Reference docs:
- `docs/STEPWISE PROGRESS/AFTER_MIDSEMS/STEPWISE PROGRESS/STEP_28_RELIABILITY_HARDENING.md`

---

### Step G: Face + Device Trust Stability
Goal: step-up authentication without breaking demos.

What we did:
- Face hash verification uses tolerant thresholds.
- On trusted devices, mismatch triggers “refresh template” (reduces false failures).
- On new devices, we allow login but flag risk (`FACE_WEAK`, `NEW_DEVICE`) so transactions can be held.

Reference docs:
- `docs/STEPWISE PROGRESS/AFTER_MIDSEMS/STEPWISE PROGRESS/STEP_29_FACE_AND_DEVICE_TRUST_STABILITY.md`

---

### Step H: Stronger Analytics (User-wise Deep Dive) + Demo Result Page
Goal:
- reduce confusion between “Demo Run” vs “Analytics”
- add admin user-wise analysis to look more “fintech”

What we did:
- `/bank/demo/result` shows “demo pack ready” + next buttons.
- Analytics cards became clickable.
- Added “User-wise Analytics” panel:
  - compare users (volume)
  - select a user and show patterns:
    - late-night transactions (IST)
    - failed logins
    - held/blocked counts
    - usage hour histogram
    - top fraud reasons

Reference docs:
- `docs/STEPWISE PROGRESS/AFTER_MIDSEMS/STEPWISE PROGRESS/STEP_30_USER_WISE_ANALYTICS_AND_DEMO_RESULT.md`

---

## Where Data Is Stored (After Midsem)
Offline-first local store:
- SQLite database in `data/` (mounted into UI container via docker-compose)

Server store:
- Postgres container for the central API (used by the server component)

This supports the “store locally, sync later” requirement.

---

## How To Demo In 2 Minutes (Professor Friendly)
1. Open Bank portal: `/bank`
2. Run “1‑Click Demo Run”
3. On Demo Result page, open Analytics
4. Show:
   - Risk distribution + top reasons
   - Fraud trends graph
   - High risk users
   - User-wise deep dive (late night, failed logins)
5. Open Sync Queue:
   - sync one record
   - sync selected records
   - release held transaction and then sync it
6. Open Customer portal and create a transaction:
   - show voice feedback (success/held/blocked)
