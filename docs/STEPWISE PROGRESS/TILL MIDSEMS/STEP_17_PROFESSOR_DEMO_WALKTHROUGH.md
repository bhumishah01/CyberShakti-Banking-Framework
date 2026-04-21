# STEP 17 - Professor Demo Walkthrough Mode

## What Was Added
- New guided endpoint: `GET /demo/walkthrough`
- One-click deterministic demo story that auto-generates:
  - low-risk normal transfer
  - high-risk scam-like transfer with trusted-contact approval path
  - panic-freeze blocked transfer
- Includes ready presentation script on the page.

## Why This Helps
- Ensures consistent live demo every time.
- Removes manual setup mistakes during presentation.
- Directly maps features to outcomes for quick professor evaluation.

## Files Added
- `src/ui/templates/demo_walkthrough.html`

## Files Updated
- `src/ui/app.py`
- `src/ui/templates/index.html`
- `src/ui/static/styles.css`
- `tests/unit/test_ui_app.py`

## Validation
- UI route test added for walkthrough endpoint.
