FROM python:3.10-slim

WORKDIR /app

# Install system dependencies including Node.js and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    procps \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy source code
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Install Python dependencies and the package
RUN pip install --no-cache-dir "mcp[cli]" && \
    pip install --no-cache-dir -e .

# Set environment variables

# Set environment variables (can be overridden at runtime)
ENV ODOO_URL="https://nivintech.odoo.com"
ENV ODOO_DB="nivintech"
ENV ODOO_USERNAME="shanmu.jul6@gmail.com"
ENV ODOO_PASSWORD="0d542e66eb9bf04fa273ff7417d3913c4f85fe65"
ENV ODOO_TIMEOUT="30"
ENV ODOO_VERIFY_SSL="1"
ENV DEBUG="0"

ENV PYTHONUNBUFFERED=1

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
ENTRYPOINT ["/app/start.sh"]

# # Run Supergateway with MCP server via uv
# ENTRYPOINT ["npx", "--yes", "supergateway", "--stdio", "uv run run_server.py"]
