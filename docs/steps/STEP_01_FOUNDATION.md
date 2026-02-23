# Step 1 Foundation (Locked Baseline)

This document freezes the foundation for the project so future work stays aligned and measurable.

## 1. Problem Alignment

- Problem Statement ID: 25205
- Title: Cybersecurity Framework for Rural Digital Banking
- Goal: build a lightweight, offline-first security framework for rural digital banking.

## 2. Product Goal

RuralShield secures digital banking transactions on low-end smartphones with weak or intermittent internet by combining:

- local authentication,
- encrypted local storage,
- local fraud risk scoring,
- delayed secure sync,
- tamper-evident auditing.

## 3. Must-Have Scope (MVP)

- `auth`: PIN-first authentication with step-up verification.
- `crypto`: encryption/decryption + integrity signature helpers.
- `database`: SQLite schema and local-first transaction storage.
- `fraud`: rule-based risk engine with explainable alerts.
- `sync`: outbox queue with retry and idempotency.
- `audit`: hash-linked local audit log.

## 4. Out of Scope (for now)

- direct production bank integrations,
- heavy cloud ML pipelines,
- full KYC ecosystem.

## 5. Definition of Done for MVP

- User can create transaction offline.
- Transaction is authenticated, risk-scored, encrypted, and stored locally.
- Outbox sync sends transaction when network is available.
- Duplicate sync is prevented using idempotency keys.
- Audit chain detects tampering.

## 6. Development Rules

- Keep features low-resource and mobile-friendly.
- Every module change should have at least one corresponding test.
- Only meaningful commits (feature-complete, fix-complete, docs-complete).
- Commit format: `type(scope): summary`.

## 7. Risk Register (Initial)

- Key management complexity on low-end devices.
- False positives in fraud rules.
- Sync conflicts and duplicate submissions.
- Performance degradation on old hardware.

Mitigation starts in Step 2 with secure key-handling decisions and baseline performance checks.
