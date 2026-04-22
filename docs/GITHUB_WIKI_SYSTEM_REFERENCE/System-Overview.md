# System Overview

RuralShield is an offline-first cybersecurity framework for rural digital banking. Its main purpose is to keep transaction workflows usable and secure even when connectivity is weak, devices are shared, and users need more visible fraud guidance than a normal banking interface provides.

The project combines three major ideas:

- **offline-first transaction continuity** using local SQLite storage
- **explainable fraud detection** using risk scores and reason codes
- **bank/admin visibility and control** through dashboards, analytics, and review actions

## Core System Idea

Instead of assuming the app can always reach a central bank server, RuralShield allows important workflows to complete locally first. The local system:

- stores users and security state
- evaluates transaction risk locally
- encrypts and signs transaction records
- stores them locally
- queues them for synchronization later

This means the system can still behave predictably in real rural conditions.

## Primary Runtime Components

### 1. Customer Portal
The customer-facing portal supports registration, login, send money, history, voice-assisted input, notifications, safety settings, and an offline-aware dashboard.

### 2. Bank/Admin Portal
The bank-facing portal supports monitoring, analytics, sync review, high-risk user controls, alerts, export, and demo/report tools.

### 3. Local Security Runtime
This includes SQLite, local auth, face-hash verification, device trust, encryption, HMAC signatures, change logs, and audit chain support.

### 4. Fraud Engine
A rule-based local fraud engine scores transactions before sync. A separate trust-aware server-side fraud service exists for central API flows.

### 5. Sync Layer
An outbox queue stores records that need to be uploaded later. Admin users can sync one, selected, or all rows.

### 6. Central API + PostgreSQL Layer
A JWT-secured FastAPI backend stores server users, transactions, fraud logs, sync logs, and trust/device data.

### 7. Deployment Layer
The deployed Render instance exposes the UI at `/` and the API at `/api`, allowing one live URL for both the demo and the technical backend.

## Why This Architecture Matters

RuralShield is not only a UI project. It is a system with:

- local operational resilience
- transparent fraud decisioning
- multi-role access
- sync-aware data handling
- admin observability

That makes it closer to a deployable product architecture than a basic classroom prototype.
