# Methodology / Working

## Methodology Overview
The methodology for RuralShield was not only feature-driven, but constraint-driven. The system was built by starting from the realities of rural banking: weak internet, low-end devices, fraud vulnerability, and the need for simple but secure workflows. The working model therefore follows a local-first approach with centralized oversight.

## Step-by-Step Working of the System

### 1. User enters the system
A customer accesses the portal and logs in using the supported authentication flow. The system checks identity context and device-related trust signals. For bank/admin users, the system routes to the monitoring interface.

### 2. Transaction input is captured
The customer enters recipient and amount, or uses voice-assisted input where supported. The UI validates obvious input issues before processing begins.

### 3. Local fraud analysis runs
Before synchronization or central confirmation, the fraud engine evaluates the transaction. The following types of checks are used:
- amount vs expected behavior
- device trust state
- time-based anomaly checks
- rapid repeat transaction patterns
- prior failed attempts or suspicious context

The engine returns:
- `risk_score`
- `decision`
- `reasons`

### 4. Transaction is stored locally
The transaction is saved in the local database so that it is not lost if the connection fails. This ensures continuity and aligns with the offline-first design.

### 5. Sync queue is updated
The transaction enters the outbox/sync queue. Depending on connectivity and decision state, it may be:
- pending sync
- retrying
- held for review
- blocked
- already synced

### 6. Bank-side visibility is enabled
When data reaches the central layer, bank/admin users can review it in multiple ways:
- transaction monitoring
- high-risk user view
- suspicious alert view
- fraud trends analytics
- device monitoring

### 7. Decision follow-up happens
Held transactions can be approved or rejected. Risky users can be frozen or unfrozen. Sync queues can be processed selectively or fully.

## Algorithms / Logic Used
The project uses a hybrid logic-driven methodology rather than a heavy machine learning approach.

### Rule-based scoring
Certain clearly interpretable conditions immediately affect risk:
- new device
- high amount
- odd transaction hour
- repeated high-risk behavior
- rapid transaction burst

### Behavior profiling
The system compares the current transaction to user behavior indicators such as:
- average amount
- transaction count/frequency
- peak usage time

### Sync management strategy
The synchronization logic follows a local-first outbox model with retry tracking. This helps maintain state consistency under rural connectivity conditions.

## Data Flow Explanation
Customer input -> local validation -> fraud analysis -> local save -> sync queue -> central API -> PostgreSQL -> admin monitoring and analytics.

That flow is central to the project because it is what makes the system both resilient and explainable.
