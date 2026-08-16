# app/core/context.py

import contextvars
from typing import Optional

# Request-scoped ContextVar storing the current correlation/request ID.
# Default value is None when accessed outside an active request context.
request_id_ctx_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> Optional[str]:
    """
    Retrieve the correlation/request ID for the current async task context.
    Returns None if called outside an active request lifecycle.
    """
    return request_id_ctx_var.get()


def set_request_id(req_id: str) -> contextvars.Token:
    """
    Sets the correlation/request ID in the current async context and returns
    the lifecycle token for reset operations.
    """
    return request_id_ctx_var.set(req_id)


def reset_request_id(token: contextvars.Token) -> None:
    """
    Resets the correlation/request ID context variable using the provided token.
    """
    request_id_ctx_var.reset(token)
