# Demo

## Main Demo Link
- [https://ruralshield.onrender.com/?lang=en](https://ruralshield.onrender.com/?lang=en)

## Supporting Links
- API documentation: [https://ruralshield.onrender.com/api/docs](https://ruralshield.onrender.com/api/docs)
- Health endpoint: [https://ruralshield.onrender.com/api/health](https://ruralshield.onrender.com/api/health)
- Customer portal: [https://ruralshield.onrender.com/customer](https://ruralshield.onrender.com/customer)
- Bank/Admin portal: [https://ruralshield.onrender.com/bank](https://ruralshield.onrender.com/bank)

## Demonstration Flow
1. Open the main landing page.
2. Show the bank/admin dashboard.
3. Open the analytics page and explain risk distribution, high-risk users, and top fraud reasons.
4. Open the sync queue and explain offline-first delayed synchronization.
5. Open the customer portal.
6. Demonstrate login, send money, and history/detail behavior.
7. Show how risky transactions can be held or blocked and how admin review affects the outcome.

## Demonstration Highlights
- local-first transaction handling
- explainable fraud scoring
- customer safety controls
- device trust and biometric prototype
- sync queue visibility
- admin monitoring and analytics
- live deployed API and UI

## Video Demo Link
- Live interactive demonstration available through the deployed application links above.

## Walkthrough Summary
A customer creates a transaction under weak connectivity. The system validates the request locally, scores fraud risk, stores the record in SQLite, and queues it for sync. Later, the bank/admin side reviews and monitors the resulting state through dashboards, analytics, alerts, and queue operations.

## Navigation
- Previous: [[References]]
- Back to start: [[Home]]
