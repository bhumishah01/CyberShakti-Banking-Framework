# Objectives & Scope

## Project Objectives
The project objectives were defined to balance technical depth, usability, and realism.

- To create an offline-first secure transaction framework.
- To ensure that transactions can be stored safely before synchronization.
- To implement fraud scoring with explainable outputs.
- To provide customer-side safety tools such as panic freeze and trusted contacts.
- To provide bank/admin-side dashboards, analytics, and review controls.
- To support a live deployment model using Docker and Render.
- To structure the project as a complete, evaluation-ready system rather than as isolated modules.

## Scope of the Project
### In Scope
- Customer portal and bank/admin portal
- Local SQLite storage and deployed PostgreSQL storage
- JWT-based authentication and role-aware routing
- Offline-first transaction capture and outbox sync queue
- Fraud scoring, fraud reasons, suspicious alerts, analytics
- Voice-assisted transaction input and feedback support
- Live Render deployment and GitHub Wiki reporting

### Out of Scope
- Real bank core or UPI integration
- Production biometric identity verification
- Enterprise-grade fraud ML pipelines
- Regulatory-grade KYC and AML integration
- Real SMS, IVR, or telecom gateway services

## Applications / Use Cases
### Customer-side use cases
- creating a transaction under weak internet conditions
- understanding why a transaction is risky
- checking pending sync or held transaction status
- using safety features to reduce personal risk

### Admin-side use cases
- reviewing held transactions
- monitoring fraud trends and suspicious patterns
- analyzing high-risk users and device states
- controlling sync release and freeze/unfreeze actions

### Academic/demo use cases
- demonstrating a live full-stack project
- showing end-to-end system architecture
- presenting explainable fraud handling rather than black-box output

## Expected Outcomes
The expected outcomes include both technical and presentation outcomes:
- a reliable prototype for rural banking security workflows
- a deployed live application accessible through a public URL
- a system with clear fraud explanation and operational controls
- a project strong enough for viva/demo/report evaluation

## What Makes the Scope Appropriate
The project does not attempt to solve every part of modern banking. Instead, it chooses one difficult and relevant slice: secure rural digital banking under offline-first conditions. That makes the scope focused, defensible, and meaningful.

## Navigation
- Previous: [[Introduction]]
- Next: [[Literature-Survey]]
