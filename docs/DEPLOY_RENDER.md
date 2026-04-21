# Render Deployment (Docker, Single Live URL)

This project can be deployed on **Render** as a single Docker web service that serves:
- **UI** at `/`
- **Server API** at `/api/*`

Render health check:
- `/health`

## Preconditions

- Code pushed to GitHub `main`
- Render account connected to GitHub

## Required Environment Variables (Render)

Set these in Render (Dashboard -> Service -> Environment):

- `DATABASE_URL`
  - Use Render **Internal Database URL**
  - The app will auto-normalize `postgres://...` or `postgresql://...` to `postgresql+psycopg://...`
- `JWT_SECRET`
  - Use a long random string
- `FIELD_ENC_KEY`
  - Used to encrypt sensitive fields
  - Must be at least 32 chars

These are already set via `render.yaml`:
- `PORT=8000`
- `RURALSHIELD_COMBINED=1`
- `RURALSHIELD_API_MOUNT_PATH=/api`

## Render Setup (Step-by-step)

1. Go to Render Dashboard
2. New -> **Blueprint**
3. Select this GitHub repo
4. Render detects `render.yaml`
5. Fill the required env vars (DATABASE_URL, JWT_SECRET, FIELD_ENC_KEY)
6. Deploy

After deploy, your live URL will serve:
- UI: `https://<your-service>.onrender.com/`
- API health: `https://<your-service>.onrender.com/api/health`

## Local Validation Checklist

- [ ] `docker build .` succeeds
- [ ] `docker run -p 8000:8000 ...` serves UI at `http://localhost:8000/`
- [ ] `http://localhost:8000/health` returns ok
- [ ] `http://localhost:8000/api/health` returns ok

## Notes

- Local offline-first SQLite is still used by the UI demo.
- In production, central data is stored in Postgres via `DATABASE_URL`.
