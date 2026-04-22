# RuralShield System Reference

This section is separate from the formal report. It is designed as a technical reference set for explaining what RuralShield actually does in code, how its modules are wired, and how customer, admin, fraud, sync, and security layers behave internally.

Use this section when you want to:

- explain the implementation to a professor in a more technical way
- understand the full system beyond the report summary
- trace customer and bank workflows step by step
- refer to fraud, sync, database, and API behavior quickly

## Pages in This System Reference

- [[System-Overview]]
- [[Complete-Feature-List]]
- [[Architecture-Explanation]]
- [[Detailed-Data-Flow]]
- [[Fraud-Detection-System]]
- [[Behavior-Profiling]]
- [[Offline-First-System]]
- [[Customer-Portal-Deep-Dive]]
- [[Admin-Portal-Deep-Dive]]
- [[Security-Layers]]
- [[Database-Design]]
- [[API-Design]]
- [[Error-Handling-and-Validation]]
- [[Hidden-and-Internal-Logic]]
- [[Limitations-and-Future-Scope]]

## Live Links

- Main UI: [https://ruralshield.onrender.com/?lang=en](https://ruralshield.onrender.com/?lang=en)
- Customer Portal: [https://ruralshield.onrender.com/customer](https://ruralshield.onrender.com/customer)
- Bank/Admin Portal: [https://ruralshield.onrender.com/bank](https://ruralshield.onrender.com/bank)
- API Docs: [https://ruralshield.onrender.com/api/docs](https://ruralshield.onrender.com/api/docs)
- API Health: [https://ruralshield.onrender.com/api/health](https://ruralshield.onrender.com/api/health)

## Main Code Entry Points

- UI controller: `/Users/bhumi/Desktop/SEM 6/PINNACLE/CyberShakti/Cybersecurity Framework for Rural Digital Banking/src/ui/app.py`
- Local auth: `/Users/bhumi/Desktop/SEM 6/PINNACLE/CyberShakti/Cybersecurity Framework for Rural Digital Banking/src/auth/service.py`
- Fraud engine: `/Users/bhumi/Desktop/SEM 6/PINNACLE/CyberShakti/Cybersecurity Framework for Rural Digital Banking/src/fraud/engine.py`
- Local transaction store: `/Users/bhumi/Desktop/SEM 6/PINNACLE/CyberShakti/Cybersecurity Framework for Rural Digital Banking/src/database/transaction_store.py`
- Sync manager: `/Users/bhumi/Desktop/SEM 6/PINNACLE/CyberShakti/Cybersecurity Framework for Rural Digital Banking/src/sync/manager.py`
- Server API: `/Users/bhumi/Desktop/SEM 6/PINNACLE/CyberShakti/Cybersecurity Framework for Rural Digital Banking/src/server/app.py`
- Combined deploy app: `/Users/bhumi/Desktop/SEM 6/PINNACLE/CyberShakti/Cybersecurity Framework for Rural Digital Banking/src/deploy/app.py`
