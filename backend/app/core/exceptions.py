# app/core/exceptions.py

from fastapi import Request, status
from fastapi.responses import JSONResponse
from loguru import logger

async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log the full stack trace for debugging
    logger.exception(
    f"RID: {request_id} | Unhandled Exception"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please contact the administrator.",
            "request_id": request_id,
        },
    )