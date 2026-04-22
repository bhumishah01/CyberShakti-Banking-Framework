# Detailed Data Flow

## Login Flow

```mermaid
flowchart LR
    A["Login form"] --> B["Local PIN auth"]
    B --> C["Device trust check"]
    C --> D["Face hash verification"]
    D --> E["Cookies/session context"]
    E --> F["Optional server JWT session"]
    F --> G["Redirect to dashboard"]
```

### Customer Login Sequence
- user enters ID and PIN
- face image is captured
- local auth checks PIN and lockout state
- device is enrolled or validated
- face hash is verified
- cookies are issued for role, user, face trust, and device trust
- server JWT session is attempted if central server is up
- dashboard loads with local and optional server-backed data

## Transaction Creation Flow

```mermaid
flowchart LR
    A["Customer submits amount + recipient + PIN"] --> B["Input validation"]
    B --> C["Session key derivation"]
    C --> D["Load history/profile/failed attempts"]
    D --> E["Risk scoring"]
    E --> F["Decision mapping"]
    F --> G["Encrypt + sign transaction"]
    G --> H["Store transaction in SQLite"]
    H --> I["Queue outbox row"]
    I --> J["Create alerts/notifications/audit/change-log"]
```

## Sync Flow

```mermaid
flowchart LR
    A["Pending outbox row"] --> B["Sync requested"]
    B --> C["Send payload + idempotency key"]
    C --> D{"Server result"}
    D -->|synced| E["Mark SYNCED"]
    D -->|duplicate| F["Mark duplicate acknowledged"]
    D -->|error| G["Increment retry + set RETRYING"]
```

## Admin Review Flow

- admin opens dashboard or analytics transaction view
- held transaction is identified
- admin approves or rejects
- local transaction status changes
- outbox state changes accordingly
- notifications and/or alerts may be created

## Trusted Approval Release Flow

- customer transaction is stored as awaiting trusted approval
- approval code hash and expiry are stored
- release endpoint checks PIN, status, expiry, attempts, and code hash
- if correct, transaction is re-signed and returned to pending sync state
