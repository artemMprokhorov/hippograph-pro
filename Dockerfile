FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and nginx
# ngrok is optional — install only if NGROK_AUTHTOKEN is set at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    unzip \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Install ngrok (multi-architecture)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then \
        NGROK_ARCH="arm64"; \
    else \
        NGROK_ARCH="amd64"; \
    fi && \
    wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-${NGROK_ARCH}.tgz && \
    tar xzf ngrok-v3-stable-linux-${NGROK_ARCH}.tgz -C /usr/local/bin && \
    rm ngrok-v3-stable-linux-${NGROK_ARCH}.tgz

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy models for multilingual entity extraction
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download xx_ent_wiki_sm

# Copy source code and startup script
COPY src/ ./src/
COPY web/ /var/www/html/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Configure nginx
RUN rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/sites-available/hippograph
RUN ln -s /etc/nginx/sites-available/hippograph /etc/nginx/sites-enabled/

# Create data directory
RUN mkdir -p /app/data

# Environment variables
ENV DB_PATH=/app/data/memory.db
ENV FLASK_PORT=5000
ENV PYTHONUNBUFFERED=1

EXPOSE 5000 5002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

CMD ["/app/start.sh"]
