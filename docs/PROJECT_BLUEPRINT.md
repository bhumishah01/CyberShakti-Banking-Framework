# Project Blueprint: RuralShield (Working Name)

## 1. Project Title
RuralShield: Offline-First Cybersecurity Framework for Rural Digital Banking

## 2. One-line Goal
Build a lightweight app that secures rural banking transactions using local encryption, strong user authentication, fraud checks, and delayed internet sync.

## 3. Why This Matters
Rural users often have weak internet, low-end phones, and high fraud risk. Most systems assume stable connectivity. RuralShield makes security work offline first.

## 4. Problem Statement Mapping
- Required: secure transactions, fraud detection, user authentication, low-resource compatibility.
- Extension: offline-first architecture, tamper-evident logs, explainable fraud alerts, delayed sync.

## 5. Target Users
- Primary: rural banking users with low-end smartphones.
- Secondary: banking field agents/support staff.

## 6. Core Constraints
- Must work with intermittent/no internet.
- Must run on low RAM and slower CPUs.
- Must keep UI simple and low-literacy friendly.
- Must show measurable fraud-risk reduction in prototype tests.

## 7. Scope (In)
- Local encrypted storage using SQLite.
- PIN-based auth with optional biometric.
- Transaction fraud risk engine (rules first).
- Offline transaction queue with secure sync.
- Tamper-evident audit logging.
- Basic backend for sync and rule updates.

## 8. Scope (Out for Now)
- Real bank core integration.
- Full KYC onboarding stack.
- Production-grade scale infrastructure.
- Heavy cloud ML pipeline.

## 9. System Architecture
- Client app: UI + SQLite + crypto + fraud + sync.
- Backend: sync APIs + fraud rule update APIs.
- Flow: create tx -> authenticate -> risk score -> encrypt/sign -> local save -> delayed sync -> ack.

## 10. Security Design
- Auth: PIN + optional biometric + step-up for high risk.
- Encryption: sensitive fields encrypted at rest.
- Key management: OS secure keystore/keychain.
- Integrity: payload signatures and verification.
- Audit: hash-linked local audit chain.

## 11. Fraud Detection Design
- Rule engine first: unusual amount, odd hour, new recipient, rapid retries, failed auth attempts.
- Output: risk score (0-100), risk level, explainable reason.
- Policy: Low allow, Medium re-auth, High step-up/hold.
- Optional phase 2: lightweight anomaly model.

## 12. Offline-First Sync Design
- Local-first outbox storage.
- Sync on connectivity + idle/charging.
- Exponential backoff retries.
- Idempotency key for dedupe.
- Ack required before marking synced.

## 13. SQLite Plan
- users
- accounts
- transactions
- outbox
- fraud_rules
- audit_log

## 14. UX Plan
- Screens: onboarding, PIN login, transaction, risk warning, sync status, help.
- Principles: large touch targets, minimal text, icon-first cues, local language readiness.

## 15. Beyond SIH (Differentiators)
- Explainable trust score per transaction.
- Tamper-evident local audit chain.
- Offline fraud rule-pack updates.
- Assisted low-literacy mode (voice/icon guidance).

## 16. Metrics
- Security: tamper detection, unauthorized block rate, signature failures caught.
- Fraud: detection rate, false positives, latency.
- Reliability: offline queue success, reconnect sync success, duplicate prevention.
- Impact simulation: baseline vs protected flow.

## 17. Roadmap
- Week 1: requirements + threat model + architecture + skeleton.
- Week 2: auth + key handling.
- Week 3: encrypted storage flow.
- Week 4: fraud rules.
- Week 5: sync engine.
- Week 6: audit chain.
- Week 7: minimal backend.
- Week 8: testing + optimization.
- Week 9: final docs + demo.

## 18. Git Strategy
- main stable + short feature branches.
- Meaningful commits only.
- Format: `type(scope): summary`.
- Tag milestones: v0.1 ... v1.0.

## 19. Testing Plan
- Unit: crypto/fraud/sync/audit.
- Integration: full transaction lifecycle.
- Security: tamper/signature/PIN lock checks.
- Device: low-memory + network instability tests.

## 20. Deliverables
- Prototype app.
- Minimal backend.
- Fraud simulation report.
- Threat model + architecture diagrams.
- Structured Git history.
- Demo script.

---

## JSON Blueprint (Source-of-Truth)

