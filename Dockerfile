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

# Pre-download GLiNER model weights (avoids cold start delay)
# GLiNER v2.1+ = Apache 2.0. Never use v1/base = CC BY-NC 4.0.
ARG GLINER_MODEL=urchade/gliner_multi-v2.1
RUN python -c "from gliner import GLiNER; GLiNER.from_pretrained('${GLINER_MODEL}')" \
    || echo "⚠️ GLiNER pre-download failed, will download at runtime"

# Pre-download GLiNER2 model weights (Deep Sleep relation extraction)
# Apache 2.0 license verified.
ARG GLINER2_MODEL=fastino/gliner2-large-v1
RUN python -c "from gliner2 import GLiNER2; GLiNER2.from_pretrained('${GLINER2_MODEL}')" \
    || echo "⚠️ GLiNER2 pre-download failed, will download at runtime"

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
