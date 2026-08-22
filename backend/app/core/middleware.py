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


def iter_declared_routes(routes, prefix: str = ""):
    """
    Recursively yields (prefix, route) pairs from FastAPI/Starlette route collections,
    loosely handling nested routers/IncludedRouters without importing private classes.
    """
    for route in routes:
        original_router = getattr(route, "original_router", None) or getattr(route, "router", None)
        if original_router and hasattr(original_router, "routes"):
            include_ctx = getattr(route, "include_context", None)
            sub_prefix = getattr(include_ctx, "prefix", "") if include_ctx else getattr(route, "prefix", "")
            combined_prefix = f"{prefix}{sub_prefix}" if sub_prefix else prefix
            yield from iter_declared_routes(original_router.routes, combined_prefix)
        elif hasattr(route, "routes"):
            sub_prefix = getattr(route, "prefix", "")
            combined_prefix = f"{prefix}{sub_prefix}" if sub_prefix else prefix
            yield from iter_declared_routes(route.routes, combined_prefix)
        else:
            yield prefix, route


def resolve_declared_route(request: Request) -> Optional[str]:
    """
    Matches the request path against declared FastAPI application route templates.
    Used for 405 Method Not Allowed or empty leaf route templates without exposing raw paths.
    """
    app = getattr(request, "app", None)
    if not app or not hasattr(app, "routes"):
        return None

    url_path = request.scope.get("path")
    if not url_path and request.url:
        url_path = request.url.path

    if not url_path:
        return None

    for prefix, route in iter_declared_routes(app.routes):
        leaf_path = getattr(route, "path_format", None) or getattr(route, "path", None) or ""
        if not leaf_path:
            if url_path == prefix:
                return prefix
        else:
            path_regex = getattr(route, "path_regex", None)
            if path_regex:
                if prefix:
                    child_pattern = path_regex.pattern.lstrip("^")
                    full_pattern = f"^{re.escape(prefix)}{child_pattern}"
                    if re.match(full_pattern, url_path):
                        return leaf_path
                else:
                    if path_regex.match(url_path):
                        return leaf_path

    return None


def get_route_template(request: Request) -> str:
    """
    Extracts the normalized parameterized route path template from route metadata.
    Returns 'unmatched' for 404s, unmatched endpoints, or unrouted requests.
    """
    route = request.scope.get("route")
    if route:
        template = getattr(route, "path_format", None) or getattr(route, "path", None)
        if template:
            return template

    declared_template = resolve_declared_route(request)
    if declared_template:
        return declared_template

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
