from typing import Optional


class ConnectorError(Exception):
    """Base exception for all financial connector operations."""
    code: str = "CONNECTOR_ERROR"
    safe_message: str = "An error occurred with the financial connector."

    def __init__(self, message: Optional[str] = None, code: Optional[str] = None):
        super().__init__(message or self.safe_message)
        if code:
            self.code = code
        self.safe_message = message or self.safe_message


class AuthFailedError(ConnectorError):
    """Authentication or authorization failed with provider."""
    code = "AUTH_FAILED"
    safe_message = "Provider authorization failed or expired. Please reconnect."


class TokenExpiredError(ConnectorError):
    """Provider access token has expired."""
    code = "TOKEN_EXPIRED"
    safe_message = "Session token has expired. Please re-authenticate."


class RateLimitedError(ConnectorError):
    """Provider API rate limit reached."""
    code = "RATE_LIMITED"
    safe_message = "Rate limit reached for provider. Please retry later."

    def __init__(self, message: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(message or self.safe_message)
        self.retry_after = retry_after


class ProviderUnavailableError(ConnectorError):
    """Provider service is temporarily down or unreachable."""
    code = "PROVIDER_UNAVAILABLE"
    safe_message = "Provider service is temporarily unavailable. Please try again later."


class InvalidResponseError(ConnectorError):
    """Provider returned malformed or unexpected data."""
    code = "INVALID_RESPONSE"
    safe_message = "Received unexpected data format from provider."


class DataValidationError(ConnectorError):
    """Normalized data failed validation rules."""
    code = "DATA_VALIDATION_FAILED"
    safe_message = "Financial records could not be validated."


class SyncFailedError(ConnectorError):
    """General sync execution failure."""
    code = "SYNC_FAILED"
    safe_message = "Unable to synchronize with the provider at this time."


class ConnectorNotImplementedError(ConnectorError):
    """Connector is planned or cataloged but not yet implemented."""
    code = "CONNECTOR_NOT_IMPLEMENTED"
    safe_message = "This integration is coming soon and has not been implemented yet."
