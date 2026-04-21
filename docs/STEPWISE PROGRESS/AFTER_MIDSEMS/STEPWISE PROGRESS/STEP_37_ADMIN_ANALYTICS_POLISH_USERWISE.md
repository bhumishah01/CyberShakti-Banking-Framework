# STEP 37: Admin Analytics Polish (Clickable Cards + User-wise Deep Dive)

## Goal
Make admin analytics “strong” and easy to present:
- not just tables, but patterns and trends
- clickable navigation from summary cards
- user-wise analysis to support bank decision making

## What Was Implemented

### 1) Analytics Page (Dedicated)
Admin analytics is separated from the clean dashboard.

Includes:
- fraud trends (lightweight graph)
- high-risk users list
- device monitoring
- suspicious alerts panel
- top fraud reasons + risk distribution

### 2) Clickable Summary Cards
Cards like Users / Transactions / Allowed / Held become clickable navigation:
- reduces confusion
- makes demo flow smoother

### 3) User-wise Deep Dive
Below the general analytics, we add a user-wise section where admin can:
- pick a user
- see transaction patterns:
  - late-night usage
  - held/blocked counts
  - failed login attempts
  - peak hours histogram

## Where To See It
- Bank portal: `/bank`
- Analytics: `/bank/analytics`

## Key Files
- UI routes + analytics context: `src/ui/app.py`
- Analytics template: `src/ui/templates/bank_analytics.html`

