# Literature Survey / Related Work

## Summary of Research Papers / Standards / Articles

### 1. Pascoe, Quinn, and Scarfone (2024) — NIST Cybersecurity Framework (CSF) 2.0
**Source:** NIST CSWP 29, National Institute of Standards and Technology.  
**What it contributes:** CSF 2.0 provides a practical cybersecurity structure built around risk management functions such as Identify, Protect, Detect, Respond, Recover, and the newer Govern function.  
**How it influenced RuralShield:** RuralShield aligns strongly with this model by combining authentication, device trust, fraud detection, auditability, response actions such as hold/block/review, and recovery-oriented sync traceability.

### 2. OWASP Application Security Verification Standard (ASVS)
**Source:** OWASP Foundation.  
**What it contributes:** ASVS provides a structured security baseline for web application controls including authentication, validation, session handling, cryptographic practices, and secure development review.  
**How it influenced RuralShield:** It informed secure input handling, local and server-side validation, safer auth workflows, and the project’s defensive approach to route and request design.

### 3. OWASP Mobile Application Security (MASVS / MASTG)
**Source:** OWASP Foundation.  
**What it contributes:** The OWASP mobile security initiative defines best practices for authentication, local data storage, cryptography, and secure testing in mobile-like environments.  
**How it influenced RuralShield:** Although RuralShield is browser-based, its rural-device and low-resource design closely matches mobile security concerns such as safe local storage, low-trust device handling, and offline-capable operation.

### 4. Kleppmann, Wiggins, van Hardenberg, and McGranaghan (2019) — Local-first software: You own your data, in spite of the cloud
**Source:** ACM Onward! 2019.  
**What it contributes:** This work formalizes the local-first software idea: applications should keep working even when network access is absent, while still supporting synchronization and data ownership.  
**How it influenced RuralShield:** RuralShield applies this idea directly through local SQLite persistence, outbox-based delayed sync, and operational continuity under weak connectivity.

### 5. den Hengst, Acar, and Visbeek (2023) — Explainable Fraud Detection with Deep Symbolic Classification
**Source:** arXiv:2312.00586.  
**What it contributes:** The paper argues that fraud systems need not only strong detection capability, but also transparent reasoning that can be explained to operators, regulators, and affected users.  
**How it influenced RuralShield:** RuralShield adopts explainability as a design goal by storing explicit reason codes and presenting fraud outcomes as understandable decisions rather than black-box predictions.

## Existing Tools / Technologies Considered
- SQLite for local offline persistence
- PostgreSQL for centralized deployed storage
- FastAPI for the web and API backend
- Docker and Render for portable deployment
- GitHub Wiki for project documentation and presentation

## Comparison Table
| Area | Conventional Banking Demo | RuralShield |
|---|---|---|
| Internet dependency | High | Reduced through local-first flow |
| Fraud explanation | Usually limited | Explicit reason codes and decision labels |
| Sync visibility | Hidden | Exposed through sync queue UI |
| Device trust awareness | Often minimal | Built into login and fraud scoring |
| Rural suitability | Weak | Core project focus |
| Admin operations | Basic | Monitoring, analytics, review, export |

## Navigation
- Previous: [[Objectives-and-Scope]]
- Next: [[System-Architecture]]
