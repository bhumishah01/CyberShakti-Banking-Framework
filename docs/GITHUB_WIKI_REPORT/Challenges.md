# Challenges & Limitations

## Problems Faced During Development
- representing offline-first states clearly in the UI
- keeping customer and admin pages consistent while the system expanded
- making fraud logic explainable instead of opaque
- stabilizing deployment from localhost to Render
- converting implementation knowledge into polished documentation

## Limitations of the System
- face verification is prototype-grade
- no real banking rail integration exists
- no production notification gateway exists
- the balance shown in customer UI is demo-oriented rather than a full reconciled ledger
- some logic exists in both local and server layers, increasing system complexity

## Practical Failure Handling Already Present
- no internet -> local save + queue
- sync failure -> retry with backoff
- suspicious transaction -> hold or block
- repeated failed logins -> alert creation
- tampered local transaction -> integrity rejection during history read

## Navigation
- Previous: [[Results]]
- Next: [[Future-Scope]]
