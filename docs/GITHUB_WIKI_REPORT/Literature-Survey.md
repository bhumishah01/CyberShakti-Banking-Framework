# Literature Survey / Related Work

## Overview
RuralShield was not built in isolation. Its design is informed by multiple streams of related work: cybersecurity frameworks, secure application guidance, offline-first system design, explainable decision systems, and fraud-aware banking workflows. This section summarizes representative references and how they shaped the project.

## 1. NIST Cybersecurity Framework
The NIST Cybersecurity Framework is not a banking-specific paper, but it provides a strong structure for thinking about security systems. Its Identify-Protect-Detect-Respond-Recover model maps naturally to RuralShield.

### Relevance to this project
- **Identify**: user profile, device trust, transaction behavior
- **Protect**: encryption, PIN handling, JWT-based access
- **Detect**: fraud score, suspicious pattern alerts
- **Respond**: hold/block/release/freeze actions
- **Recover**: sync recovery, auditability, retry handling

### Contribution to RuralShield
The framework helped shape the system as a full security lifecycle rather than a single fraud classifier.

## 2. OWASP Application and Mobile Security Guidance
OWASP guidance emphasizes secure storage, safe authentication, validation, and defense against tampering. Even though RuralShield is not a mobile APK, it shares many mobile-like constraints because it is designed for low-resource, field-like conditions.

### Contribution to RuralShield
- local storage is treated as sensitive
- user actions are validated before processing
- deployment is separated from local data handling
- authentication and session behavior are structured rather than ad hoc

## 3. Offline-First Data Architecture Articles and Patterns
Offline-first system design is common in field applications such as logistics, healthcare, and retail POS systems. The main idea is to record user intent locally first and sync later instead of failing hard when the network is unavailable.

### Contribution to RuralShield
This directly influenced:
- local SQLite usage
- sync queue design
- retry and pending states
- selective sync and release workflows

## 4. Explainable Fraud Detection Research
Fraud detection systems often focus on prediction strength but provide little explanation. In financial operations, this is a limitation because staff need interpretable reasons to review transactions and users need understandable outcomes.

### Contribution to RuralShield
The project uses reason codes such as:
- `NEW_DEVICE`
- `HIGH_AMOUNT`
- `ODD_TIME`
- `RAPID_BURST`
- `HIGH_AMOUNT_VS_AVG`

These codes make the fraud engine reviewable, not just functional.

## 5. Device Trust and Shared-Device Risk Work
A significant fraud signal in low-resource environments is device context. New devices, shared phones, or unfamiliar activity patterns often increase account misuse risk.

### Contribution to RuralShield
This motivated:
- trusted vs untrusted device tracking
- device monitoring in admin analytics
- additional risk contribution from new-device scenarios

## Existing Tools / Technologies Considered
- SQLite for local-first persistence
- PostgreSQL for central server persistence
- FastAPI for API + routed application structure
- Docker for portable deployment
- GitHub Wiki for structured documentation delivery

## Comparison Table
| Area | Traditional Online Banking Demo | RuralShield |
|---|---|---|
| Offline support | Minimal | Core design principle |
| Explainable fraud output | Weak | Strong |
| Sync queue visibility | Rare | Explicit |
| Device trust visibility | Rare | Included |
| Admin controls | Usually basic | Operational |
| Rural constraints focus | Often absent | Central |

## Summary
The strongest insight from related work is that security, fraud detection, offline storage, and usability cannot be treated as separate concerns in rural banking. RuralShield integrates them into one practical system design.

## Navigation
- Previous: [[Objectives-and-Scope]]
- Next: [[System-Architecture]]
