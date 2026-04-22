# Objectives & Scope

## Project Objectives
- Design a secure and explainable banking transaction flow suitable for rural digital usage.
- Make the application functional even during no-internet or low-internet periods.
- Support secure local storage and delayed synchronization.
- Add adaptive risk scoring that evolves based on user transaction patterns.
- Provide a bank/admin portal with visibility into held, blocked, risky, and pending-sync records.
- Demonstrate a real-world style product with live deployment, documentation, and a full UI.

## Scope of the Project
The scope of RuralShield includes both system design and functional demonstration.

### In Scope
- FastAPI-based backend and combined deployment app
- Customer and Bank/Admin portals
- Local SQLite storage for offline-first behavior
- Central PostgreSQL database for server-side persistence
- JWT-based authentication and role separation
- Rule-based and behavior-aware fraud detection
- Notifications, alerts, analytics, and transaction review workflows
- Docker-based deployment and live hosting on Render

### Out of Scope
- Real payment rail integration such as UPI or banking core systems
- Production-grade biometric verification and liveness detection
- Telecom-backed OTP or SMS gateway integration
- Full-scale compliance automation for a real banking environment

## Applications / Use Cases
- Rural customers making secure transfers with weak internet
- Bank officers reviewing suspicious transactions before release
- Agents or assisted workflows for onboarding and support
- Offline transaction capture with later synchronization
- Fraud monitoring using trends, user risk scores, and suspicious pattern alerts

## Expected Outcomes
- A working end-to-end banking security demo with a live deployment
- A cleaner and more realistic bank-customer interaction model
- A fraud engine whose decisions are visible and interpretable
- A strong academic project artifact with architecture, methodology, implementation, and results clearly documented
