# Security Layers

## Authentication Layer

### Local Authentication
- PIN-based identity
- scrypt hashing with salt
- lockout logic
- failed attempt counting

### Server Authentication
- JWT token creation and verification
- `/auth/login` and `/auth/me`
- dependency-based current user resolution

## Authorization Layer

Roles include:
- customer
- bank / bank_officer
- agent

Both UI routes and API routes enforce role checks.

## Encryption Layer

### Local Encryption
- AES-GCM encryption for amount and recipient
- key derivation from user PIN

### Server Encryption
- AES-GCM encryption helper for sensitive server-side fields

## Integrity Layer

- HMAC signatures over canonical transaction data
- verification during history reads
- integrity failures become explicit transaction states

## Device Trust Layer

- device enrollment in auth config
- `devices` table for trust and seen count
- new/untrusted device contributes risk

## Biometric Layer

- lightweight face image hashing
- acts as a prototype step-up signal, not a full production biometric control

## Fraud Layer

- rule-based local scoring
- trust-aware server scoring
- reasons stored and surfaced

## Audit and Logging Layer

- tamper-evident audit chain
- field-level change log
- alerts and notifications
- UI error logging
