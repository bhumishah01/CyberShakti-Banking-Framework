# STEP 04: Customer Portal Core Flows (Offline-First Banking UX)

## Goal
Deliver a real “customer banking” experience for rural users:
- simple dashboard
- send money flow
- transaction history
- safety controls (trusted contacts, panic freeze)
- offline indicators + pending sync count

## What Was Implemented

### Customer Portal Dashboard
URL: `/dashboard/customer`

Shows:
- Balance (local demo balance)
- Total tx, pending sync, held tx
- Device trust + face verified indicator
- Mini statement (safe metadata)
- Notifications panel
- Alerts panel (human friendly)

### Send Money (AJAX, no error pages)
Send money is handled via:
- POST `/customer/api/transactions` (JSON)

It returns:
- decision (ALLOW/HOLD/BLOCK)
- risk score
- reason codes

The UI redirects back to the dashboard with a “last transaction” panel.

### History + Tx Details
Transaction history requires PIN (privacy):
- `/customer/history`

Tx details view:
- `/customer/tx/{tx_id}`

### Safety Settings
Includes:
- Trusted contacts set/remove
- Panic freeze (freeze outgoing transfers)

## Key Files
- Routes + context: `src/ui/app.py`
- Customer dashboard template: `src/ui/templates/customer_home.html`
- Customer history template: `src/ui/templates/customer_history.html`

## Why This Matters
This maps directly to SIH:
- lightweight fraud controls
- user authentication
- minimal UI, works offline first

