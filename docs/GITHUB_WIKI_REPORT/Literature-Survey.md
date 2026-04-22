# Literature Survey / Related Work

## 1. NIST Cybersecurity Framework (CSF)
The NIST Cybersecurity Framework organizes security work into Identify, Protect, Detect, Respond, and Recover. RuralShield reflects this pattern by identifying trust signals, protecting transactions with encryption and authentication, detecting suspicious behavior, responding through hold/block/review workflows, and recovering via logging and sync traceability.

## 2. OWASP Application and Mobile Security Guidance
OWASP guidance influenced secure local handling, input validation, and defensive request processing. For a banking-style workflow, these controls matter because data cannot be trusted simply because it comes from the frontend.

## 3. Offline-First System Design Patterns
Offline-first patterns are widely used in logistics, health, field-data, and remote operations systems. RuralShield applies similar ideas through local storage, an outbox queue, delayed synchronization, and retry tracking.

## 4. Explainable Fraud Detection Concepts
Many fraud systems generate scores but hide their reasoning. RuralShield instead stores explicit reason codes such as `NEW_DEVICE`, `HIGH_AMOUNT`, and `RAPID_BURST`, making decisions easier to justify and present.

## 5. Device Trust and Behavioral Risk Models
Shared devices, new devices, and unusual usage timing are common fraud signals. RuralShield incorporates device trust tracking and behavioral profiling to make its scoring more realistic.

## Existing Tools / Technologies Referenced
- SQLite for local persistence
- PostgreSQL for central persistence
- FastAPI for API and mounted UI runtime
- JWT for token-based auth
- Docker and Render for deployment

## Comparison Table
| Area | Conventional Online Banking Demo | RuralShield |
|---|---|---|
| Offline operation | Weak | Strong |
| Explainable fraud | Usually limited | Explicit reason codes |
| Sync queue visibility | Rare | Built in |
| Device trust | Often hidden | Visible and scored |
| Admin monitoring | Basic | Operational + analytical |
| Rural-first design | Often absent | Central design goal |

## Navigation
- Previous: [[Objectives-and-Scope]]
- Next: [[System-Architecture]]
