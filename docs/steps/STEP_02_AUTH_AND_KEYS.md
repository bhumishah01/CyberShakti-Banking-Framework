# Step 2: Authentication and Key Handling

## What was implemented

- PIN-based authentication service (`src/auth/service.py`).
- Secure PIN hashing using `scrypt` with per-user random salt.
- Failed-attempt tracking and timed lockout policy.
- Deterministic session key derivation helper after successful auth.
- Backward-compatible DB schema update for auth fields.

## Auth policy

- PIN length: 4 digits.
- Max failed attempts: 5.
- Lockout window: 15 minutes.
- On success: failed attempts reset to 0.

## Key handling decision (current)

- Session key is derived from `user_id + pin` and stored salt using `scrypt`.
- This is a bridge for prototype stage.
- Next hardening step: wrap/guard keys using platform keystore when moving to mobile runtime.

## DB changes

Users table now includes:
- `failed_attempts`
- `lockout_until`
- `last_auth_at`

Migration helper in `init_db.py` adds these columns if missing in old local DB files.

## Tests added

- Successful authentication flow.
- Lockout after repeated failed attempts.
- Recovery after lockout expiry.
- Session key derivation only after valid auth.

Result: `4 passed`.
