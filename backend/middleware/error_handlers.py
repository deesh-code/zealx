"""
Error handling middleware for ZealX Backend
Provides consistent error responses across all API endpoints
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from pydantic import ValidationError
import traceback
import logging
from typing import Dict, Any, Optional

from backend.models.api import ErrorDetail

# Configure logger
logger = logging.getLogger("zealx.error_handlers")

class ErrorCodes:
    """Error codes for ZealX API responses"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    BRAINX_ERROR = "BRAINX_ERROR"
    AUTOX_ERROR = "AUTOX_ERROR"
    API_ACCOUNT_ERROR = "API_ACCOUNT_ERROR"

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors from FastAPI"""
    errors = exc.errors()
    logger.warning(f"Validation error: {errors}")
    
    # Extract field information for better error messages
    field_errors = {}
    for error in errors:
        loc = ".".join([str(l) for l in error.get("loc", [])])
        if loc:
            field_errors[loc] = error.get("msg", "")
    
    error_detail = ErrorDetail(
        code=ErrorCodes.VALIDATION_ERROR,
        message="Request validation failed",
        details={"errors": field_errors},
        suggestion="Please check the request format and try again"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": error_detail.dict(),
            "response": None,
            "meta": {"request_path": request.url.path}
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
    
    error_code = ErrorCodes.HTTP_ERROR
    suggestion = "Please check your request and try again"
    
    # Map specific status codes to more specific error codes
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        error_code = ErrorCodes.RESOURCE_NOT_FOUND
        suggestion = "The requested resource does not exist"
    elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = ErrorCodes.AUTHENTICATION_ERROR
        suggestion = "Please provide valid authentication credentials"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        error_code = ErrorCodes.AUTHORIZATION_ERROR
        suggestion = "You don't have permission to access this resource"
    elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        error_code = ErrorCodes.RATE_LIMIT_EXCEEDED
        suggestion = "Please slow down your request rate"
    
    error_detail = ErrorDetail(
        code=error_code,
        message=str(exc.detail),
        suggestion=suggestion
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": error_detail.dict(),
            "response": None,
            "meta": {"request_path": request.url.path}
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    # Log the full traceback for debugging
    error_traceback = traceback.format_exc()
    logger.error(f"Unhandled exception: {str(exc)}\n{error_traceback}")
    
    # Determine if this is a specific known error type
    error_code = ErrorCodes.INTERNAL_SERVER_ERROR
    error_message = "An unexpected error occurred"
    
    if "BrainX" in str(exc.__class__):
        error_code = ErrorCodes.BRAINX_ERROR
        error_message = "Error in BrainX processing"
    elif "AutoX" in str(exc.__class__):
        error_code = ErrorCodes.AUTOX_ERROR
        error_message = "Error in AutoX processing"
    elif "API" in str(exc.__class__) and "Account" in str(exc.__class__):
        error_code = ErrorCodes.API_ACCOUNT_ERROR
        error_message = "Error with API account"
    
    # Don't expose internal error details in production
    error_detail = ErrorDetail(
        code=error_code,
        message=error_message,
        suggestion="Please try again later or contact support if the issue persists"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": error_detail.dict(),
            "response": None,
            "meta": {"request_path": request.url.path}
        }
    )

def setup_error_handlers(app):
    """Register all error handlers with the FastAPI app"""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
