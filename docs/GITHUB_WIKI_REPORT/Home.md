# RuralShield

## Project Title
**RuralShield: Offline-First Cybersecurity Framework for Rural Digital Banking**

## Team Members
- **Bhumi Shah** — Roll No: **2307883**  
  GitHub: [bhumishah01](https://github.com/bhumishah01)

## Guide / Faculty Name
- **Dr. Yogesh Jadhav**

## Project Domain
- Cybersecurity
- FinTech
- Web Development
- Offline-First Systems
- Fraud Detection

## Short Description
RuralShield is a rural-first digital banking security system designed for environments where internet connectivity is unreliable and devices are low-end. It uses local SQLite storage, explainable fraud scoring, delayed synchronization, and bank-side monitoring to keep transactions secure and understandable. The system includes separate customer and bank/admin portals, a sync queue, analytics, alerts, and a live public deployment.

## Problem Statement
Most banking systems assume stable internet, immediate server access, and digitally confident users. In rural settings, those assumptions often fail. This increases the risk of incomplete transactions, fraud exposure, and user confusion. RuralShield addresses this by making transaction workflows work locally first, evaluating risk before sync, and giving both customers and bank officers clear visibility into what happened and why.

## Objectives
- Build a transaction workflow that remains functional under weak or no internet.
- Detect suspicious behavior before synchronization using explainable fraud rules.
- Maintain a secure local record of user activity and transaction state.
- Provide role-based customer and bank/admin portals.
- Support sync, review, analytics, and audit visibility.
- Deploy the project publicly using a Docker-friendly setup.

## Key Features
- Offline-first local transaction handling
- Explainable fraud detection with risk score and reasons
- Sync queue with retry, selected sync, and one-record sync
- Customer safety controls: trusted contact and panic freeze
- Admin analytics: fraud trends, top reasons, high-risk users, device monitoring
- Audit chain, change log, alerts, and notifications
- Render deployment with live links

## Main Links
- Main page: [https://ruralshield.onrender.com/?lang=en](https://ruralshield.onrender.com/?lang=en)
- Customer portal: [https://ruralshield.onrender.com/customer](https://ruralshield.onrender.com/customer)
- Bank/Admin portal: [https://ruralshield.onrender.com/bank](https://ruralshield.onrender.com/bank)
- API docs: [https://ruralshield.onrender.com/api/docs](https://ruralshield.onrender.com/api/docs)
- Health endpoint: [https://ruralshield.onrender.com/api/health](https://ruralshield.onrender.com/api/health)

## Quick Navigation
- Start report: [[Introduction]]
- Jump to architecture: [[System-Architecture]]
- Jump to implementation: [[Implementation]]
- Jump to live demo section: [[Demo]]
- Technical cheat sheet: [[Project-Cheat-Sheet]]
