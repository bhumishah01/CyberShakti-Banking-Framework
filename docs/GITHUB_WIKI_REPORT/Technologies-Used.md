# Technologies Used

## Overview
The technology stack for RuralShield was selected to support four project needs simultaneously:
- rapid prototyping,
- structured backend logic,
- full-stack integration,
- and deployment on a live public URL.

The stack also needed to support offline-first behavior, local database handling, server-side database migration, and relatively lightweight deployment. As a result, the final tech stack combines Python-based backend tooling, template-driven frontend rendering, Docker deployment, and both local and server-side databases.

## Programming Languages
### Python 3.11
Python is the primary language used across the system. It powers:
- backend route handling,
- authentication logic,
- fraud scoring,
- synchronization behavior,
- deployment entrypoints,
- analytics preparation,
- and data validation.

### HTML
HTML is used for customer and admin templates. It provides the structural layout for dashboards, forms, analytics sections, and multi-page flows.

### CSS
CSS is used to create the actual product experience: layout spacing, cards, status tags, typography, tables, alerts, and responsive sections.

### JavaScript
JavaScript is used selectively for interactivity such as:
- language switching,
- speech interaction support,
- button handling,
- front-end UX enhancements,
- dynamic navigation behavior.

## Frameworks and Libraries
### FastAPI
FastAPI is the central web framework used to build both backend endpoints and route-connected functionality. It was chosen because it provides:
- clean routing,
- strong integration with Pydantic,
- automatic API docs,
- and good structure for modular development.

### Jinja2
Jinja2 is used for server-rendered templates. It makes the customer and admin portals easy to deploy within the same application while keeping the UI fully dynamic.

### SQLAlchemy
SQLAlchemy is used for structured interaction with the server-side PostgreSQL database. It provides model definitions, sessions, and central data access patterns.

### Pydantic
Pydantic is used for input validation and typed data structures. This improves API reliability and reduces silent failures.

### python-jose
Used for JWT token generation and decoding in authenticated server flows.

### passlib[bcrypt]
Used for hashing credentials securely.

### cryptography
Used for sensitive field protection and encryption-related logic.

### Pillow
Used in the prototype for image-related handling in face-capture flows.

## Databases
### SQLite
SQLite is used as the offline-first local database. It was chosen because it is lightweight, file-based, simple to ship, and well suited for constrained environments.

Uses in the project:
- local transaction persistence
- pending sync queue
- cached user/session context
- demo continuity and local-first state

### PostgreSQL
PostgreSQL is used as the central deployed database. It supports stronger relational design, indexing, and multi-user server-side persistence.

Uses in the project:
- users
- transactions
- fraud logs
- devices
- sync queue state
- admin analytics source data

## Tools and Platforms
### Docker
Docker is used to containerize the project and make deployment portable and reproducible.

### docker-compose
Used in local development to run the application stack together and simulate a more realistic environment.

### Git and GitHub
Used for source control, structured commit history, collaboration support, documentation hosting, and Wiki/report preparation.

### GitHub Wiki
Used to publish the final project report in the required academic structure.

### Render
Used to deploy the application publicly. Render was chosen because it supports full-stack Docker deployments and integrates cleanly with GitHub.

## Tech Stack Summary Table
| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| UI Rendering | Jinja2 + HTML + CSS + JS |
| Web Framework | FastAPI |
| Local Database | SQLite |
| Server Database | PostgreSQL |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Auth | JWT + python-jose + passlib |
| Encryption | cryptography |
| Image Handling | Pillow |
| Local Containerization | Docker / docker-compose |
| Live Hosting | Render |
| Version Control | Git + GitHub |
| Report Hosting | GitHub Wiki |

## Why This Tech Stack Was Chosen
This stack balances clarity, capability, and deployability. It is strong enough to demonstrate real system architecture, yet simple enough to remain understandable and maintainable for an academic project. It also helped ensure that the final output was not only functional locally, but actually available as a live deployed system.
