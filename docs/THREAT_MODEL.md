# Threat Model (Step 1)

## 1. Assets to Protect

- User identity and credential material.
- Transaction details and metadata.
- Fraud scores and risk decisions.
- Audit logs.
- Sync payloads.

## 2. Threat Actors

- Device thief with physical access.
- Malware on compromised device.
- Network attacker on public/untrusted Wi-Fi.
- Insider manipulating local records.

## 3. Primary Threats

- Unauthorized app access.
- Local database exfiltration.
- Payload tampering before sync.
- Replay and duplicate transaction injection.
- Fraud attempts using stolen PIN.

## 4. Security Controls

- PIN-first auth + lockout thresholds.
- Encryption for sensitive fields at rest.
- OS-backed key storage.
- Record-level signatures and verification.
- Idempotency keys on sync.
- Hash-linked append-only audit log.

## 5. Assumptions

- Device OS provides secure keystore support.
- TLS is available during sync.
- User has occasional connectivity windows.

## 6. Open Decisions for Step 2

- Exact crypto library choice.
- Key derivation and rotation policy.
- Step-up auth thresholds for high-risk transactions.
- Audit retention and log pruning strategy.
