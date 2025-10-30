FROM python:3.14-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY requirements.txt .

# Create venv and install dependencies with uv
RUN uv venv && \
    uv pip install -r requirements.txt

# Copy application code
COPY . .

# Expose Flask port
EXPOSE 5000

# Health check using /health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Run Flask with uv
CMD ["uv", "run", "flask", "--app", "app", "run", "--host", "0.0.0.0"]
