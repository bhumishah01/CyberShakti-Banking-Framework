# STEP 34: Weekly Progress Breakdown (What We Did, In Order)

This is a **detailed, week-style** progress log for after-midsem work, written in the order things were built and fixed.
It is designed so you can explain your GitHub progress to your professor without missing steps.

## Week Focus
- Make portals feel “real”: customer + bank admin
- Remove internal server errors
- Make offline-first sync visible and controllable
- Add explainable fraud intelligence (risk score + reasons)
- Add accessibility: multilingual UI + voice assist

## Timeline (Grouped By Milestone)

### 1) Portal Split + Stable Navigation
What changed:
- Clear landing: choose **Customer** or **Bank/Admin**
- After login, routes go to the correct dashboards
- Admin subpages return to **bank dashboard** (not logout)

Why:
- Prevent demo confusion, reduce “random” navigation resets.

Where to see:
- Home: `/`
- Bank portal: `/bank`
- Customer portal: `/customer`

### 2) Customer Portal Core Flows (Banking UX)
What changed:
- Customer dashboard with balance + quick actions
- Send money flow (AJAX, no redirect errors)
- Transaction history unlock by PIN
- Notifications panel + mini statement
- Offline indicator + pending sync counts

Why:
- Demonstrates the real PS: secure banking on low-end devices + low internet.

### 3) Risk Engine + Behavior Profiling + Alerts
What changed:
- Adaptive risk score per transaction (0–100)
- Explainable reason codes (`NEW_DEVICE`, `HIGH_AMOUNT`, `ODD_HOUR`, etc.)
- Behavior profile per user (avg amount, tx count, peak hour)
- Alerts + notifications for suspicious patterns

Why:
- Fraud detection must be explainable to banks and usable in rural workflows.

### 4) Admin Portal + Analytics Upgrade
What changed:
- Clean admin dashboard (operations + monitoring)
- Analytics page (fraud trends, high-risk users, devices, alerts)
- Clickable summary cards
- User-wise deep dive section for patterns (late night, failed logins)

Why:
- Bank side needs “control room + evidence”, not only buttons.

### 5) Offline Sync Queue + Selective Sync Controls
What changed:
- Outbox sync queue page
- Sync one record / sync selected / sync all
- Release held transactions intentionally
- UI alignment improvements (short IDs, tooltips)

Why:
- Offline-first must show that data is stored locally and synced later.

### 6) Full Language Switching + IST Everywhere
What changed:
- Language selection persists across pages
- Headings/buttons/alerts/labels translated consistently
- All timestamps shown in **Asia/Kolkata (IST)**

Why:
- Rural usability and demo clarity.

### 7) Voice Assist (Input + Output)
What changed:
- Parse typed voice commands: `Send 500 to Ramesh`
- Mic record button for speech-to-text (browser dependent)
- Voice feedback messages after transaction outcomes

Why:
- Low literacy support (core rural constraint).

