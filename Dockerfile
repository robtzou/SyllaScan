# syntax=docker/dockerfile:1
FROM python:3.12-slim

# System deps (build tools are usually not needed for your stack)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Prevent Python from writing .pyc files & buffer logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create app directory & non-root user
WORKDIR /app
RUN useradd -m appuser
COPY requirements.txt /app/

# Install deps
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app
COPY . /app
RUN chown -R appuser:appuser /app
USER appuser

# Render provides $PORT; default to 8080 locally
ENV PORT=8080

# Start with gunicorn (change "app:app" if your entrypoint/module differs)
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 120"]
