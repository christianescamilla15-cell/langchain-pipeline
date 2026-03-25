"""API Key authentication middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os


class APIKeyMiddleware(BaseHTTPMiddleware):
    EXCLUDED_PATHS = {"/api/health", "/docs", "/openapi.json", "/"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for excluded paths and static files
        if path in self.EXCLUDED_PATHS or not path.startswith("/api/") or path.startswith("/assets"):
            return await call_next(request)

        # Check for API key
        api_key = request.headers.get("X-API-Key", "")
        expected_key = os.environ.get("PIPELINE_API_KEY", "demo")

        if api_key != expected_key and expected_key != "demo":
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})

        return await call_next(request)
