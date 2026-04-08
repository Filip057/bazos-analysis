FROM python:3.10-slim

# Prevent Python from writing pyc files / buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for mysql-connector and spaCy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Download spaCy multilingual model (used by ML pipeline)
RUN python -m spacy download xx_ent_wiki_sm 2>/dev/null || true

# Copy application code
COPY . .

# Create non-root user and hand over ownership
RUN useradd --create-home --shell /bin/bash bazos && \
    chown -R bazos:bazos /app
USER bazos

EXPOSE 8000

# Production WSGI server — binds to $PORT (Railway/Heroku) or 8000 locally.
# Shell form so the env var is expanded at runtime.
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --access-logfile - webapp.app:app