```json
{
  "project": {
    "name": "RuralShield",
    "full_title": "Offline-First Cybersecurity Framework for Rural Digital Banking",
    "problem_statement": {
      "id": "25205",
      "title": "Cybersecurity Framework for Rural Digital Banking",
      "organization": "Government of Odisha",
      "department": "E & IT Department",
      "theme": "Blockchain & Cybersecurity"
    },
    "goal": "Secure rural digital banking transactions with local encryption, fraud detection, user authentication, and delayed sync for low-end smartphones with weak internet."
  },
  "context": {
    "constraints": [
      "Low-end smartphones",
      "Intermittent or limited internet",
      "Simple UX for rural users",
      "Solo development",
      "Continuous Git-tracked progress"
    ],
    "professor_suggestion": "Store and verify sensitive data locally in SQLite first, then sync later when idle/night/connected."
  },
  "scope": {
    "in_scope": [
      "Offline-first mobile app prototype",
      "Encrypted local storage (SQLite + field encryption)",
      "PIN-based authentication with optional biometric",
      "Fraud detection engine (rule-based first, optional lightweight anomaly layer)",
      "Secure outbox + delayed sync",
      "Tamper-evident audit logs",
      "Minimal backend for sync + rule updates"
    ],
    "out_of_scope": [
      "Full bank core integration",
      "Production-grade national scale architecture",
      "Complex cloud-only ML systems",
      "Full KYC ecosystem"
    ]
  },
  "architecture": {
    "client_app": {
      "modules": [
        "auth",
        "crypto",
        "local_db",
        "fraud_engine",
        "sync_engine",
        "audit_chain",
        "ui"
      ],
      "flow": [
        "User creates transaction",
        "User authenticates (PIN/biometric/step-up)",
        "Fraud engine scores risk and explains reason",
        "Transaction payload encrypted + signed",
        "Stored locally in outbox",
        "Syncs when network conditions are suitable",
        "Server ack updates local state"
      ]
    },
    "backend": {
      "services": [
        "Receive encrypted transaction packets",
        "Acknowledge and deduplicate by idempotency key",
        "Deliver fraud rule updates"
      ]
    }
  },
  "security_design": {
    "authentication": {
      "primary": "PIN",
      "optional": "Biometric",
      "step_up_for_high_risk": true,
      "controls": [
        "Rate-limit PIN attempts",
        "Temporary lock after repeated failures"
      ]
    },
    "encryption": {
      "at_rest": "Sensitive fields encrypted (AES-GCM or equivalent AEAD)",
      "in_transit": "HTTPS/TLS",
      "record_nonce_iv": "Unique per encrypted record"
    },
    "key_management": {
      "master_key_storage": "OS secure keystore/keychain",
      "derived_session_key": "Unlocked after successful PIN auth",
      "hardcoded_keys_allowed": false
    },
    "integrity": {
      "transaction_signature": true,
      "signature_verification_before_sync": true
    },
    "audit": {
      "tamper_evident_chain": true,
      "method": "Each log entry stores previous hash + current hash"
    }
  },
  "fraud_detection": {
    "phase_1_rule_engine": [
      "Unusually high amount for user history",
      "New beneficiary",
      "Odd transaction time",
      "Rapid repeated transactions",
      "Multiple failed auth attempts"
    ],
    "output": {
      "risk_score_range": "0-100",
      "risk_levels": [
        "LOW",
        "MEDIUM",
        "HIGH"
      ],
      "explainable_reason": true
    },
    "policy": {
      "LOW": "Allow normal flow",
      "MEDIUM": "Require re-authentication",
      "HIGH": "Step-up auth and hold until sync/confirmation"
    },
    "phase_2_optional": {
      "type": "Lightweight anomaly model",
      "constraint": "Must remain explainable and low-resource"
    }
  },
  "offline_sync": {
    "strategy": "Store-first, sync-later",
    "triggers": [
      "Network available",
      "Device idle/charging",
      "Manual sync"
    ],
    "reliability": {
      "retry": "Exponential backoff",
      "idempotency_key": true,
      "ack_required_before_mark_synced": true
    },
    "states": [
      "PENDING",
      "RETRYING",
      "SYNCED",
      "SYNCED_DUPLICATE_ACK",
      "REJECTED_INTEGRITY_FAIL"
    ]
  },
  "database_schema": {
    "users": [
      "user_id",
      "phone_hash",
      "pin_salt",
      "pin_hash",
      "auth_config",
      "created_at"
    ],
    "accounts": [
      "account_id",
      "user_id",
      "masked_account_no",
      "metadata_enc"
    ],
    "transactions": [
      "tx_id",
      "user_id",
      "amount_enc",
      "recipient_enc",
      "timestamp",
      "risk_score",
      "risk_level",
      "status",
      "signature",
      "nonce"
    ],
    "outbox": [
      "outbox_id",
      "tx_id",
      "payload_enc",
      "retry_count",
      "next_retry_at",
      "sync_state"
    ],
    "fraud_rules": [
      "rule_id",
      "rule_version",
      "rule_data",
      "updated_at"
    ],
    "audit_log": [
      "log_id",
      "event_type",
      "event_data_enc",
      "prev_hash",
      "curr_hash",
      "created_at"
    ]
  },
  "ux_plan": {
    "screens": [
      "Onboarding",
      "PIN setup/login",
      "Transaction form",
      "Risk warning/confirmation",
      "Sync status/history",
      "Help"
    ],
    "principles": [
      "Large touch targets",
      "Minimal text",
      "Simple language",
      "Icon-first cues",
      "Local language ready"
    ]
  },
  "innovation_beyond_statement": [
    "Explainable Trust Score per transaction",
    "Tamper-evident local audit chain",
    "Offline fraud rule-pack updates from server",
    "Assisted low-literacy mode (voice/icon guidance)"
  ],
  "metrics": {
    "security": [
      "Unauthorized access block rate",
      "Tamper detection rate",
      "Signature verification failure detection"
    ],
    "fraud": [
      "Fraud scenario detection rate",
      "False positive rate",
      "Detection latency"
    ],
    "reliability": [
      "Offline queue success rate",
      "Sync success after reconnect",
      "Duplicate prevention accuracy"
    ],
    "impact_simulation": {
      "baseline": "No fraud checks",
      "proposed": "Auth + fraud rules + hold policy + secure sync",
      "target": "Demonstrate meaningful reduction in successful simulated fraud attempts"
    }
  },
  "roadmap": [
    {
      "week": 1,
      "focus": [
        "Requirements freeze",
        "Threat model",
        "Architecture",
        "Repo setup",
        "UI skeleton"
      ]
    },
    {
      "week": 2,
      "focus": [
        "Auth module",
        "PIN flow",
        "Keychain/keystore integration"
      ]
    },
    {
      "week": 3,
      "focus": [
        "Encrypted SQLite schema",
        "Transaction save pipeline"
      ]
    },
    {
      "week": 4,
      "focus": [
        "Rule-based fraud engine",
        "Explainable risk output"
      ]
    },
    {
      "week": 5,
      "focus": [
        "Outbox queue",
        "Background sync",
        "Retry + idempotency"
      ]
    },
    {
      "week": 6,
      "focus": [
        "Tamper-evident audit chain",
        "Integrity checker"
      ]
    },
    {
      "week": 7,
      "focus": [
        "Minimal backend APIs",
        "Rule update pipeline"
      ]
    },
    {
      "week": 8,
      "focus": [
        "Testing",
        "Low-end optimization",
        "Demo scenario runs"
      ]
    },
    {
      "week": 9,
      "focus": [
        "Documentation",
        "Results report",
        "Presentation prep"
      ]
    }
  ],
  "git_strategy": {
    "branching": {
      "main": "stable",
      "feature_branches": [
        "feature/auth",
        "feature/crypto-db",
        "feature/fraud-engine",
        "feature/offline-sync",
        "feature/audit-chain"
      ]
    },
    "commit_policy": [
      "Commit only meaningful completed units",
      "Avoid tiny noisy commits",
      "Each commit should build/run"
    ],
    "message_format_examples": [
      "feat(auth): add PIN setup and unlock flow",
      "feat(db): add encrypted transaction and outbox schema",
      "feat(fraud): implement risk scoring with reason codes",
      "fix(sync): prevent duplicate retries via idempotency key",
      "docs(architecture): add threat model and sequence diagram"
    ],
    "cadence": "2-6 meaningful commits/day on active build days",
    "milestone_tags": [
      "v0.1-auth",
      "v0.2-encrypted-store",
      "v0.3-fraud-rules",
      "v0.4-offline-sync",
      "v1.0-prototype"
    ]
  },
  "testing_plan": {
    "unit_tests": [
      "Crypto helpers",
      "Fraud rule logic",
      "Sync retry/idempotency",
      "Audit chain hash verification"
    ],
    "integration_tests": [
      "Transaction flow end-to-end: create -> auth -> score -> encrypt -> queue -> sync"
    ],
    "security_tests": [
      "Tampered record detection",
      "Invalid signature rejection",
      "Wrong PIN lock behavior"
    ],
    "device_tests": [
      "Low-memory profile testing",
      "Airplane mode + reconnect scenarios"
    ]
  },
  "deliverables": [
    "Working mobile prototype",
    "Minimal backend sync service",
    "Fraud simulation dataset + evaluation report",
    "Threat model and architecture diagrams",
    "Structured Git history showing progress",
    "Demo script and presentation material"
  ]
}
```
