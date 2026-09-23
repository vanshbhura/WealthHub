from typing import Optional
from app.connectors.exceptions import (
    ConnectorError,
    AuthFailedError,
    TokenExpiredError,
    RateLimitedError,
    ProviderUnavailableError,
    InvalidResponseError,
)


class SetuClientError(ConnectorError):
    """Base error for Setu Account Aggregator operations."""
    code = "SETU_CLIENT_ERROR"
    safe_message = "Account Aggregator operation failed."


class SetuAuthError(AuthFailedError):
    """Setu client ID / secret / product instance ID authentication failed."""
    code = "SETU_AUTH_FAILED"
    safe_message = "Account Aggregator authentication failed. Please verify credentials."


class SetuTimeoutError(ProviderUnavailableError):
    """Setu sandbox API timed out."""
    code = "SETU_TIMEOUT"
    safe_message = "Account Aggregator service timed out. Please retry."


class SetuProviderUnavailableError(ProviderUnavailableError):
    """Setu sandbox is unreachable or returning 5xx."""
    code = "SETU_UNAVAILABLE"
    safe_message = "Account Aggregator service is temporarily unavailable."


class SetuInvalidResponseError(InvalidResponseError):
    """Setu sandbox returned malformed or unexpected JSON."""
    code = "SETU_INVALID_RESPONSE"
    safe_message = "Received an unexpected response from Account Aggregator service."


class SetuRateLimitError(RateLimitedError):
    """Setu API rate limit reached."""
    code = "SETU_RATE_LIMITED"
    safe_message = "Account Aggregator rate limit reached. Please try again shortly."


class SetuConsentRejectedError(ConnectorError):
    """Consent was rejected by the customer in AA flow."""
    code = "CONSENT_REJECTED"
    safe_message = "Consent was rejected or denied by user."


class SetuConsentExpiredError(TokenExpiredError):
    """Consent session or validity window has expired."""
    code = "CONSENT_EXPIRED"
    safe_message = "Account Aggregator consent has expired. New consent is required."


class SetuConsentRevokedError(ConnectorError):
    """Consent was revoked by user or provider."""
    code = "CONSENT_REVOKED"
    safe_message = "Account Aggregator consent was revoked."


class SetuConfigurationError(ConnectorError):
    """Setu configuration missing or invalid when real sandbox integration is requested."""
    code = "SETU_CONFIGURATION_ERROR"
    safe_message = "Account Aggregator configuration is incomplete or missing required credentials."

    def __init__(self, message: Optional[str] = None, missing_keys: Optional[list] = None):
        if missing_keys:
            joined = ", ".join(missing_keys)
            safe_msg = f"SETU_CONFIGURATION_ERROR: Missing required configuration: {joined}."
            super().__init__(safe_msg)
            self.safe_message = safe_msg
            self.missing_keys = missing_keys
        else:
            super().__init__(message or self.safe_message)
            self.safe_message = message or self.safe_message
            self.missing_keys = []

