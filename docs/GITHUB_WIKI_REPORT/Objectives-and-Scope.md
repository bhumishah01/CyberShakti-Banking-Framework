# Objectives and Scope

## Project Objectives
- Build an offline-first rural banking workflow.
- Preserve transaction intent locally before synchronization.
- Implement fraud scoring with human-readable explanations.
- Provide a dedicated customer portal and a separate bank/admin portal.
- Support analytics, alerts, sync review, and audit visibility.
- Deploy the system publicly for evaluation.

## Scope of the Project
### In Scope
- Customer registration and login
- Local transaction creation and fraud scoring
- Transaction history and detail views
- Safety controls (trusted contact and panic freeze)
- Bank/admin dashboard and analytics
- Sync queue and synchronization workflows
- Export/report utilities
- Docker-compatible live deployment

### Out of Scope
- Real UPI or core banking integration
- Production-grade biometric verification
- Full KYC and AML workflow
- External SMS/OTP infrastructure
- Full-scale mobile app packaging

## Applications / Use Cases
- A customer creates a transaction when internet is weak.
- The system locally scores the transaction and decides allow/hold/block.
- Pending records are synced later.
- A bank officer reviews held transactions and monitors suspicious activity.

## Expected Outcomes
- A technically complete full-stack prototype
- A clear fraud-aware workflow suited to rural banking conditions
- An academically presentable live deployment
- A system that demonstrates both security logic and operations logic

## Navigation
- Previous: [[Introduction]]
- Next: [[Literature-Survey]]
