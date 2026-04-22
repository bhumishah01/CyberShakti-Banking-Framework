# Objectives-and-Scope

## Project Objectives
- To design an offline-first transaction workflow for rural banking use.
- To secure local transaction storage before synchronization.
- To implement fraud detection with explainable outputs.
- To provide separate customer and bank/admin experiences.
- To support analytics, monitoring, and review actions for risky activity.
- To deploy the project publicly for demonstration and evaluation.

## Scope of the Project
### In Scope
- Customer portal
- Bank/admin portal
- Local SQLite-based persistence
- Central PostgreSQL-backed server storage
- JWT-based role-aware access
- Fraud scoring, alerts, sync queue, and device monitoring
- Docker-based deployment and public hosting

### Out of Scope
- Real UPI or core banking integration
- Production-grade biometric identity verification
- Full KYC/AML workflow
- Telecom-based SMS/OTP infrastructure

## Applications / Use Cases
- Customer creates a transaction in weak-network conditions
- Bank/admin reviews held transactions
- Admin monitors suspicious patterns and high-risk users
- System preserves local state until sync becomes possible

## Expected Outcomes
- A working live deployment with both customer and admin portals
- A secure transaction workflow that handles low-connectivity conditions
- A readable and explainable fraud monitoring framework
- A project that is technically strong and academically presentable

## Navigation
- Previous: [[Introduction]]
- Next: [[Literature-Survey]]
