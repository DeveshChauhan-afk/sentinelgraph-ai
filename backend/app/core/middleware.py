# app/core/middleware.py

import re
import time
import uuid
from typing import Optional
from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import reset_request_id, set_request_id
from app.core.metrics import http_request_duration_seconds, http_requests_total

# Whitelist pattern for valid incoming X-Request-ID (1-64 alphanumeric, hyphens, underscores)
REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
MAX_REQUEST_ID_LENGTH = 64


def validate_request_id(incoming_id: Optional[str]) -> Optional[str]:
    """
    Validates an incoming X-Request-ID header value.
    Returns the validated ID if valid, or None if missing or invalid.
    """
    if not incoming_id:
        return None

    if len(incoming_id) > MAX_REQUEST_ID_LENGTH:
        return None

    if not REQUEST_ID_REGEX.match(incoming_id):
        return None

    return incoming_id


def get_route_template(request: Request) -> str:
    """
    Extracts the normalized parameterized route path template from route metadata.
    Returns 'unmatched' for 404s, unmatched endpoints, or unrouted requests.
    """
    route = request.scope.get("route")
    if route and hasattr(route, "path_format"):
        return route.path_format
    if route and hasattr(route, "path"):
        return route.path
    return "unmatched"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_id = request.headers.get("X-Request-ID")
        valid_id = validate_request_id(incoming_id)
        request_id = valid_id if valid_id is not None else str(uuid.uuid4())

        request.state.request_id = request_id
        token = set_request_id(request_id)

        start_time = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            reset_request_id(token)
            process_time = time.perf_counter() - start_time
            status_code = response.status_code if response else 500
            client_ip = request.client.host if request.client else "unknown"
            logger.info(
                f"RID: {request_id} | "
                f"{request.method} {request.url.path} | "
                f"Status: {status_code} | "
                f"Duration: {process_time * 1000:.2f} ms | "
                f"Client: {client_ip}"
            )
            route_template = get_route_template(request)
            http_requests_total.labels(
                method=request.method,
                path=route_template,
                status_code=str(status_code),
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method,
                path=route_template,
            ).observe(process_time)
            if response:
                response.headers["X-Request-ID"] = request_id
