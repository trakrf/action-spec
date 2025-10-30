"""
REST API module for Flask application.

Provides JSON endpoints for:
- Pod listing (GET /api/pods)
- Pod details (GET /api/pod/<customer>/<env>)
- Pod creation/update (POST /api/pod)
- Health check (GET /api/health already exists in main app)
"""

from flask import Blueprint

# Create API blueprint
api_blueprint = Blueprint("api", __name__, url_prefix="/api")

# Import routes to register with blueprint
from . import routes

__all__ = ["api_blueprint"]
