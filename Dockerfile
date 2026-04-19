FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY data /app/data

# Render/Railway/Fly set PORT; default to 8502 for local Docker runs.
EXPOSE 8502
CMD ["sh", "-c", "uvicorn src.ui.app:app --host 0.0.0.0 --port ${PORT:-8502}"]

