# Stage 1: Build Vue frontend
FROM node:22-slim AS frontend-builder

# Install pnpm
RUN npm install -g pnpm

WORKDIR /app/frontend

# Copy dependency files
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./

# Build for production
RUN pnpm run build

# Stage 2: Python runtime with Flask + Gunicorn
FROM python:3.14-slim

WORKDIR /app

# Copy backend requirements
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies (gunicorn already in requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy Vue build from stage 1 to backend/static/
COPY --from=frontend-builder /app/frontend/dist ./backend/static/

# Environment variables (defaults, override at runtime via App Runner)
ENV FLASK_ENV=production \
    PORT=8080 \
    GH_REPO=trakrf/action-spec \
    SPECS_PATH=infra \
    WORKFLOW_BRANCH=main

# Expose port
EXPOSE 8080

# Health check using existing /health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run with Gunicorn (production WSGI server)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "--chdir", "backend", "app:app"]
