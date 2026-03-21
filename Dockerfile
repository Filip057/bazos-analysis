FROM python:3.10-slim

WORKDIR /app

# System dependencies for mysql-connector and spaCy
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Download spaCy Czech model (used by ML pipeline)
RUN python -m spacy download xx_ent_wiki_sm 2>/dev/null || true

EXPOSE 8000

# Production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "webapp.app:app"]
