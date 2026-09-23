import asyncio
import logging
from typing import Any, Dict, Optional
import httpx

from app.config import settings
from app.connectors.exceptions import (
    AuthFailedError,
    TokenExpiredError,
    RateLimitedError,
    ProviderUnavailableError,
    InvalidResponseError,
)

logger = logging.getLogger("wealthhub.connectors.groww")


class GrowwApiClient:
    """
    Production-grade HTTP client for the official Groww Trading API (v1).
    Handles authentication headers, timeouts, rate-limit backoff, response validation,
    and token redaction.
    """

    def __init__(
        self,
        access_token: str,
        base_url: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 2,
    ):
        if not access_token or not access_token.strip():
            raise AuthFailedError("Groww access token is required.")

        self._access_token = access_token.strip()
        self.base_url = (base_url or settings.GROWW_API_BASE_URL).rstrip("/")
        self.api_version = api_version or settings.GROWW_API_VERSION
        self.timeout = timeout or settings.GROWW_TIMEOUT_SECONDS
        self.max_retries = max_retries

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token}",
            "X-API-VERSION": self.api_version,
            "User-Agent": "WealthHub-Connector/1.0",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes an HTTP request to Groww API with bounded retries and sanitized error handling.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retries = 0

        while True:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self._headers,
                        params=params,
                    )

                # 1. Success response
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception as e:
                        logger.error("Groww API returned invalid JSON: %s", type(e).__name__)
                        raise InvalidResponseError("Malformed JSON response received from Groww API.")

                    if not isinstance(data, dict):
                        raise InvalidResponseError("Groww API returned unexpected response format.")

                    status_str = str(data.get("status", "")).upper()
                    if status_str == "FAILURE":
                        err_msg = data.get("message") or data.get("error") or "Unknown provider failure"
                        # Check for token expiration in message
                        if any(term in str(err_msg).lower() for term in ["token expired", "session expired", "unauthorized"]):
                            raise TokenExpiredError(f"Groww session expired: {err_msg}")
                        raise InvalidResponseError(f"Groww API reported failure: {err_msg}")

                    return data

                # 2. Authentication failure / expired token
                if response.status_code in (401, 403):
                    try:
                        err_body = response.json()
                        detail = str(err_body.get("message") or err_body.get("error") or "")
                    except Exception:
                        detail = ""

                    if "expired" in detail.lower():
                        raise TokenExpiredError("Groww access token has expired. Please re-authenticate.")
                    raise AuthFailedError(
                        "Groww API authentication failed. Please verify your access token."
                    )

                # 3. Rate limiting (429)
                if response.status_code == 429:
                    retry_after_hdr = response.headers.get("Retry-After")
                    retry_after = int(retry_after_hdr) if retry_after_hdr and retry_after_hdr.isdigit() else 2

                    if retries < self.max_retries:
                        retries += 1
                        backoff = min(retry_after, 5) * retries
                        logger.warning("Groww API rate-limited (429). Backing off for %ds (attempt %d)", backoff, retries)
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        raise RateLimitedError(
                            "Groww API rate limit reached. Please try again later.",
                            retry_after=retry_after,
                        )

                # 4. Transient server error (502, 503, 504)
                if response.status_code in (502, 503, 504):
                    if retries < self.max_retries:
                        retries += 1
                        backoff = 1.5 * retries
                        logger.warning("Groww server error (%d). Retrying in %.1fs...", response.status_code, backoff)
                        await asyncio.sleep(backoff)
                        continue
                    raise ProviderUnavailableError(f"Groww server error ({response.status_code}).")

                # 5. Other HTTP errors
                raise InvalidResponseError(f"Groww API returned HTTP status {response.status_code}.")

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException):
                if retries < self.max_retries:
                    retries += 1
                    logger.warning("Groww API timeout. Retrying (attempt %d)...", retries)
                    await asyncio.sleep(1.0 * retries)
                    continue
                raise ProviderUnavailableError("Groww API request timed out.")

            except (httpx.ConnectError, httpx.NetworkError):
                if retries < self.max_retries:
                    retries += 1
                    logger.warning("Groww network connection error. Retrying (attempt %d)...", retries)
                    await asyncio.sleep(1.0 * retries)
                    continue
                raise ProviderUnavailableError("Unable to establish connection to Groww API.")

    async def get_user_profile(self) -> Dict[str, Any]:
        """
        Retrieves user profile and account identification from GET /v1/user/detail.
        Expected payload contains: vendor_user_id, ucc, active_segments.
        """
        return await self._request("GET", "/v1/user/detail")

    async def get_holdings(self) -> Dict[str, Any]:
        """
        Retrieves equity Demat stock holdings from GET /v1/holdings/user.
        Expected payload contains list of holdings with isin, trading_symbol, quantity, average_price.
        """
        return await self._request("GET", "/v1/holdings/user")

    async def get_positions(self, segment: str = "CASH") -> Dict[str, Any]:
        """
        Retrieves open cash/FNO positions from GET /v1/positions/user.
        """
        return await self._request("GET", "/v1/positions/user", params={"segment": segment})

    async def get_margin_details(self) -> Dict[str, Any]:
        """
        Retrieves user margin and settled cash details from GET /v1/margins/detail/user.
        Expected payload contains: clear_cash, net_margin_used, collateral_available.
        """
        return await self._request("GET", "/v1/margins/detail/user")
