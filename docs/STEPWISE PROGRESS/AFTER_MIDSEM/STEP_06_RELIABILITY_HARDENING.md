# STEP 06: Reliability Hardening (No More Random 500s)

## Goal
Ensure demo stability:
- no “Internal Server Error” black screens
- defensive parsing for timestamps / JSON fields
- safe template rendering

## Fixes Implemented

### Safe Template Rendering
Fixed a tricky issue where template TypeErrors were incorrectly handled, causing:
- `AttributeError: 'dict' object has no attribute 'split'`

Solution:
- `render_template()` now only uses the fallback signature when it is truly a Starlette signature mismatch.

### Transaction History Stability
History page previously crashed when `amount` was decrypted as a string.
Now:
- backend prepares `display_amount` as float (or `None`)
- template prints `-` when amount is not available

### Defensive Timestamp Formatting
Added defenses so `datetime.fromisoformat` never receives dict-like values.
All displayed time is shown in IST for consistency.

### Local Error Log
Unexpected UI errors are written to:
- `data/ui_errors.log`

This is useful during evaluation to show concrete evidence of debugging.

## Key Files
- `src/ui/app.py` (render_template, friendly time, history formatting)
- `src/ui/templates/customer_history.html`

