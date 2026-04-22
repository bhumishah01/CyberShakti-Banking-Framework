# Offline-First System

## Core Principle

The project treats the local SQLite database as the operational layer that allows the system to keep working when the network is absent or unstable.

## SQLite Responsibilities

SQLite stores:

- users and auth state
- encrypted transactions
- outbox queue
- alerts and notifications
- audit log and change log
- devices and user profiles

## Outbox Queue

The `outbox` table records which transactions need to be synchronized later. Each row carries sync state, retry counters, next retry timestamps, error details, and an idempotency key.

## Sync Modes Supported

- sync all pending rows
- sync one specific row
- sync selected rows
- simulate night sync locally

## Retry Strategy

When a sync attempt fails:

- retry count increases
- `last_error` is stored
- `next_retry_at` is scheduled
- state becomes `RETRYING`

This is handled in `src/sync/manager.py`.

## Duplicate Protection

Each transaction generates an idempotency key. The sync layer and server sync log use this to avoid repeated creation of the same record.

## Why This Matters

This design matches the real project problem: digital banking in environments with unstable connectivity cannot rely on immediate round trips to a server for every operation.
