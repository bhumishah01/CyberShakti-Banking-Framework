# STEP 08: User-wise Analytics + Demo Result Page (Stronger Admin Story)

## Goal
Make analytics stronger from an admin perspective:
- keep bank-level analytics as-is
- add user-wise analytics for “deep dive”
- reduce confusion between “Demo Run” and “Analytics”

## What Was Implemented

### Demo Run Result Page (Separate)
Previously, “1-Click Demo Run” redirected to Analytics, making it feel identical.

Now:
- Demo Run redirects to `/bank/demo/result`
- The page explains what just happened and provides buttons to open:
  - Analytics
  - Sync Queue
  - Walkthrough

### Clickable Overview Cards
In analytics:
- top overview cards are links to:
  - Users list
  - Transactions list
  - Held/Blocked filters
  - Sync Queue

### User-wise Analytics (New)
Below bank analytics:
1. Compare users (bar chart by transaction volume)
2. Deep-dive for one user:
   - late-night transactions (IST logic)
   - failed login attempts
   - held/blocked counts
   - usage hour histogram (0–23)
   - top explainable fraud reasons

## Key Files
- Analytics computations: `src/ui/app.py` (`_bank_user_analytics`, `_single_user_insights`)
- Analytics template: `src/ui/templates/bank_analytics.html`
- Demo result template: `src/ui/templates/bank_demo_result.html`

## Demo Tips
1. Run “1-Click Demo Run”
2. On result page, open Analytics
3. Use user dropdown to show a “deep dive” profile

