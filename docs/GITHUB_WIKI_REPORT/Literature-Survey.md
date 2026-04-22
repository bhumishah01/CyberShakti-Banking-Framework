# Literature-Survey

## Summary of 3–5 Research Papers / Articles / Conceptual References

### 1. NIST Cybersecurity Framework (CSF)
The NIST Cybersecurity Framework organizes security into Identify, Protect, Detect, Respond, and Recover. RuralShield aligns well with this structure by using device trust, authentication, fraud scoring, alerts, review actions, and sync recovery.

### 2. OWASP Security Guidance
OWASP guidance influenced the project in secure storage, authentication handling, input validation, and safe request processing. These ideas are important because banking systems cannot tolerate weak local handling of sensitive actions.

### 3. Offline-First System Design Patterns
Offline-first architecture is common in field systems such as logistics and healthcare. The outbox pattern and delayed synchronization used in RuralShield were inspired by these resilience-oriented approaches.

### 4. Explainable Fraud Detection Concepts
Fraud systems are more useful when the system can explain why a transaction is suspicious. This influenced RuralShield’s use of explicit reason codes rather than only hidden scores.

### 5. Device Trust and Behavioral Risk Concepts
Shared devices, new devices, and unusual behavior are major fraud signals. RuralShield includes device trust and behavior profiling for that reason.

## Existing Tools / Technologies
- SQLite
- PostgreSQL
- FastAPI
- Docker
- GitHub Wiki
- Render

## Comparison Table
| Area | Conventional Online Banking Demo | RuralShield |
|---|---|---|
| Offline support | Weak | Strong |
| Fraud explainability | Low | High |
| Sync queue visibility | Rare | Included |
| Device trust monitoring | Rare | Included |
| Admin controls | Basic | Operational |
| Rural-first focus | Often absent | Central |

## Navigation
- Previous: [[Objectives-and-Scope]]
- Next: [[System-Architecture]]
