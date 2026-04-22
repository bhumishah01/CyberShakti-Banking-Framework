# Limitations and Future Scope

## Real Limitations

- face verification is prototype-grade, not production-grade biometric verification
- admin login uses configured default credentials instead of a full admin-user lifecycle
- some behavior exists in both local and server layers, increasing complexity
- demo balance is not a full reconciled ledger
- local change log stores readable values for explanation/demo support
- no formal migration framework is used for SQLite
- no always-running background sync worker exists yet
- no real payment rail integration is present
- no external notification gateways are integrated

## Realistic Future Scope

- stronger biometric verification and liveness
- formal migration tooling
- background sync scheduler/worker
- richer trust scoring signals
- multi-factor admin authentication
- customer dispute workflows
- more modular analytics services
- SMS/WhatsApp/push notification integration
- richer server-side ledger model
- stronger server-side recipient novelty handling
