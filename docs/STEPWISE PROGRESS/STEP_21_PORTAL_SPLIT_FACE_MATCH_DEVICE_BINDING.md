# STEP 21: Portal Split + Face Match + Device Binding

## Why We Did This (Problem Statement Alignment)

The SIH problem statement is about securing rural digital banking on low-end devices with limited connectivity:
- user authentication must work reliably
- fraud detection should happen locally
- risky behavior should be stopped before syncing

This step makes the prototype more realistic by separating roles and adding stronger local authentication signals.

## What Changed

### 1) Two Portals (Role Separation)

We split the product into two experiences:

- **Customer Portal**: rural end user flow only
  - login
  - create transaction
  - view personal history
  - safety controls (trusted contact, panic freeze)

- **Bank Portal**: staff / clerk / admin operations
  - fraud monitoring and review
  - sync queue + night sync
  - audit and change log
  - kiosk/agent mode

This avoids mixing "customer actions" with "bank control screens" and matches real-world banking workflows.

### 2) Separate Login Links

- Customer login: `/customer/login`
- Bank login: `/bank/login`

Root (`/`) becomes a simple portal selector when no session cookie exists.

### 3) Face Identity (Offline Enrollment + Match)

We upgraded from a checkbox/simulation to a real webcam flow:
- the browser captures a PNG image
- the app computes a lightweight perceptual hash (dHash) locally
- **first login enrolls**
- next logins must match within a threshold

This remains offline-first and lightweight (no cloud biometrics).

### 4) Device Binding + New Device Risk

We generate a stable `device_id` in the browser (stored in `localStorage`) and send it at login.

Behavior:
- first login enrolls the device
- if a different device logs in later, the session is marked as **untrusted**
- transactions created on an untrusted device are:
  - labeled with reason `NEW_DEVICE`
  - given extra risk points
  - forced into `HOLD_FOR_REVIEW` for safety

This directly reduces fraud for account takeover scenarios in rural settings.

## Files Added/Updated

- `src/ui/app.py`
- `src/ui/templates/login.html`
- `src/ui/templates/customer_dashboard.html`
- `src/ui/templates/index.html`
- `src/ui/templates/agent.html`
- `src/database/transaction_store.py`
- `src/auth/service.py`
- `src/auth/biometric.py` (new)
- `requirements.txt` (adds Pillow)
- `Dockerfile`, `.dockerignore`, `render.yaml`
- `.gitignore`

## How To Demo Quickly

1. Start the UI.
2. Open `/customer/login` and login with camera capture.
3. Logout, then login again (face must match).
4. Clear browser localStorage key `ruralshield_device_id` (or use a different browser).
5. Login again and create a transaction:
   - it should show `NEW_DEVICE`
   - it should be held for review

