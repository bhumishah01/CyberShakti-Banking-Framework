# STEP 01: Admin Portal Rebuild (Dashboard + Analytics)

## Goal
Make the Bank/Admin side feel like a real control room:
- simple dashboard for day-to-day operations
- separate analytics page for deeper intelligence
- clear navigation + demo helpers for evaluation

## What Was Implemented

### Admin Dashboard (clean)
- A “clean” admin dashboard focused on:
  - monitoring cards
  - operational shortcuts (Sync Queue, Audit Events, Change Log)
  - quick tools grouped into collapsible sections
- Reduced clutter by moving deep intelligence out of the dashboard.

### Analytics Page (separate)
Created `/bank/analytics` as a dedicated page containing:
- Overview counters
- Risk distribution summary
- Top fraud reasons (explainable engine)
- Fraud trends (with lightweight SVG graph)
- High-risk users list (behavior profiling signals)
- Suspicious pattern alerts list
- Device monitoring table

### Demo Map + Guide Hooks
Added “Demo Map” / “Demo Guide” style guidance content so a first-time viewer can follow the story.

## Demo URLs
- Bank login: `/bank`
- Bank dashboard: `/bank/dashboard`
- Admin analytics: `/bank/analytics`

## Key Files
- UI routes + data context: `src/ui/app.py`
- Dashboard template: `src/ui/templates/bank_dashboard.html`
- Analytics template: `src/ui/templates/bank_analytics.html`
- Styling: `src/ui/static/styles.css`

## Notes (Why This Matters)
This step aligns with the SIH requirement: “fraud detection + user authentication”.
The admin portal makes decisions **visible** and **explainable**:
why something is held, blocked, or flagged.

