# Objectives & Scope

## Project Objectives
The primary goal of RuralShield is to design a digital banking security framework that remains practical and safe in rural usage conditions. The objectives of the project are:

- To create an offline-first banking flow that does not collapse under poor internet conditions.
- To support secure local storage of transaction data before synchronization.
- To implement fraud detection that produces both a score and a reasoned explanation.
- To create role-based interfaces for both customers and bank/admin users.
- To provide an admin control layer for approvals, alerts, analytics, and freeze/unfreeze operations.
- To deploy the complete project on a live public URL for demonstration and evaluation.
- To document the project in a form suitable for academic review and technical discussion.

## Scope of the Project
The scope of RuralShield includes system architecture, frontend-backend integration, fraud-aware transaction workflows, synchronization management, and deployment.

### In Scope
- Customer portal with secure login, transaction creation, history, notifications, and safety settings
- Bank/Admin portal with dashboard, analytics, sync queue, device monitoring, alert review, and transaction controls
- Local SQLite database for offline-first workflows
- Central PostgreSQL database for deployed backend persistence
- Adaptive fraud scoring and explainable rule outputs
- Voice-assisted transaction input and feedback simulation
- Docker-based deployment on Render
- GitHub documentation and Wiki report support

### Out of Scope
- Real bank core or UPI integration
- Production-grade biometric identity verification and liveness detection
- National-scale infrastructure and compliance automation
- Live telecom-based OTP/SMS infrastructure
- Full KYC/AML onboarding stack

## Applications / Use Cases
RuralShield is designed around practical use cases rather than abstract features.

### Customer-side use cases
- making a secure transfer when internet is weak
- viewing why a transaction was held or blocked
- checking risk indicators and notifications
- using safety settings such as panic freeze or trusted contact management

### Bank/Admin use cases
- reviewing held transactions
- tracking fraud trends and high-risk users
- monitoring sync queues and delayed records
- inspecting trusted/untrusted devices for suspicious behavior
- freezing or unfreezing users based on risk

### Evaluation and demo use cases
- showing a live URL with both portals
- demonstrating fraud explainability and sync behavior
- presenting an academically structured end-to-end project

## Expected Outcomes
The expected outcomes of the project are not limited to a working app. The project aims to deliver:
- a complete prototype architecture,
- a realistic rural banking workflow,
- measurable and interpretable risk logic,
- a strong deployment story,
- and a professional documentation/report structure.

## Boundary of the Current Version
The current project version should be understood as a strong prototype and deployable academic system, not as a regulated banking product. Its strength lies in architecture, realism, explainability, and product completeness.
