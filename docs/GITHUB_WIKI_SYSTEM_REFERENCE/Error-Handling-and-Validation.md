# Error Handling and Validation

## Validation Examples

- PIN length and presence checks
- amount must be positive
- recipient cannot be empty
- invalid decisions rejected
- invalid freeze durations rejected
- invalid role rejected
- invalid DB upload rejected

## Auth Failure Handling

- failed attempts counted locally
- lockout enforced
- failed-login alerts created at suspicious thresholds
- user-facing error messages are localized and simplified

## Transaction Error Handling

- customer AJAX flow returns JSON error instead of broken redirect
- history read refuses to decrypt tampered records
- approval code expiry and max attempts are enforced

## Sync Error Handling

- retry counts increment automatically
- `last_error` stored
- backoff scheduled
- duplicate sync acknowledgements handled explicitly

## UI Error Handling

A custom exception handler in the UI app:
- logs to `data/ui_errors.log`
- returns JSON for JSON-like requests
- renders friendly `error.html` for browser users

## Fallback Logic

- server session creation failure does not prevent local usage
- missing optional data falls back to safe defaults in dashboard context builders
- translation fallback defaults are used when keys are missing
