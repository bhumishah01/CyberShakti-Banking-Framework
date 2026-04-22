# Introduction

## Background of the Project
Digital banking systems are usually designed for ideal conditions: stable internet, modern smartphones, and backend availability at all times. Rural banking environments are different. Users may rely on weak connectivity, shared devices, and interfaces that need stronger clarity and trust signals. A cybersecurity framework for such users must therefore work even when the server is not immediately reachable.

## Motivation
The motivation behind RuralShield is to redesign security around rural constraints instead of treating those constraints as exceptions. Instead of letting connectivity failure break the entire flow, the system preserves actions locally, applies security checks locally, and synchronizes later. This gives the user continuity while still retaining strong fraud visibility.

## Existing System
A conventional online-first banking flow usually works like this:
1. The user submits a request.
2. The central server validates the request.
3. Fraud checks happen centrally.
4. A result is returned immediately.

This model works when the internet is reliable, but becomes fragile when network quality drops.

## Limitations of Existing Systems
- Strong dependence on continuous server access
- Limited visibility into why a transaction is flagged
- Poor support for low-end devices or delayed operations
- Weak continuity when actions happen during connectivity drops
- Less operational visibility into local-only pending actions

## Proposed Solution
RuralShield proposes an offline-first framework in which customer actions are written locally first, checked locally for fraud, and queued for later synchronization. It combines:
- local SQLite persistence
- central PostgreSQL storage
- role-based FastAPI APIs
- explainable rule-based fraud detection
- device trust awareness
- bank/admin analytics and review tools

## Navigation
- Previous: [[Home]]
- Next: [[Objectives-and-Scope]]
