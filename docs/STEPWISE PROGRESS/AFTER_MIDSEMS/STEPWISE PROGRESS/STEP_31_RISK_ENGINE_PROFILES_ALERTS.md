# STEP 31: Risk Engine + Profiles + Alerts (Core Intelligence Layer)

## Goal
Move from "static rules" to a system that can:
- compute **adaptive risk score (0-100)** per transaction
- track a **user risk score** over time
- build **behavior profiles** (avg amount, frequency, peak hours)
- generate **alerts + notifications** for suspicious patterns

This directly supports SIH PS 25205:
fraud detection + authentication under low-connectivity and low-end devices.

## What Was Implemented

### 1. Behavior Profile (Per User)
For each user we compute and store:
- `avg_amount`
- `tx_count`
- `peak_hour_local` (based on Asia/Kolkata)
- `last_activity_at`

These values are used by the risk engine and shown in Admin Analytics.

### 2. Adaptive Risk Score (Per Transaction)
Transaction evaluation outputs:
- `risk_score` (0-100)
- `decision`: `ALLOWED` / `HELD` / `BLOCKED`
- `reason_codes`: explainable list such as:
  - `NEW_DEVICE`
  - `HIGH_AMOUNT`
  - `ODD_HOUR`
  - `RAPID_BURST`
  - `FAILED_LOGINS`

### 3. Suspicious Pattern Alerts
We detect and store alerts for:
- rapid burst of transactions (example: 5 in 2 minutes)
- multiple failed login attempts
- repeated high-risk transaction outcomes

Alerts are shown in the Admin portal.

### 4. Notifications (Customer + Admin)
We store lightweight notifications for:
- transaction queued (offline-first)
- transaction held for review
- suspicious activity detected

Customer portal shows these in a simple “Notifications” panel.
Admin portal shows alerts in monitoring panels.

## Data Storage (Offline-First)
All intelligence data is stored locally for the demo (SQLite) so it works offline:
- user profiles
- devices
- alerts
- notifications

The system can later sync these to server storage.

## Key Files
- DB schema: `src/db/init_db.py`
- Fraud engine: `src/fraud/engine.py`
- Fraud rules: `src/fraud/rules.py`
- Alert generation: `src/fraud/alerts.py`
- Device tracking: `src/auth/device.py`

## Demo Pages
- Admin Analytics: `/bank/analytics`
- High-risk users + alerts panels: included on Analytics
- Customer Notifications: `/dashboard/customer`

