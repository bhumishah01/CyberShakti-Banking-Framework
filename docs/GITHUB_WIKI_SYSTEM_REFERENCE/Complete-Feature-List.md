# Complete Feature List

## Customer Features

- Customer registration with PIN, phone, and identity fields
- Customer login with face capture and device trust checks
- Server JWT session creation when the central API is reachable
- Customer dashboard with balance, counters, alerts, notifications, and mini statement
- Risk badge based on current customer state
- Send money through form submission
- Send money through AJAX transaction API
- Voice-assisted send command parsing
- Voice recording support through browser speech recognition in the UI
- Transaction history unlock with PIN
- Per-transaction detailed view
- Trusted contact set/remove flow
- Panic freeze flow
- Device trust visibility
- Offline simulator toggle
- Voice feedback strings for customer guidance
- Notification center and alert banners

## Admin/Bank Features

- Bank login with face capture requirement in UI
- Main dashboard split into monitoring, operations, administration, and tools
- Overview cards for users, transactions, allowed, held, blocked, pending sync
- Transaction monitoring filters
- Fraud analytics page
- User-wise analytics and single-user deep dive
- Suspicious alerts panel
- Device monitoring panel
- Notifications panel for bank role
- Sync queue page
- Sync all pending rows
- Sync one row
- Sync selected rows
- Simulate night sync
- Review local held transactions
- Review server-side transactions through central API
- Freeze/unfreeze user controls
- Export JSON security report
- Export CSV change log
- Audit event page
- Change log page
- Impact report page
- One-click demo seeding
- Demo result page
- Demo walkthrough page
- Local DB import tool
- Local DB reset tool
- Agent mode

## Agent Features

- Assisted user creation if user does not exist
- Assisted transaction creation in same flow
- Optional trusted contact setup in assisted flow
- Result summary with risk, action, status, reasons, and approval information

## Hidden/System Features

- Lockout handling after repeated PIN failures
- Alert generation for repeated failures
- Local AES-GCM encryption for amount and recipient
- Local HMAC signing for transaction integrity
- Integrity failure detection during history reads
- Audit chain verification
- Field-level change log tracking
- User behavior profile updates on every transaction
- Device tracking with trust persistence and seen count
- Retry scheduling with backoff in sync layer
- Duplicate protection through idempotency keys
- Schema backfill helpers for older SQLite files
- Friendly error page rendering instead of raw 500s in most UI cases
