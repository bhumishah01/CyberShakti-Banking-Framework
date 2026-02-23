# Architecture

## 1. High-Level Components

- Mobile Client (offline-first)
- Local SQLite Database
- Crypto Layer
- Fraud Rule Engine
- Sync Queue Manager
- Minimal Sync API

## 2. Transaction Lifecycle

1. User creates transaction.
2. Auth module verifies user (PIN/step-up if high risk).
3. Fraud module computes score and reason codes.
4. Crypto module encrypts payload and attaches integrity signature.
5. Database stores encrypted transaction + outbox entry.
6. Sync manager retries upload when network is stable.
7. API returns acknowledgment and dedupe status.
8. Audit module appends immutable hash-linked event.

## 3. Module Contracts

### auth
- Input: user credential data, transaction context.
- Output: authenticated session token or denial reason.

### crypto
- Input: plaintext payload + key reference.
- Output: encrypted payload, nonce, signature metadata.

### database
- Input: encrypted records + metadata.
- Output: persistent local records + query interface.

### fraud
- Input: transaction + user behavior history.
- Output: risk score (0-100), level, reason codes.

### sync
- Input: pending outbox records.
- Output: synced state transitions and retry schedule.

### audit
- Input: security event.
- Output: appended hash-chained log entry.

## 4. Reliability Strategy

- Local-first writes before network operations.
- Exponential backoff for sync retries.
- Idempotency key per transaction to prevent duplicates.
- Fail-safe states for rejected or tampered records.

## 5. Data States

- `PENDING`
- `RETRYING`
- `SYNCED`
- `SYNCED_DUPLICATE_ACK`
- `REJECTED_INTEGRITY_FAIL`
