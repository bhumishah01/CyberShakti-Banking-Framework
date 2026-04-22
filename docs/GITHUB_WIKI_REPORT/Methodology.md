# Methodology / Working

## Methodology Overview
The methodology of RuralShield is based on constraint-driven engineering. Instead of starting with a standard online-first banking design and then retrofitting security, the project starts from real rural constraints and builds the system around them. This leads to a working method where the transaction is secured locally first, risk is evaluated locally first, and synchronization happens later under controlled conditions.

## Step-by-Step Working of the System
### Step 1: User enters the portal
A customer or bank/admin user enters through the appropriate portal. Role-aware logic determines what workflows and views are accessible.

### Step 2: Transaction details are captured
The customer enters transaction information manually or via voice-assisted input.

### Step 3: Input validation occurs
Basic validation ensures the transaction request is complete and sensible before further processing.

### Step 4: Fraud engine evaluates the request
The fraud engine computes:
- `risk_score`
- `decision`
- `reasons`

Possible decisions:
- `ALLOWED`
- `HELD`
- `BLOCKED`

### Step 5: Transaction is saved locally
The system stores the transaction locally in SQLite so that user intent is preserved even if the connection is lost.

### Step 6: Sync queue state is created
The transaction enters the outbox queue and is marked with a sync-related status.

### Step 7: User receives immediate feedback
The UI explains the transaction result in a product-friendly way so that the user understands what happened.

### Step 8: Synchronization occurs later
When connectivity is available, queued items are pushed toward the central backend.

### Step 9: Admin views reflect monitored state
The bank/admin side surfaces trends, suspicious patterns, held items, high-risk users, and device trust details.

### Step 10: Admin actions close the loop
Admins can release held records, reject risky actions, freeze users, unfreeze them, or selectively sync items.

## Algorithms Used
### 1. Rule-Based Fraud Scoring
The project uses explicit rules such as:
- new device usage
- high transaction amount
- unusual time of activity
- rapid repeated activity
- amount significantly above average

### 2. Behavior Profiling
The project tracks user-related behavior indicators such as:
- average transaction amount
- frequency of transactions
- preferred transaction timing

A new transaction is compared against these patterns.

### 3. Suspicious Pattern Detection
The system also looks for higher-level risk events such as:
- multiple failed logins
- repeated high-risk decisions
- burst-like transaction behavior

## Data Flow Explanation
```text
Customer Input
   -> Validation
   -> Fraud Engine
   -> SQLite Local Save
   -> Sync Queue / Outbox
   -> FastAPI Server API
   -> PostgreSQL
   -> Admin Dashboard / Analytics / Controls
```

## Data Flow Deep Dive
### Customer-side flow
The customer interacts with the UI, but behind the scenes the system is creating local state, risk metadata, and sync metadata simultaneously.

### Admin-side flow
The admin side consumes both direct transaction state and aggregated data. This means the admin experience is not just operational, but also analytical.

## Real-World Scenario Walkthrough
Imagine a rural user trying to send money during low connectivity:
1. The user initiates a transfer.
2. The internet is weak, so the transaction cannot safely depend on immediate central confirmation.
3. The system stores the action locally.
4. Fraud scoring still happens.
5. The user receives a clear result: allowed, held, or blocked.
6. The item waits in the sync queue.
7. Later, once connectivity improves, it syncs to the server.
8. The bank portal can now review it if needed.

## User Experience Strategy
The methodology also includes UX decisions:
- use simple page structures
- avoid silent failures
- display state clearly
- keep fraud explanations understandable
- provide recovery paths instead of dead ends

## Failure Handling
- no internet -> preserve locally
- risky action -> hold or block with explanation
- sync failure -> queue and retry
- suspicious user behavior -> escalate in admin analytics

## Navigation
- Previous: [[Technologies-Used]]
- Next: [[Implementation]]
