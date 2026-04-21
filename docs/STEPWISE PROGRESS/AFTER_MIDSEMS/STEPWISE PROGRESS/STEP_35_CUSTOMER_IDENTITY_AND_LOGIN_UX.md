# STEP 35: Customer Identity + Login UX (Remember Users, Stable Face Step)

## Goal
Make customer login feel like a real banking app:
- if a user already exists, they should be able to log in directly
- avoid forcing “create user” every time
- store/display customer identity properly (Title + Name + Surname)
- keep face verification stable (reduce false failures)

## What Was Implemented

### 1) Customer Identity Fields
Customer onboarding/login flow supports:
- `title` (Ms/Mr)
- `first_name`
- `last_name`

This is used for a clear header like:
**Logged in as Ms. Bhumi Shah (Customer ID 5)**

### 2) Remember Existing Users
If a user was created in the past:
- UI remembers the user list (local store)
- login checks local DB first
- portal does not say “user doesn’t exist” incorrectly

### 3) Face Verification Stability (Customer Side)
Face match is used as a “step-up” factor:
- on trusted device: smoother match, fewer hard failures
- on mismatch: show safe guidance + allow re-capture (no crash)

Note:
Face verification should never cause an unrecoverable blank screen.
If it cannot verify strongly, we degrade gracefully (risk increases, but user can continue).

## Where To See It
- Customer portal: `/customer`
- After login: `/dashboard/customer`

## Key Files
- UI auth + customer routes: `src/ui/app.py`
- Customer templates: `src/ui/templates/customer_home.html`, `src/ui/templates/customer_dashboard.html`
- Auth service helpers: `src/auth/service.py`

