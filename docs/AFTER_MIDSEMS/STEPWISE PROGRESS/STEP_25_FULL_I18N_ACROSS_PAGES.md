# STEP 03: Full i18n Across Pages (Consistent Language Switching)

## Goal
When language changes, **every heading, label, and button** should change too.
This is important for rural UX and for demo clarity.

## What Was Implemented

### Central Translation Bundle
Implemented a single translation bundle system in:
- `src/ui/app.py` (`_bundle()` + `_t()`)

All templates reference:
- `i18n.<key>` (preferred)

### Supported Languages
The UI includes these languages (demo-friendly):
- English (`en`)
- Hindi (`hi`)
- Odia (`or`)
- Gujarati (`gu`)
- German (`de`)

### Persistence
Language choice is persisted via cookie:
- `ruralshield_lang`

So if a new page opens (history, analytics, sync queue), language stays consistent.

## Key Files
- Translation bundle + helper: `src/ui/app.py`
- All templates under: `src/ui/templates/`

## Demo Checklist
1. Switch language on dashboard
2. Open Analytics
3. Open Sync Queue
4. Open Customer History

All pages should remain in the selected language.

