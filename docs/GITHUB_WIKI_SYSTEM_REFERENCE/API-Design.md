# API Design

## Central API Routes

### Auth
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

### Transactions
- `POST /transactions`
- `GET /transactions/me`
- `GET /transactions`
- `POST /transactions/{tx_id}/review`

### Sync
- `POST /sync/push`
- `POST /sync/push_v2`
- `GET /sync/logs`
- `GET /sync/status`

### Fraud
- `GET /fraud/logs`

### Agent
- `POST /agent/onboard`
- `POST /agent/assisted-transaction`

### Legacy Compatibility
- `POST /sync/transactions`
- `GET /rules`
- `POST /rules`

## Local/UI JSON Routes

### Customer
- `GET /customer/api/summary`
- `POST /customer/api/transactions`
- `POST /customer/api/voice`

### Admin
- `GET /admin/api/fraud-trends`
- `GET /admin/api/high-risk-users`
- `GET /admin/api/alerts`
- `GET /admin/api/devices`
- `GET /admin/api/transactions`
- `GET /admin/api/user-profile/{user_id}`
- `POST /admin/api/transactions/{tx_id}/review`
- `POST /admin/api/users/{user_id}/freeze`
- `POST /admin/api/users/{user_id}/unfreeze`

## UI Interaction Pattern

The UI uses a mix of:
- traditional form submissions
- redirect + flash cookies
- AJAX JSON requests for smoother customer flows
- JWT-backed API fetches when the server is reachable
