# RuralShield: Offline-First Cybersecurity Framework for Rural Digital Banking

## Project Title
RuralShield: Offline-First Cybersecurity Framework for Rural Digital Banking

## Team Members
- Bhumi Shah (Roll No: <ADD_ROLL_NO>)  
  GitHub Profile: https://github.com/bhumishah01

## Guide / Faculty Name
- <ADD_GUIDE_NAME>

## Project Domain
Cybersecurity, FinTech, Offline-First Systems, Fraud Detection, Secure Web Platforms

## Short Description
RuralShield is a lightweight cybersecurity framework designed for rural digital banking, where internet connectivity is weak, devices are low-end, and users may have limited digital literacy. The system secures transactions through local encrypted storage, adaptive risk scoring, explainable fraud detection, and reliable delayed synchronization to a central server. It includes both a Customer Portal and a Bank/Admin Portal so that the solution can be demonstrated as a complete banking workflow rather than as an isolated backend prototype.

The project was built to align with the Smart India Hackathon problem statement on securing rural digital banking systems. It combines practical software engineering decisions with strong academic explainability, making it suitable both for real-world thinking and for project evaluation.

## Problem Statement
Rural digital banking users face a very different threat landscape compared to urban smartphone-first users. They often transact on unstable networks, use budget phones, rely on assisted banking models, and are more vulnerable to fraud due to limited awareness and fewer recovery options. Most conventional digital banking systems assume stable internet, frequent server access, and modern devices. That assumption makes them fragile in rural contexts.

The core problem addressed by RuralShield is therefore:

> How can a secure, fraud-aware, authentication-backed digital banking framework be built for rural users who may be offline for long periods, use low-resource devices, and still need trustworthy banking interactions?

## Objectives
- Build a secure digital banking workflow that functions reliably even with poor internet connectivity.
- Store sensitive transaction records safely on-device before synchronization.
- Add fraud detection that is not only accurate enough for a demo, but also explainable to bank staff and end users.
- Support customer-side safety features such as panic freeze, trusted contacts, and risk-aware transaction feedback.
- Provide a bank/admin control interface for monitoring transactions, alerts, devices, and risky users.
- Deploy the project on a live URL using a Docker-preferred setup.

## Key Features
### Offline-first transaction handling
Transactions are created and stored locally first, then synced later when connectivity becomes available.

### Adaptive fraud engine
Every transaction is evaluated for risk using a combination of static rules and behavior-aware comparisons.

### Explainable decisions
Transactions are not only allowed or blocked. The system records why they were marked risky, using human-readable reasons such as `NEW_DEVICE`, `HIGH_AMOUNT`, and `ODD_TIME`.

### Customer and bank portals
The project includes separate interfaces for rural users and bank officers, making the system more realistic and aligned with real operational flows.

### Sync queue and recovery model
Pending transactions can be synced selectively or all at once, supporting intermittent connectivity and safe retry behavior.

### Deployment-ready architecture
The final project is deployed on Render using Docker, with a live link available for demonstration and evaluation.

## Live Links
- Main application: https://ruralshield.onrender.com/
- Customer portal: https://ruralshield.onrender.com/customer
- Bank/Admin portal: https://ruralshield.onrender.com/bank
- API documentation: https://ruralshield.onrender.com/api/docs
- Health endpoint: https://ruralshield.onrender.com/health

## Repository
- GitHub Repository: https://github.com/bhumishah01/CyberShakti-Banking-Framework

## Navigation
- [[Introduction]]
- [[Objectives-and-Scope]]
- [[System-Architecture]]
- [[Technologies-Used]]
- [[Demo]]
