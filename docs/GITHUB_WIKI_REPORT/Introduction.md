# Introduction

## Background of the Project
Digital banking adoption is growing quickly, but the architecture of many systems still assumes conditions that are not consistently available in rural environments. Banking applications are often designed with the expectation of modern phones, persistent internet, immediate backend verification, and users who already understand digital workflows. In many rural contexts, those assumptions break down.

A rural banking user may use a budget phone, rely on patchy connectivity, share a device with family members, and need reassurance at every critical step. A system that depends entirely on live backend validation becomes fragile in such situations. If a transaction disappears due to connectivity loss, or if the system blocks a transfer without explanation, trust drops immediately. This is especially serious in financial systems where trust is central.

## Motivation
The motivation behind RuralShield came from the need to rethink digital banking security for real field conditions instead of ideal lab conditions.

### Practical motivation
- Internet cannot be assumed to be stable.
- Device quality cannot be assumed to be high.
- Fraud awareness cannot be assumed to be strong.
- Recovery options must exist when things go wrong.

### Product motivation
The system needed to feel like a real product, not just a backend assignment. That meant creating customer and admin interfaces, clear user states, monitoring controls, and a public deployment.

### Academic motivation
The project also needed to map cleanly to report sections such as architecture, methodology, implementation, results, and future scope, making it suitable for formal evaluation.

## Existing System (if any)
A typical online-first banking architecture works like this:
1. User submits a transaction.
2. Backend validates the session and request.
3. Fraud rules are checked centrally.
4. The transaction is either approved or rejected immediately.

This model is efficient under stable internet and centralized control, but it does not adapt well when the network is unreliable or when users need local continuity.

## Limitations of Existing Systems
- High dependence on continuous internet connectivity.
- Limited transparency into fraud decisions.
- Poor preservation of user intent if the transaction flow is interrupted.
- Weak adaptation to low-end devices and low-literacy user experience.
- Minimal support for delayed synchronization and staged recovery.

## Proposed Solution
RuralShield proposes an offline-first security architecture for rural digital banking. Instead of assuming live connectivity, it allows transactions to be captured locally, evaluated for risk locally, and synchronized to a central backend later. The system uses:
- **SQLite** for local-first storage,
- **PostgreSQL** for central persistence,
- **FastAPI** for backend and deployed routing,
- **JWT-based authentication** for role-aware access,
- **adaptive fraud scoring** for local decisions,
- **bank/admin analytics and controls** for review and oversight.

## Real-World Design Intention
The project is designed to answer a practical question: how should a banking platform behave when connectivity is weak, security still matters, and both customers and bank officers need a system they can trust? RuralShield is the project’s answer to that question.

## Navigation
- Previous: [[Home]]
- Next: [[Objectives-and-Scope]]
