# Methodology

## Step-by-Step Working of System
1. User enters the customer or bank/admin portal.
2. Customer provides transaction details.
3. Input is validated.
4. Fraud engine computes risk score, decision, and reasons.
5. Transaction is stored locally.
6. Sync queue tracks the transaction state.
7. User receives immediate result feedback.
8. Central sync happens later.
9. Admin dashboards and analytics reflect monitored state.
10. Admin actions complete the review cycle.

## Algorithms Used (if any)
### Rule-Based Fraud Scoring
Rules check for conditions such as:
- new device
- high amount
- unusual time
- rapid repeated activity
- amount above expected average

### Behavior Profiling
The system compares current transactions against:
- average transaction amount
- frequency of transactions
- timing pattern of usage

### Suspicious Pattern Detection
The system also detects broader risk indicators such as repeated failed logins or bursts of risky transactions.

## Flowchart / Diagram
```text
User Action
 -> Validation
 -> Fraud Evaluation
 -> Local Save
 -> Sync Queue
 -> Central Server
 -> Admin Monitoring / Review
```

## Data Flow Explanation
Customer actions first create local state. That local state is then turned into synchronization state. Once synced, it becomes central operational data visible in the admin portal.

## Extra: Real-World Scenario Walkthrough
A user in a weak-network rural area creates a transaction. The app cannot depend on immediate backend confirmation, so it stores the transaction locally, evaluates it for risk, and gives the user an immediate understandable result. Later, when internet becomes available, the transaction is synchronized and becomes visible to the bank/admin layer.

## Extra: User Experience Strategy
- keep important actions clear
- avoid silent failures
- explain risk states simply
- give recovery paths instead of dead ends

## Navigation
- Previous: [[Technologies-Used]]
- Next: [[Implementation]]
