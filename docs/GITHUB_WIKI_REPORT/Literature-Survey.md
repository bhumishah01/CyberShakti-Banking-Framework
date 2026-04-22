# Literature Survey / Related Work

## Overview
The design of RuralShield is informed by practical cybersecurity frameworks, secure mobile application guidance, offline-first synchronization patterns, and explainable fraud analysis principles. Instead of reproducing a single research paper, the project synthesizes several relevant ideas into a coherent banking security system suitable for rural deployment scenarios.

## 1. Cybersecurity Framework Thinking
A useful conceptual reference for this project is the NIST Cybersecurity Framework. The structure of Identify, Protect, Detect, Respond, and Recover maps naturally onto the system:
- **Identify**: user profiles, device trust, behavior baselines, risk patterns
- **Protect**: PIN-based access, encryption, token handling, field-level data security
- **Detect**: fraud scoring, suspicious pattern alerts, high-risk transaction detection
- **Respond**: hold/block decisions, release workflows, freeze/unfreeze actions
- **Recover**: sync recovery, audit logs, queue handling, retry states

This project therefore does not treat fraud detection as an isolated feature. It fits fraud analysis into a broader security lifecycle.

## 2. Mobile and Application Security Guidance
OWASP-inspired secure development practices influenced several project decisions:
- secure local storage
- authenticated session management
- safe routing between pages and actions
- controlled exposure of sensitive data
- validation of user actions before processing

Even though the project is deployed as a web application, many of its concerns are mobile-like in nature because the system is designed around low-end, field-like, constrained usage.

## 3. Offline-First Application Design
Offline-first design patterns are widely used in healthcare, logistics, field audits, and retail POS systems. The outbox model used in RuralShield is an adaptation of these resilience-oriented patterns. The key ideas are:
- write locally first,
- preserve intent safely,
- retry synchronization later,
- avoid data loss when the connection fails.

These ideas are especially relevant in rural finance because a failed or vanished transaction can produce both user mistrust and operational confusion.

## 4. Explainable Fraud Detection
Banking systems often use risk scoring, but many student prototypes stop at a number or a binary outcome. In real operations, however, staff need to know why something is suspicious. RuralShield therefore uses reason codes and simple explanations rather than opaque outputs. This makes the system more reviewable and more aligned with real financial workflows.

## 5. Device Trust and Shared-Device Risk
In rural banking contexts, device trust is particularly relevant because device sharing and device change are more common. A system that ignores device context misses a major risk signal. RuralShield explicitly includes device trust tracking and uses it in both scoring and monitoring.

## Existing Tools and Technologies Studied
The system also reflects the strengths and limitations of common tools:
- **SQLite** for local portability and low overhead
- **PostgreSQL** for central reliability and structured relationships
- **FastAPI** for rapid but structured full-stack web/API delivery
- **Docker** for repeatable local and cloud deployment

## Comparative Perspective
| Aspect | Typical Online Banking Demo | RuralShield |
|---|---|---|
| Offline-first operation | Often absent | Core design principle |
| Explainable fraud reasons | Minimal | Built-in |
| Device trust visibility | Rare | Included |
| Selective sync/recovery | Rare | Implemented |
| Admin analytics depth | Often basic | Extended |
| Rural usability orientation | Usually low | Central design focus |

## Summary
The main contribution of RuralShield is not a single novel algorithm. Its contribution lies in how it integrates offline-first reliability, explainable security controls, customer-side usability, and bank/admin oversight into one realistic system.
