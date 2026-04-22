# Challenges & Limitations

## Problems Faced During Development
### 1. Aligning offline-first behavior with a clean demo UX
Offline-first logic is technically useful, but it can easily become confusing for users if states such as pending, held, retrying, and synced are not explained clearly. A major challenge was making these states visible and understandable.

### 2. Growing from prototype to product-style demo
As the project evolved, the requirement shifted from “make the features work” to “make the system feel real.” This required a large amount of work in layout refinement, navigation consistency, analytics clarity, and workflow polish.

### 3. Keeping explainability intact
As more fraud logic, alerts, and analytics were added, there was a risk of the system becoming harder to interpret. Maintaining explainability across customer and admin views remained an ongoing design priority.

### 4. Deployment and configuration issues
Moving the system from local development to Render involved challenges related to:
- database drivers,
- environment variables,
- database URL formats,
- service health checks,
- and consistency between local and deployed data states.

### 5. Documentation and academic packaging
Another challenge was presenting the system in a form that satisfies both technical and academic evaluation. This required a proper Wiki structure, polished report writing, and clearer mapping between features and project goals.

## Limitations of the System
- Face verification is prototype-level and not a production biometric solution.
- Banking logic is simulated and not connected to live financial rails.
- Notification systems are demo-oriented and not integrated with SMS or official messaging infrastructure.
- The fraud engine is intentionally lightweight and explainable rather than ML-heavy.

## Why These Limitations Are Acceptable
The current system is best understood as a serious prototype. It demonstrates architecture, reasoning, controls, and deployment without pretending to be a production banking platform. That level is appropriate for the current project scope and evaluation context.
