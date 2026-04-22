# Literature Survey / Related Work

## Overview
RuralShield draws inspiration from secure mobile system design, fraud detection principles, and offline-first data synchronization patterns. Rather than reproducing a single published model, the project combines practical ideas from cybersecurity standards, banking security workflows, and resilient application architecture.

## Related Work and Conceptual References

### 1. NIST Cybersecurity Framework
The NIST Cybersecurity Framework provides a useful structure for organizing security systems into Identify, Protect, Detect, Respond, and Recover stages. RuralShield aligns naturally with this model:
- Identify: user profiles, device trust, transaction behavior patterns
- Protect: PIN auth, encryption, role separation
- Detect: fraud scoring and suspicious pattern alerts
- Respond: hold, block, release, freeze, review
- Recover: audit logs, sync recovery, reprocessing

### 2. OWASP Mobile and Application Security Guidance
OWASP guidance emphasizes secure storage, strong authentication, secure transport, and protection against tampering. RuralShield adopts these ideas through encrypted storage, tokenized sessions, and safe synchronization behavior.

### 3. Offline-First System Design
Offline-first applications are widely used in field operations, health systems, and logistics where internet is intermittent. The outbox pattern, local-first writes, and delayed synchronization used in RuralShield are well established and important in rural digital banking contexts.

### 4. Explainable Fraud Systems
In traditional fraud systems, classification is often treated as sufficient. In banking operations, however, explainability matters. A bank officer needs to know why something is suspicious. RuralShield therefore retains interpretable reason codes instead of using a completely opaque scoring model.

### 5. Device Trust and Assisted Security
Device binding, trusted device recognition, and assisted workflows are important in contexts where shared phones, public charging points, and informal support interactions are common. RuralShield includes a device trust model precisely to reflect that reality.

## Existing Tools and Technologies Reviewed
- SQLite for local persistence
- PostgreSQL for server persistence
- FastAPI for rapid web/API development
- Docker for deployment portability
- JSON-structured APIs for frontend-backend consistency

## Comparative Positioning
| Aspect | Typical Online Banking Demo | RuralShield |
|---|---|---|
| Offline-first operation | Weak or absent | Core design principle |
| Explainable fraud decisions | Usually limited | Built-in |
| Device trust tracking | Often omitted | Included |
| Bank analytics | Basic | Detailed admin analytics |
| Sync queue visibility | Rare | Explicit and demo-ready |

## Summary
The project stands out not because it uses one novel algorithm, but because it assembles multiple relevant ideas into a coherent, rural-first banking security framework.
