# STEP 15 - Fraud Scenario Simulator (Demo-Ready)

## What Was Added
- Added a new UI section: **Fraud Scenario Simulator**.
- Added backend route: `POST /simulate/scenario`.
- Supports realistic one-click fraud cases:
  - Late-night high-value transfer to unknown recipient
  - Rapid burst transfers (money mule pattern)
  - Account takeover after failed login attempts

## Why This Matters
- Converts the prototype from basic transaction entry into a practical anti-fraud demo.
- Lets evaluators instantly see detection logic and intervention outcomes.
- Demonstrates explainable security decisions with `risk`, `action`, `status`, and `reasons`.

## Technical Notes
- Simulator can auto-create a test user if missing.
- Optional trusted contact can be set before running a scenario.
- Account takeover scenario temporarily injects failed-attempt state to simulate credential abuse.

## Files Updated
- `src/ui/app.py`
- `src/ui/templates/index.html`
- `src/ui/static/styles.css`
- `tests/unit/test_ui_app.py`

## Validation
- UI tests include simulator endpoint coverage.
- Full test suite remains green.
