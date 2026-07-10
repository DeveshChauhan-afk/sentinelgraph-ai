# app/core/exceptions.py

from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger

# ==========================================================
# Domain Exceptions
# ==========================================================


class SentinelGraphError(Exception):
    """Base exception for SentinelGraph AI."""

    pass


class IncidentNotFoundError(SentinelGraphError):
    """Raised when an incident cannot be found."""

    pass


class DuplicateCaseReferenceError(SentinelGraphError):
    """Raised when a duplicate case reference is detected."""

    pass


class BusinessValidationError(SentinelGraphError):
    """Raised when business validation fails."""

    pass


class InvalidIncidentStateError(SentinelGraphError):
    """Raised when an invalid incident state transition occurs."""

    pass


# ==========================================================
# Global Exception Handler
# ==========================================================


async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")

    logger.exception(f"RID: {request_id} | Unhandled Exception")

    if isinstance(exc, IncidentNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": "Incident Not Found",
                "message": str(exc),
                "request_id": request_id,
            },
        )

    if isinstance(exc, DuplicateCaseReferenceError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "error": "Duplicate Case Reference",
                "message": str(exc),
                "request_id": request_id,
            },
        )

    if isinstance(exc, BusinessValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": "Business Validation Error",
                "message": str(exc),
                "request_id": request_id,
            },
        )

    if isinstance(exc, InvalidIncidentStateError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": "Invalid Incident State",
                "message": str(exc),
                "request_id": request_id,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal Server Error",
            "message": "An unexpected error occurred.",
            "request_id": request_id,
        },
    )
