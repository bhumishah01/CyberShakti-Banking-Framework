# Technologies-Used

## Programming Languages
### Python
**Python** is the main backend programming language used in the project. It powers authentication, routing, fraud logic, synchronization logic, analytics processing, and deployment entrypoints.

### HTML
**HTML (HyperText Markup Language)** is used to structure customer and admin templates.

### CSS
**CSS (Cascading Style Sheets)** is used for layout, styling, tables, dashboards, alerts, and page presentation.

### JavaScript
**JavaScript** is used for interactive frontend behavior such as language switching, button actions, and voice-related handling.

## Frameworks / Libraries
### FastAPI
**FastAPI** is the main backend web framework. It is used to build API routes and mounted web application flows.

### Jinja2
**Jinja2** is a template engine used to render dynamic HTML pages for the customer and admin portals.

### SQLAlchemy
**SQLAlchemy** is an ORM (Object Relational Mapper). It helps the application interact with the PostgreSQL database using structured Python models.

### Pydantic
**Pydantic** is used for typed validation of inputs and structured request/response handling.

### python-jose
Used for JWT handling.

### JWT
**JWT (JSON Web Token)** is used for token-based authentication and secure role-aware access.

### passlib[bcrypt]
Used for hashing credentials securely.

### bcrypt
**bcrypt** is a password hashing algorithm designed to store credentials securely.

### cryptography
Used for encryption-related operations and sensitive data handling.

### Pillow
**Pillow** is an image-processing library used in the face-capture related parts of the project.

## Tools
### Docker
**Docker** is a containerization platform. It packages the application so it can run consistently across systems and deployment environments.

### docker-compose
**docker-compose** is used to run multiple local services together during development.

### Git
**Git** is the version control system used to track changes in the project.

### GitHub
**GitHub** is used to host the repository, commits, and documentation.

### GitHub Wiki
The GitHub Wiki is used to publish the final report in the required structured format.

### Render
**Render** is the cloud platform used to deploy the application on a live public URL.

## Databases
### SQLite
**SQLite** is the local database used for offline-first storage and pending sync state.

### PostgreSQL
**PostgreSQL** is the central server-side relational database used in the deployed system.

## Hardware (if applicable)
- Low-end smartphone assumption for user-side design
- Webcam-capable development device for face capture simulation
- Standard development laptop for coding, testing, and deployment

## Tech Stack Summary Table
| Category | Technology | Meaning / Purpose |
|---|---|---|
| Backend Language | Python | Core application logic |
| Frontend | HTML, CSS, JavaScript | UI structure, style, interaction |
| Web Framework | FastAPI | API and mounted app routing |
| Template Engine | Jinja2 | Dynamic page rendering |
| Local Database | SQLite | Offline-first storage |
| Central Database | PostgreSQL | Deployed server persistence |
| ORM | SQLAlchemy | Structured database access |
| Validation | Pydantic | Typed validation |
| Auth | JWT, python-jose, passlib | Secure access control |
| Encryption | cryptography | Sensitive data handling |
| Image Handling | Pillow | Face-capture support |
| Containerization | Docker, docker-compose | Deployment consistency |
| Hosting | Render | Live deployment |
| Version Control | Git, GitHub | Code management |
| Report Hosting | GitHub Wiki | Final documentation |

## Why This Tech Stack Was Chosen
This stack was chosen because it is practical, deployable, academically presentable, and strong enough to support both the product demo and the backend security logic.

## Navigation
- Previous: [[System-Architecture]]
- Next: [[Methodology]]
