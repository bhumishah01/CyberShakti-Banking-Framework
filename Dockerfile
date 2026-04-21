FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
# Install into an isolated venv for more predictable container builds.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY src /app/src
COPY data /app/data

# Render/Railway/Fly set PORT; default to 8000.
# In production we run a single web service that serves UI + API together:
# - UI at `/`
# - API at `/api/*`
EXPOSE 8000
CMD ["sh", "-c", "uvicorn src.deploy.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
