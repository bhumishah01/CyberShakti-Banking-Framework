# Methodology / Working

## Methodology Overview
The development methodology for RuralShield was driven by system constraints rather than by a generic feature list. Instead of beginning with a standard web application model and then adding security, the project began with the realities of rural banking and built upward from them. This led to a methodology centered on offline-first storage, localized fraud decisions, clear UI feedback, and controlled synchronization.

## Core Working Principle
The key idea behind RuralShield is:

> capture safely first, decide locally, preserve state, and sync centrally later.

This principle is what distinguishes the system from a normal online-only banking demo.

## Step-by-Step Working of the System

### Step 1: User enters the portal
The customer opens the portal and authenticates through the supported login flow. The bank/admin user enters through a separate role-based entry point.

### Step 2: Customer initiates a transaction
The customer provides transaction details manually or through voice-assisted input.

### Step 3: Local validation is performed
Before any deeper action, the system checks that the input is valid and complete.

### Step 4: Fraud engine evaluates the transaction
The system computes:
- `risk_score`
- `decision`
- `reasons`

The decision can be:
- `ALLOWED`
- `HELD`
- `BLOCKED`

### Step 5: Transaction is stored locally
The transaction is written to the local store so that a network outage does not destroy the operation flow.

### Step 6: Sync queue is updated
The outbox records the transaction state and prepares it for future synchronization.

### Step 7: Customer receives understandable feedback
Instead of ambiguous backend errors, the system explains the result in understandable product language.

### Step 8: Admin side receives visibility
When synchronized or locally processed for monitoring, the bank/admin portal can show:
- transaction status
- fraud reasons
- suspicious patterns
- sync state
- user/device risk information

### Step 9: Admin actions are applied
The admin can:
- approve/reject held transactions
- freeze/unfreeze users
- release specific records
- monitor trends and device state

## Algorithms / Logic Used
### Rule-based risk scoring
Rules include:
- new device detection
- high amount threshold
- odd transaction time
- rapid repeated activity
- suspicious behavioral deviation

### Behavior profiling
The system compares a current transaction with:
- average transaction amount
- transaction count/frequency
- usage time patterns

### Suspicious pattern detection
The system aggregates event patterns such as:
- repeated failed logins
- high-risk bursts
- 5 transactions in 2 minutes

## Data Flow Explanation
Customer Input -> Local Validation -> Fraud Engine -> SQLite Save -> Sync Queue -> Central API -> PostgreSQL -> Admin Analytics and Review

## Why This Methodology Fits the Problem
This methodology directly addresses the challenge of rural banking security. It avoids dependence on ideal internet conditions, preserves explainability, and ensures that both users and bank staff remain part of the security process.
