# Admin Portal Deep Dive

## Main Responsibilities

The admin portal is the operational and analytics surface for the system. It is not just a static dashboard; it includes actions, investigations, exports, and maintenance tools.

## Dashboard Structure

The bank dashboard is split into:

- Monitoring
- Operations
- Administration
- Tools

## Monitoring Features

- overview cards
- local transactions view
- held/blocked/allowed filters
- server-backed data when available

## Analytics Features

- fraud trends by day
- risk distribution
- top fraud reasons
- high-risk users
- alerts
- device monitoring
- notifications
- user-wise comparison
- single-user insights

## Sync Queue Features

- view outbox rows and sync state
- sync one row
- sync selected rows
- sync all pending rows
- simulate night sync

## Review and Control Features

- approve held transaction
- reject held transaction
- freeze user
- unfreeze user

## Export and Audit Features

- security report page
- JSON report download
- change log CSV export
- audit chain verification
- impact report

## Demo and Maintenance Tools

- one-click demo run
- demo result page
- walkthrough page
- import local DB
- reset local DB
- seed demo data
- agent mode
