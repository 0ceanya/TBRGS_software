"""Global error handling middleware for TBRGS API."""
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a safe JSON error envelope.

    The full exception is logged server-side; only a generic message is
    returned to the client to avoid leaking internal implementation details.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "detail": "An unexpected error occurred."},
    )
