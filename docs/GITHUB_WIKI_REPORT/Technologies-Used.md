# Technologies Used

## Overview
RuralShield uses a practical full-stack web architecture chosen for three reasons:
- low setup overhead for rapid prototyping,
- clear explainability for academic reporting,
- enough modularity to resemble a real deployable system.

## Programming Languages
- **Python 3.11**
  Used for backend logic, UI routing, fraud scoring, synchronization logic, and deployment entrypoints.
- **HTML/CSS**
  Used for the UI templates, admin dashboards, customer portal layout, and visual styling.
- **JavaScript**
  Used selectively for interactivity such as language switching, voice interaction handling, and front-end actions.

## Frameworks and Libraries
- **FastAPI**
  Primary web framework for APIs and server-rendered route handling.
- **Jinja2**
  Templating engine used to render dynamic customer and admin pages.
- **SQLAlchemy**
  ORM used for structured database interaction in the server-side layer.
- **Pydantic**
  Used for validation and structured request/response handling.
- **python-jose**
  Used for JWT-based authentication.
- **passlib[bcrypt]**
  Used for password/PIN hashing and secure credential handling.
- **cryptography**
  Used for encryption and sensitive field protection.
- **Pillow**
  Used in the prototype for image handling in face-capture-related flows.

## Databases
- **SQLite**
  Used for local offline-first storage, transaction queueing, and demo persistence.
- **PostgreSQL**
  Used as the central server-side database in deployment.

## Tools and Platforms
- **Docker**
  Used to containerize the application for reproducible deployment.
- **docker-compose**
  Used in local development to run the application stack with database services.
- **Git & GitHub**
  Used for version control, structured commits, and collaborative documentation.
- **Render**
  Used to deploy the application live with a public URL.

## Frontend / UX Features Built on Top of This Stack
- multilingual language switching
- clickable dashboard cards
- voice command input and spoken feedback support
- graph-based analytics in SVG
- structured admin subpages and export flows

## Why This Tech Stack Was Chosen
This stack balances simplicity, deployability, and technical credibility. FastAPI and Jinja2 make it possible to build both API and UI in one coherent codebase. SQLite supports the offline-first model efficiently. PostgreSQL gives the deployed system a more production-style persistence layer. Docker and Render satisfy the live deployment and portability requirement.
