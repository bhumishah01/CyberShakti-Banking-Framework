# STEP 07: Face + Device Trust Stability (Practical Rural Biometrics)

## Goal
Use face + device trust as a “step-up” signal without breaking the user experience.

The system must:
- be strict enough to demonstrate security
- be tolerant enough for low-end webcams / lighting changes

## What Was Implemented

### Face Hash Verification (Prototype)
Biometric model:
- lightweight perceptual hash (dHash)
- stored locally per user in `auth_config`

### Auto-Refresh on Trusted Devices
Problem:
Even the same person can produce small image hash drift across logins.

Fix:
If PIN is correct and the device is already trusted:
- auto-refresh stored face template to prevent repeated false mismatches

### New Device Behavior
If device is new/untrusted:
- login continues (to avoid blocking demos)
- session is flagged as face weak (`FACE_COOKIE=0`)
- risk scoring adds reason `FACE_WEAK` for customer transactions

## Key Files
- Face helpers: `src/auth/biometric.py`
- Face logic: `src/auth/service.py`
- Login wiring: `src/ui/app.py`

## Demo Tips
1. Login once normally (enroll face)
2. Login again with slightly different angle (still works due to trusted refresh)
3. Show that new device increases risk (FACE_WEAK / NEW_DEVICE reasons)

