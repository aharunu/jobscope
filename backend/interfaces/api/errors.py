"""API exception handlers and error response formatters."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.application.common.exceptions import JobScopeError

logger = logging.getLogger(__name__)


async def jobscope_error_handler(
    request: Request,
    exc: JobScopeError,
) -> JSONResponse:
    """Handle known application exceptions and format a standardized response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected server exceptions securely without leaking internal state."""
    logger.exception(
        "Unhandled exception occurred processing %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom application error handlers on the FastAPI instance."""
    app.add_exception_handler(JobScopeError, jobscope_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_exception_handler(500, unhandled_exception_handler)
