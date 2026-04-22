# Challenges & Limitations

## Problems Faced During Development
### 1. Offline-first logic is hard to present cleanly
States such as pending, held, retrying, and synced are technically meaningful, but they can confuse users if not surfaced properly.

### 2. Product polish required repeated rework
Once the system became larger, many pages needed refinement to feel consistent. This included alignment, language handling, navigation, export behavior, and analytics presentation.

### 3. Explainability had to be preserved across growth
As more fraud-related features were added, it became easy for the system to feel noisy or overly technical. Care had to be taken so that explanations remained useful.

### 4. Deployment was not trivial
Moving from localhost to Render required handling database drivers, environment variables, service paths, public links, and live persistence.

### 5. Documentation had to become report-grade
The Wiki had to be rewritten from a basic structure into a genuinely detailed report that did not look copied or generic.

## Limitations of the System
- biometric verification is still prototype-level
- no real banking rails are integrated
- notifications are not connected to production messaging infrastructure
- fraud scoring remains intentionally light and explainable rather than fully ML-driven

## Failure Handling Summary
- no connectivity -> keep local state intact
- suspicious activity -> raise alerts and risk score
- sync failure -> retain queued record
- admin review requirement -> hold until decision

## Why These Limitations Are Reasonable
The current goal is a strong prototype and academic submission, not a certified commercial banking platform. The present version demonstrates the right system thinking, even if some integrations remain future work.

## Navigation
- Previous: [[Results]]
- Next: [[Future-Scope]]
