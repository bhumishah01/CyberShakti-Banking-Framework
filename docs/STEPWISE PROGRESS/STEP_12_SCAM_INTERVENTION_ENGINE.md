# Step 12: Scam Intervention Engine (Operational Safety Layer)

## Why this matters

This upgrade turns fraud scoring into actual protection decisions, making the system more deployable in real-world scam scenarios.

## What was implemented

- Action decision engine in `src/fraud/engine.py`:
  - `ALLOW`
  - `STEP_UP`
  - `HOLD`
  - `BLOCK`
- Decision persistence in DB (`transactions` table):
  - `action_decision`
  - `intervention_data`
- Hold/Block behavior integrated into transaction pipeline.

## Operational behavior

- `ALLOW` / `STEP_UP`:
  - transaction enters normal pending sync path.
- `HOLD`:
  - transaction stored securely but marked `HOLD_FOR_REVIEW` and not synced until manual release.
- `BLOCK`:
  - transaction blocked locally from sync path for immediate protection.

## New UI capabilities

- Transaction table now shows:
  - Action decision,
  - human-readable intervention guidance.
- New action in dashboard:
  - `Release Held Transaction` form.

## Security integrity

- Releasing held transactions now re-signs transaction integrity metadata to preserve tamper checks.

## Outcome

The prototype now behaves like a safety copilot, not only a scoring engine.
