import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger("wealthhub")


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPExceptions with standard error envelope."""
    detail = exc.detail
    code = "REQUEST_ERROR"
    message = str(detail)
    details = None

    if isinstance(detail, dict):
        code = detail.get("code", "REQUEST_ERROR")
        message = detail.get("message", "An error occurred")
        details = detail.get("details")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details
            }
        },
        headers=getattr(exc, "headers", None)
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle 422 input validation errors."""
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Validation error")
    loc = " -> ".join(str(l) for l in first_error.get("loc", []))

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"{loc}: {msg}" if loc else msg,
                "details": {"validation_errors": errors}
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all 500 handler preventing stack trace leaks."""
    logger.exception(f"Unhandled server error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later."
            }
        }
    )
