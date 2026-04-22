# RuralShield: Offline-First Cybersecurity Framework for Rural Digital Banking

## Project Title
RuralShield: Offline-First Cybersecurity Framework for Rural Digital Banking

## Team Members
- Bhumi Shah (Roll No: 2307883)  
  GitHub Profile: https://github.com/bhumishah01

## Guide / Faculty Name
- Dr. Yogesh Jadhav

## Project Domain
Cybersecurity, FinTech, Digital Banking Security, Offline-First Systems, Fraud Detection, Secure Web Platforms

## Short Description
RuralShield is a security-focused digital banking framework designed specifically for rural operating conditions, where internet connectivity is unstable, devices are low-end, and users may require simple and trustworthy interactions. The system combines offline-first transaction handling, local secure storage, adaptive fraud scoring, explainable fraud decisions, and centralized monitoring through a bank/admin portal. Instead of assuming constant connectivity, RuralShield treats offline operation as a primary requirement and builds around it.

The project has been designed as both a technical prototype and a product-oriented solution. It demonstrates how a banking system can remain useful and safe even when a user cannot immediately reach the central server. At the same time, it gives the bank visibility into risky transactions, suspicious activity, and synchronization workflows. This makes the system relevant not only as a coding project but also as a deployable concept aligned with real rural banking constraints.

## Problem Statement
Rural digital banking users face a different set of challenges from mainstream urban users. They often operate on weak or intermittent networks, use shared or low-resource smartphones, and may not fully understand why a transaction is flagged or blocked. At the same time, they remain vulnerable to common fraud patterns such as suspicious receivers, social engineering, unauthorized device usage, and repeated risky transfers. Most existing digital banking prototypes assume always-online verification, modern devices, and highly literate digital users.

The problem addressed by RuralShield is therefore:

> How can a secure, explainable, and practical digital banking framework be built for rural users who may be offline for long periods, use low-end devices, and still need trustworthy banking transactions and bank-side protection?

## Objectives
- Build a secure banking workflow that remains functional during weak or no internet conditions.
- Store transaction and safety-critical data locally first, so the system does not fail under poor connectivity.
- Add fraud detection that produces both a risk score and interpretable reasons.
- Support customer-side safety controls such as panic freeze, trusted contacts, risk notifications, and device trust visibility.
- Provide a bank/admin control interface for transaction review, sync monitoring, fraud analytics, and user risk control.
- Demonstrate the final system through a public live deployment using a Docker-based setup.

## Key Features
### 1. Offline-First Transaction Handling
Transactions are created and stored locally first, then synchronized later when internet becomes available. This reflects real rural conditions and reduces workflow failure.

### 2. Adaptive Fraud Engine
Each transaction is evaluated using both fixed rule logic and user behavior signals such as amount patterns, time of use, device trust, and repeated risky actions.

### 3. Explainable Fraud Decisions
The system does not simply say “fraud” or “not fraud.” It records clear reason codes such as `NEW_DEVICE`, `HIGH_AMOUNT`, `ODD_TIME`, `RAPID_BURST`, and `HIGH_AMOUNT_VS_AVG` so that decisions are reviewable and understandable.

### 4. Customer and Bank/Admin Portals
The project includes separate interfaces for customers and bank/admin users, creating a more realistic and operationally complete system.

### 5. Sync Queue and Recovery Model
Pending records can be retried, selectively synced, or processed in batches. This creates a practical bridge between offline storage and central authority.

### 6. Deployment-Ready Productization
The project is deployed live on Render and organized with Docker, structured documentation, Git history, and a report-ready Wiki.

## Primary Live Link
- Main Project Page: https://ruralshield.onrender.com/?lang=en

## Supporting Technical Links
These links are included in the report because they help demonstrate that the deployment is real, healthy, and inspectable:
- API documentation: https://ruralshield.onrender.com/api/docs
- Health endpoint: https://ruralshield.onrender.com/health
- Customer portal: https://ruralshield.onrender.com/customer
- Bank/Admin portal: https://ruralshield.onrender.com/bank

## Repository
- GitHub Repository: https://github.com/bhumishah01/CyberShakti-Banking-Framework

## Why This Project Matters
RuralShield goes beyond a generic banking demo. It focuses on reliability under real constraints, transparency of security decisions, and usability for both customers and bank personnel. Its value lies not only in what it does technically, but in the way it rethinks banking security for rural digital contexts.

## Navigation
- [[Introduction]]
- [[Objectives-and-Scope]]
- [[Literature-Survey]]
- [[System-Architecture]]
- [[Technologies-Used]]
- [[Methodology]]
- [[Implementation]]
- [[Results]]
- [[Demo]]
