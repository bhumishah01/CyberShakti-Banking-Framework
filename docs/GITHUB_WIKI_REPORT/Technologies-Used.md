# Technologies Used

## Programming Languages
### Python
**Python** is the primary backend language. It powers routing, business logic, fraud scoring, sync handling, data access, and deployment entrypoints.

### HTML
**HTML (HyperText Markup Language)** structures the customer and admin templates.

### CSS
**CSS (Cascading Style Sheets)** controls layout, tables, dashboards, cards, alerts, and page styling.

### JavaScript
**JavaScript** is used for UI interactivity such as AJAX requests, language switching, speech recognition, and dynamic customer actions.

## Frameworks / Libraries
### FastAPI
**FastAPI** is the main web framework. It is used for both the central API and the mounted web interface.

### Jinja2
**Jinja2** is the template engine used to render dynamic HTML pages.

### SQLAlchemy
**SQLAlchemy** is an ORM (Object Relational Mapper). It helps define and access PostgreSQL-backed server models using Python objects.

### Pydantic
**Pydantic** is used for input validation and typed API schemas.

### python-jose
Used for working with **JWT (JSON Web Tokens)**.

### passlib / bcrypt
Used for secure password hashing in the server-side auth layer.

### cryptography
Used for AES-GCM encryption and other cryptographic operations.

### Pillow
Used for image handling in the prototype face-capture flow.

## Databases
### SQLite
Used as the local offline-first operational database.

### PostgreSQL
Used as the central shared database for the deployed API.

## Tools
### Docker
Used for containerized local/dev deployment and Render-friendly packaging.

### Docker Compose
Used to run multiple local services together, such as UI, API, and database.

### Git and GitHub
Used for version control, documentation, and Wiki publishing.

### Render
Used for live public deployment.

## Hardware / Runtime Context
- Laptop/webcam for face capture demo
- browser-based portals for customer and bank roles
- low-end/rural-device constraints simulated through offline-first architecture rather than requiring special hardware

## Why This Stack Fits the Project
This tech stack is strong for RuralShield because it supports:
- lightweight deployment
- clear backend control
- offline-first local persistence
- public live hosting
- security-focused business logic without unnecessary frontend complexity

## Navigation
- Previous: [[System-Architecture]]
- Next: [[Methodology]]
