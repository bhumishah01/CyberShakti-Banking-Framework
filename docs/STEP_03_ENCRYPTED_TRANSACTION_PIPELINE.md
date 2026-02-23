# Step 3: Encrypted Transaction Storage Pipeline

## What was implemented

- AES-GCM encryption helpers and HMAC integrity signatures in `src/crypto/service.py`.
- Key separation from session key (`enc_key`, `sig_key`).
- Secure transaction store service in `src/database/transaction_store.py`.

## Pipeline now

1. User is authenticated using PIN.
2. Session key is derived.
3. Amount and recipient are encrypted.
4. Canonical transaction record is signed.
5. Encrypted record is written to `transactions`.
6. Encrypted sync packet is written to `outbox` with `PENDING` state.
7. Reads verify signature before decrypting.

## Security controls added

- AES-GCM for confidentiality + tamper-resistant ciphertext.
- HMAC-SHA256 over canonical JSON to detect modification.
- Integrity check enforced on read path.

## Tests added

- Encrypted storage and successful decryption retrieval.
- Outbox payload creation in pending sync state.
- Tampering detection via signature verification failure.

Result: `6 passed`.
