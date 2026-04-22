# Technologies Used

This page explains each important technology, acronym, or technical term in two ways:

- **What it means in general**
- **How it is used specifically in RuralShield**

This makes the page easier to use in viva, because it answers both:
- “What is this thing?”
- “Why did you use it in your project?”

## Programming Languages

| Technology | What it is in general | How it is used in RuralShield |
|---|---|---|
| **Python** | A high-level programming language commonly used for backend systems, APIs, automation, and data processing. | Python powers almost the entire backend of RuralShield, including routing, fraud logic, sync handling, local storage logic, server APIs, and deployment entrypoints. |
| **HTML** | HyperText Markup Language, the standard language used to structure web pages. | HTML is used to build the customer and bank/admin portal pages rendered through templates. |
| **CSS** | Cascading Style Sheets, used to style and visually organize web pages. | CSS is used to design dashboards, cards, tables, buttons, alerts, and page layouts in the customer and bank portals. |
| **JavaScript** | A scripting language used to make web pages interactive. | JavaScript is used in RuralShield for AJAX requests, language switching, speech-recognition-based input, and other browser-side interactions. |

## Frameworks and Core Libraries

| Technology | What it is in general | How it is used in RuralShield |
|---|---|---|
| **FastAPI** | A modern Python web framework used to build APIs and web backends quickly with validation support. | FastAPI is the main application framework in RuralShield. It powers the local UI controller, the central server API, and the combined deployed application. |
| **Jinja2** | A Python template engine used to generate dynamic HTML pages. | Jinja2 is used to render the customer portal, admin portal, analytics pages, sync pages, and report-style UI screens. |
| **SQLAlchemy** | An ORM (Object Relational Mapper) that lets developers work with databases using Python models instead of raw SQL everywhere. | SQLAlchemy is used in the central PostgreSQL server layer to define models like users, transactions, fraud logs, sync logs, and devices. |
| **Pydantic** | A Python data validation library used for structured request and response schemas. | Pydantic is used in the API layer to validate request payloads and define typed schemas for auth, transactions, sync, and other backend flows. |
| **python-jose** | A Python library used for working with JWTs and cryptographic token structures. | RuralShield uses `python-jose` to create and decode JWT tokens for authenticated server-side access. |
| **Pillow** | A Python imaging library used for opening, processing, and saving images. | Pillow is used in the face-capture/biometric prototype flow to help process captured PNG images before hashing. |
| **cryptography** | A Python cryptographic library used for secure encryption, decryption, and related operations. | RuralShield uses this library for AES-GCM encryption and other secure cryptographic functions in both local and server layers. |

## Databases and Data Storage

| Technology | What it is in general | How it is used in RuralShield |
|---|---|---|
| **SQLite** | A lightweight embedded database that stores data in a local file. | SQLite is the offline-first local database. It stores users, encrypted transactions, sync queue rows, alerts, notifications, devices, user profiles, audit logs, and change logs. |
| **PostgreSQL** | A powerful relational database commonly used for production backend systems. | PostgreSQL is used as the central deployed database behind the FastAPI server, storing server users, transactions, devices, fraud logs, and sync logs. |
| **CSV** | Comma-Separated Values, a simple tabular text format used for exports and spreadsheets. | RuralShield exports the change log into CSV so it can be reviewed outside the application. |
| **JSON** | JavaScript Object Notation, a structured text format used for exchanging data. | JSON is used throughout the project for API payloads, config-like fields, reason-code storage, intervention metadata, and downloadable reports. |

## Security and Authentication Terms

| Technology / Term | What it is in general | How it is used in RuralShield |
|---|---|---|
| **JWT** | JSON Web Token, a signed token format used to represent authenticated user sessions in APIs. | RuralShield uses JWTs for server-side login sessions so customer and bank roles can securely access central API routes. |
| **RBAC** | Role-Based Access Control, an authorization method where access depends on the user’s role. | RuralShield uses RBAC to separate customer, bank/admin, and agent capabilities across both UI and API routes. |
| **bcrypt** | A password hashing algorithm designed to safely store passwords. | RuralShield uses bcrypt in the server-side auth layer for storing and verifying central API passwords. |
| **scrypt** | A memory-hard password hashing/key derivation algorithm designed to resist brute-force attacks. | RuralShield uses scrypt in the local auth layer for PIN hashing and for deriving session keys from customer PINs. |
| **AES-GCM** | Advanced Encryption Standard in Galois/Counter Mode, an authenticated encryption method that protects both confidentiality and integrity. | In RuralShield, AES-GCM encrypts sensitive data such as transaction amount and recipient so that local and server-side sensitive fields are not stored in plaintext. |
| **HMAC** | Hash-Based Message Authentication Code, a method used to verify that data has not been tampered with and was signed by a trusted key. | RuralShield uses HMAC signatures to protect local transaction integrity, so tampered transactions can be detected during history reads. |
| **SHA-256** | A cryptographic hash function that converts data into a fixed-length digest. | RuralShield uses SHA-256 for things like phone hashing, idempotency keys, approval code hashing, and key derivation support. |
| **Face Hash / Perceptual Hash** | A compact fingerprint-like value generated from image structure, often used for similarity checking. | RuralShield uses a lightweight perceptual image hash as a prototype face verification signal during registration and login. |
| **Device Trust** | A security concept where the system tracks whether a device is known, trusted, or suspicious. | RuralShield stores device state and uses new/untrusted devices as fraud signals that can increase risk or force a hold. |
| **Lockout** | A security mechanism that temporarily blocks login after repeated failures. | RuralShield applies local lockout rules after repeated wrong PIN attempts to reduce brute-force risk. |

