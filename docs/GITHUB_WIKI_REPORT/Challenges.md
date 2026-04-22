# Challenges & Limitations

## Problems Faced During Development
### 1. Maintaining offline-first consistency
A major challenge was ensuring that local state, sync state, and admin-visible state all remained understandable and consistent.

### 2. UI reliability across many pages
As the project grew into a real demo product, the number of screens increased significantly. Ensuring language switching, clickable actions, export behavior, and subpage consistency required repeated polishing.

### 3. Balancing realism with demo practicality
The system needed to look and behave like a real rural banking product while still being feasible as a student project. This affected choices around biometrics, analytics complexity, and deployment architecture.

### 4. Deployment configuration
Moving from local setup to Render introduced issues involving database URL formats, drivers, environment variables, and keeping the deployed system aligned with the local demo.

## Limitations of the System
- Face verification in the current demo is not production-grade biometric matching.
- The project uses simulated/demo financial logic rather than actual banking integrations.
- Notification logic is UI/demo oriented and not yet connected to real messaging infrastructure.
- The fraud engine is intentionally explainable and light-weight, so it does not include heavy ML models.

## Why These Limitations Are Acceptable in This Stage
The current goal is a deployment-ready academic and prototype system, not a bank-certified production platform. The present implementation is strong enough to demonstrate architecture, security logic, workflow depth, and product thinking.
