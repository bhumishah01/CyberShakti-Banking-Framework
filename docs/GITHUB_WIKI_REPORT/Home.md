# RuralShield: Offline-First Cybersecurity Framework for Rural Digital Banking

## Project Title
**RuralShield: Offline-First Cybersecurity Framework for Rural Digital Banking**

## Team Members
- **Bhumi Shah** — Roll No: **2307883**  
  GitHub: https://github.com/bhumishah01

## Guide / Faculty Name
- **Dr. Yogesh Jadhav**

## Project Domain
- Cybersecurity
- FinTech
- Web Development
- Offline-First Systems
- Fraud Detection and Risk Monitoring

## Short Description
RuralShield is a full-stack cybersecurity framework designed for rural digital banking environments where internet connectivity is unreliable, devices are low-end, and users need simple, trustworthy interactions. The system uses local-first transaction handling, adaptive fraud scoring, explainable decisions, and delayed synchronization so that banking workflows remain usable even during connectivity gaps. It includes a customer portal, a bank/admin portal, fraud analytics, sync controls, device trust tracking, and deployment on a live URL. The project is designed to be both technically realistic and academically presentable.

## Problem Statement
Rural users often face unstable networks, shared devices, low digital literacy, and a higher likelihood of financial fraud through social engineering or suspicious transaction behavior. Most traditional banking systems assume continuous connectivity and immediate server verification, which makes them unsuitable for low-resource rural conditions. This creates a real gap between security design and field reality.

RuralShield addresses the following problem:

> How can a secure, explainable, and reliable digital banking framework be built for rural users who may operate offline for long periods, use low-end devices, and still need a trustworthy banking experience backed by fraud detection and bank-side control?

## Objectives
- Build a secure transaction system that continues to work under weak or no internet conditions.
- Preserve user actions locally so that data is not lost when connectivity drops.
- Apply fraud detection before synchronization using interpretable rules and behavior profiling.
- Provide clear explanations for why a transaction is allowed, held, or blocked.
- Support bank/admin workflows for monitoring, release, review, user control, and analytics.
- Deliver a live, Docker-based deployment suitable for demo and evaluation.

## Key Features
### Offline-first transaction workflow
Transactions are recorded locally first and synchronized later. This ensures continuity and reflects real rural connectivity conditions.

### Adaptive risk scoring
Each transaction is assigned a risk score using rule-based logic and user behavior signals such as amount patterns, device trust, and activity timing.

### Explainable fraud engine
Fraud decisions are backed by explicit reason codes like `NEW_DEVICE`, `HIGH_AMOUNT`, `ODD_TIME`, and `RAPID_BURST` instead of opaque classifications.

### Customer portal
The customer side includes transaction creation, account overview, safety controls, voice-assisted input, history, and sync awareness.

### Bank/Admin portal
The bank side includes transaction monitoring, fraud analytics, device monitoring, suspicious alerts, release/reject actions, and user freeze/unfreeze control.

### Sync queue and recovery support
The system shows pending sync, retry states, selective sync, and recovery-oriented admin controls.

### Deployment and documentation readiness
The project is deployed publicly and documented through repository docs and GitHub Wiki for academic evaluation.

## Primary Live Link
- **Main deployed page:** https://ruralshield.onrender.com/?lang=en

## Supporting Technical Links
- API documentation: https://ruralshield.onrender.com/api/docs
- Health endpoint: https://ruralshield.onrender.com/health
- Customer portal: https://ruralshield.onrender.com/customer
- Bank/Admin portal: https://ruralshield.onrender.com/bank

## Repository Link
- GitHub Repository: https://github.com/bhumishah01/CyberShakti-Banking-Framework

## Why This Project Is Valuable
RuralShield is valuable because it does not treat rural banking as a simplified version of normal online banking. Instead, it redesigns the architecture around real constraints: delayed connectivity, low-resource devices, fraud vulnerability, and the need for explainable workflows. This makes the project stronger both as a cybersecurity solution and as a product-thinking exercise.

## Navigation
- Next: [[Introduction]]
- Architecture: [[System-Architecture]]
- Technology Stack: [[Technologies-Used]]
- Demo: [[Demo]]
