# Technologies Used

## Overview
The RuralShield tech stack was chosen to support a project that is simultaneously a working product demo, a cybersecurity system, and an evaluation-ready academic submission. The stack needed to support local-first storage, server deployment, user-facing portals, authentication, fraud scoring, analytics, and documentation. For that reason, the final stack combines Python-based backend development, template-driven frontend rendering, dual-database strategy, Docker deployment, and GitHub-based documentation.

## Programming Languages
### Python 3.11
Python is the core language used across the project. It powers:
- backend APIs,
- route handling,
- fraud scoring logic,
- synchronization behavior,
- deployment entrypoints,
- data processing,
- and state validation.

### HTML
HTML is used for the customer and admin templates. It structures the dashboards, forms, tables, monitoring views, analytics sections, and report-friendly layouts.

### CSS
CSS is used to turn the project into a presentable product. It controls card layouts, tables, tags, spacing, headings, alerts, graph containers, and responsive design.

### JavaScript
JavaScript is used where interactivity is required, including:
- language switching,
- voice interaction handling,
- event-based button behavior,
- page-level refresh/control logic,
- and lightweight frontend UX improvements.

## Frameworks / Libraries
### FastAPI
FastAPI is the central web framework. It was chosen because it supports:
- clean routing,
- strong API structure,
- mounted deployment paths,
- automatic Swagger docs,
- and a Python-first development model.

### Jinja2
Jinja2 is used for server-rendered pages. It allows the customer and admin portals to remain tightly integrated with backend state while still giving strong UI control.

### SQLAlchemy
SQLAlchemy is used for structured interaction with PostgreSQL. It supports model definitions, database sessions, and central persistence handling.

### Pydantic
Pydantic is used for typed request and response validation, improving API safety and consistency.

### python-jose
Used for JWT token generation and validation.

### passlib[bcrypt]
Used for hashing authentication-related values securely.

### cryptography
Used for encryption-related operations and sensitive field protection.

### Pillow
Used in the project’s face-capture/image-handling flow.

## Databases
### SQLite
SQLite is used as the local offline-first database.

**Why used:**
- lightweight
- file-based
- simple to ship and reset
- ideal for offline-first persistence

**Used for:**
- local transaction storage
- pending sync queue state
- demo continuity
- local-first user/session state

### PostgreSQL
PostgreSQL is used as the central deployed database.

**Why used:**
- stronger central persistence
- better relational structure
- realistic server-side storage for a deployed banking backend

**Used for:**
- users
- transactions
- fraud logs
- device state
- sync and admin-side monitoring data

## Tools
### Docker
Docker is used for containerization and consistent deployment.

### docker-compose
Used for local orchestration of the application stack during development.

### Git
Used for source control and structured commit history.

### GitHub
Used for repository hosting, progress tracking, collaboration, and report support.

### GitHub Wiki
Used for the final project report in the required academic structure.

### Render
Used for live full-stack deployment on a public URL.

## Hardware (Applicable Context)
While the project is web-based, the design assumes interaction on low-end smartphones or constrained computing devices. In addition:
- a webcam-capable device was used for face capture simulation
- a regular laptop environment was used for development, testing, and deployment

## Tech Stack Summary Table
| Layer | Technology |
|---|---|
| Backend Language | Python 3.11 |
| Frontend Rendering | HTML + CSS + JavaScript + Jinja2 |
| Web Framework | FastAPI |
| Local Database | SQLite |
| Central Database | PostgreSQL |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Authentication | JWT, python-jose, passlib |
| Encryption Support | cryptography |
| Image Handling | Pillow |
| Deployment | Docker, docker-compose, Render |
| Version Control | Git, GitHub |
| Documentation Hosting | GitHub Wiki |

## Why This Tech Stack Fits the Project
This stack is well suited to the project because it balances clarity, speed, deployability, and realism. It is strong enough to demonstrate a real product workflow, but still understandable enough to document in an academic report.

## Navigation
- Previous: [[System-Architecture]]
- Next: [[Methodology]]
