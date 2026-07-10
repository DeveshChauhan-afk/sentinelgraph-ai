# app/core/middleware.py

import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
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
            if response:
                response.headers["X-Request-ID"] = request_id
