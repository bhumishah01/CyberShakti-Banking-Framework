# Midsem Report – RuralShield

## Title
**Cybersecurity Framework for Rural Digital Banking (RuralShield)**

## Problem Statement (SIH PSID 25205)
Develop a lightweight cybersecurity framework to secure digital banking transactions for rural users, focusing on fraud detection and user authentication. The solution must be compatible with low-end smartphones and limited internet connectivity.

## Abstract
RuralShield is an offline-first security prototype for rural digital banking. It stores transactions locally in encrypted form, evaluates fraud risk on-device, and queues transactions for later synchronization when connectivity is available. The system includes PIN-based authentication, trusted-contact approvals for high-risk transfers, panic freeze controls, audit-chain integrity logs, change logs (old/new values), multilingual UI, and voice-guided safety prompts. The goal is to reduce fraud risk before any data leaves the device and to offer a simple, rural-friendly interface.

## Objectives
1. Secure local storage of sensitive transaction data on low-end devices.
2. On-device fraud detection with explainable reasons and risk scores.
3. Step-up verification for risky transfers.
4. Offline queueing with safe, delayed synchronization.
5. Transparent auditability and change tracking.
6. Simple, multilingual UI for rural users.

## Scope (What is built in this phase)
- Offline-first transaction pipeline with encryption and signature checks.
- Rule-based fraud scoring and decisioning (ALLOW/HOLD/BLOCK).
- Trusted-contact approvals for high-risk cases.
- Panic freeze to block outgoing transfers.
- Local outbox queue for delayed sync.
- Audit chain + change log.
- Web UI for demo with multilingual text and voice prompts.
- Sync queue visualization + night sync simulator.

## Tech Stack
- **Language:** Python 3
- **Backend Framework:** FastAPI
- **Database:** SQLite (local, offline-first)
- **Frontend:** Jinja2 templates + HTML/CSS
- **Security:** scrypt (PIN hashing), cryptography (encryption/signing)
- **Audio:** Browser SpeechSynthesis API

## Architecture Overview (High Level)
1. **UI Layer (FastAPI + Jinja2)**
   - Handles forms and pages (dashboard, agent mode, reports, sync queue).
2. **Core Security Layer**
   - Encryption, signatures, PIN auth, fraud scoring.
3. **Storage Layer (SQLite)**
   - Users, transactions, outbox, audit_log, change_log.
4. **Sync Layer**
   - Outbox queue + retry/backoff; sync later when online.

## Modules and Responsibilities

### 1) UI Module
- **File:** `src/ui/app.py`
- **Purpose:** Routes, form handling, language switching, demo flows.
- **Key pages:**
  - Dashboard
  - Agent/Kiosk mode
  - Transactions list
  - Sync queue
  - Fraud impact report
  - Demo walkthrough
  - Change log

### 2) Transaction Security Module
- **File:** `src/database/transaction_store.py`
- **Purpose:**
  - Encrypt amount/recipient locally
  - Score fraud risk
  - Decide allow/hold/block
  - Store to transactions table
  - Queue in outbox for sync
  - Release held transactions with trusted approval

### 3) Authentication Module
- **File:** `src/auth/service.py`
- **Purpose:**
  - PIN hashing + verification
  - Lockout on repeated failures
  - Trusted contact + panic freeze
  - Session key derivation

### 4) Fraud Engine
- **File:** `src/fraud/engine.py`
- **Rules Used:**
  - New recipient
  - High amount
  - Odd hour
  - Rapid burst
  - Recent auth failures

### 5) Audit & Change Logging
- **Files:**
  - `src/audit/chain.py`
  - `src/audit/change_log.py`
- **Purpose:**
  - Tamper-evident audit chain
  - Old/new value tracking for key edits

### 6) Sync Manager
- **Files:**
  - `src/sync/manager.py`
  - `src/sync/client.py`
- **Purpose:**
  - Sync outbox to server
  - Retry/backoff
  - Idempotent sync

### 7) Database Schema
- **File:** `src/database/init_db.py`
- **Tables:** users, accounts, transactions, outbox, audit_log, change_log

## Implementation Details (Technical)

### A) Local Encryption
- Transaction amount and recipient are encrypted using keys derived from the user PIN.
- Sensitive fields are stored as encrypted blobs in SQLite.

### B) PIN Security
- PINs are hashed with **scrypt** + random salt.
- Lockout after repeated failed attempts.

### C) Fraud Decisioning
- Each transaction is scored locally.
- Action = ALLOW, HOLD, or BLOCK.
- Reasons are stored and shown in UI.

### D) Trusted-Contact Approval
- For HOLD cases, a 6-digit approval code is generated locally.
- Hash of approval code + expiry time stored in DB.
- If code is valid, transaction is released and queued.

### E) Offline Sync Queue
- All safe transactions go into the outbox queue.
- Queue is visible in UI.
- A **night sync simulator** demonstrates delayed syncing.

### F) Audit Chain
- Each major action appends a hash-linked audit record.
- Provides tamper evidence.

### G) Change Log
- Records old/new values for key edits.
- Exportable as CSV for Excel.

### H) Multilingual + Voice
- UI supports English, Hindi, Odia, Gujarati, German.
- Voice guidance uses browser SpeechSynthesis API (no internet required).

## Demo Instructions (Quick)
1. Run UI: `uvicorn src.ui.app:app --host 127.0.0.1 --port 8502 --reload`
2. Create user + transaction
3. Show risk/hold/block
4. Open Sync Queue
5. Simulate Night Sync

## Results Achieved So Far
- Fully working offline-first demo
- Fraud scoring + explainable actions
- Trusted approvals + panic freeze
- Auditable, transparent logs
- Multilingual rural-friendly UI
- Sync queue + night sync simulator

## Limitations (Current Stage)
- OTP delivery is simulated (not real SMS)
- Fraud model is rule-based (not ML yet)
- Backend sync server is minimal demo

## Future Work
- Real OTP delivery
- ML anomaly detection on-device
- Signed PDF audit reports
- Village/region fraud analytics

---
**End of Midsem Report**