## Backend and Architecture Terms

| Technology / Term | What it is in general | How it is used in RuralShield |
|---|---|---|
| **API** | Application Programming Interface, a set of endpoints or methods that allow systems to communicate. | RuralShield uses APIs for auth, transactions, sync, fraud logs, admin analytics, and server-backed dashboard access. |
| **ORM** | Object Relational Mapper, a tool that maps database tables to code objects. | RuralShield uses SQLAlchemy as the ORM in the server layer. |
| **Outbox Pattern** | A reliability pattern where changes are saved locally first and sent later to another system. | RuralShield uses an outbox queue to store pending transactions that must be synced to the central server later. |
| **Idempotency Key** | A unique key used to prevent the same action from being processed multiple times. | RuralShield generates idempotency keys for synced transactions so repeated sync attempts do not create duplicate central records. |
| **Retry / Backoff** | A reliability mechanism where failed requests are retried after waiting intervals. | RuralShield schedules retries for failed sync rows and stores retry count, next retry time, and last error. |
| **Mounted App** | A web architecture pattern where one application is mounted inside another under a path prefix. | RuralShield mounts the server API at `/api` and the UI at `/` in the combined Render deployment app. |

## Deployment and Project Tools

| Technology | What it is in general | How it is used in RuralShield |
|---|---|---|
| **Docker** | A containerization platform that packages applications with their dependencies into portable containers. | RuralShield uses Docker for consistent local and deployment environments. |
| **Docker Compose** | A tool for running multiple Docker services together using one configuration file. | RuralShield uses Docker Compose locally to run UI, API, and database services together for development/demo. |
| **Render** | A cloud deployment platform for hosting web services and databases. | RuralShield is publicly deployed on Render, where the combined app serves both the UI and the API. |
| **Git** | A distributed version control system used to track code changes over time. | RuralShield uses Git for structured development, commits, and iteration tracking. |
| **GitHub** | A code hosting platform built around Git repositories. | The RuralShield repository, Wiki, and documentation are all maintained on GitHub. |
| **GitHub Wiki** | A documentation space attached to a GitHub repository. | RuralShield uses GitHub Wiki to present the formal report pages and the separate technical system-reference pages. |

## Runtime / User-Facing Terms

| Term | What it is in general | How it is used in RuralShield |
|---|---|---|
| **Customer Portal** | The end-user side of an application used by customers or clients. | In RuralShield, the customer portal allows registration, login, send money, history viewing, safety settings, and notifications. |
| **Admin Portal** | The operator or institution-facing side of a system used for oversight and control. | In RuralShield, the admin portal supports monitoring, analytics, review actions, sync management, exports, and demo tools. |
| **Agent Mode** | An assisted workflow where an operator helps a user complete actions. | RuralShield includes agent mode for assisted onboarding and assisted transactions. |
| **Analytics Dashboard** | A page that summarizes and visualizes system patterns, risks, and operational metrics. | The RuralShield analytics page shows risk distribution, top fraud reasons, fraud trends, high-risk users, devices, and alerts. |
| **Sync Queue** | A visible list of pending records waiting to be synchronized. | RuralShield exposes the local sync queue directly so the delayed-sync architecture can be monitored and controlled. |

## Summary

If your professor asks “What is this?” for any term in the stack, the easiest answer format is:

1. **general meaning** — what the technology does in software systems overall
2. **project-specific use** — why RuralShield needed it and where it appears

That is exactly how this page is structured.

## Navigation
- Previous: [[System-Architecture]]
- Next: [[Methodology]]
- Quick technical page: [[Project-Cheat-Sheet]]
