# Introduction

## Background of the Project
Digital banking has expanded rapidly, but most systems are still designed around assumptions that do not hold in rural regions. Rural users may have intermittent network access, older smartphones, and fewer fallback options if something goes wrong. A failed transaction, an unexplained block, or an insecure assisted transfer can carry more serious consequences in such contexts. Security for rural banking therefore cannot be treated as only a server-side concern. It must be embedded directly into the user workflow, the local device, and the synchronization process.

RuralShield was built with this background in mind. It aims to provide a cybersecurity framework that does not break when the internet is unavailable. Instead of depending entirely on a central server for every action, the system processes transactions locally first, applies fraud checks locally, and syncs with the server when conditions are suitable.

## Motivation
The project was motivated by three main realities:

### 1. Connectivity is not guaranteed
A large number of rural transactions happen in weak-network environments. If the application fails completely without internet, security and usability both suffer.

### 2. Fraud prevention must be understandable
In many systems, transactions are declined or flagged without clear reasoning. In a rural banking context, this can reduce trust and increase confusion. RuralShield therefore emphasizes explainable fraud output.

### 3. Banking involves more than one stakeholder
A practical system must serve both the customer and the bank. The customer needs simple, confidence-building interactions, while the bank needs visibility, analytics, and control.

## Existing System (if any)
Typical digital banking solutions focus on centralized validation. They generally follow this model:
- user submits transaction online,
- server authenticates and validates it,
- central fraud checks run,
- response is returned immediately.

This model works well when the network is stable and the device is modern, but it becomes fragile when either condition is not met.

## Limitations of Existing Systems
- They are often internet-dependent, making them unreliable in rural conditions.
- They usually do not preserve full workflows offline.
- They provide limited explainability to staff or users.
- They are not optimized for low-end devices and low-literacy UX.
- They rarely include safe synchronization logic that is central to intermittent-connectivity systems.

## Proposed Solution
RuralShield proposes an offline-first banking security model in which:
- transactions are created and stored locally using SQLite,
- a fraud engine computes risk score, decision, and reasons on-device,
- an outbox queue stores pending sync records,
- a central FastAPI server with PostgreSQL receives synchronized records,
- a bank/admin interface monitors, reviews, and controls risk.

The result is a system that treats rural constraints not as edge cases, but as the main design condition.
