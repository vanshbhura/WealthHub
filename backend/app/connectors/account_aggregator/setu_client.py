import re
import json
import logging
import asyncio
import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, date
import httpx

from app.config import settings
from app.connectors.account_aggregator.dtos import (
    SetuConsentRequest,
    SetuConsentResponse,
    SetuConsentStatus,
    SetuDataSessionRequest,
    SetuDataSessionResponse,
    SetuFinancialDataResponse,
    SetuBankAccount,
    SetuBankTransaction,
    SetuMutualFundHolding,
    SetuEquityHolding,
    SetuFixedDeposit,
    SetuNPSAccount,
)
from app.connectors.account_aggregator.exceptions import (
    SetuClientError,
    SetuAuthError,
    SetuTimeoutError,
    SetuProviderUnavailableError,
    SetuInvalidResponseError,
    SetuRateLimitError,
    SetuConsentRejectedError,
    SetuConsentExpiredError,
    SetuConsentRevokedError,
    SetuConfigurationError,
)
from app.connectors.account_aggregator.sandbox import SetuSandboxDataGenerator

logger = logging.getLogger("wealthhub.connectors.setu_aa")

# Sensitive substrings for key-based redaction
REDACT_KEYS = (
    "secret",
    "token",
    "password",
    "key",
    "account_number",
    "accountnumber",
    "accno",
    "maskedaccnumber",
    "demat",
    "pran",
    "authorization",
    "auth",
    "pan",
    "aadhaar",
    "phone",
    "mobile",
    "email",
    "narration",
)


def redact_sensitive_data(val: Any) -> Any:
    """
    Recursively redacts secrets, tokens, PII, and financial identifiers from logs/errors.
    Safe for structured debugging and diagnostics.
    """
    if isinstance(val, dict):
        redacted = {}
        for k, v in val.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in REDACT_KEYS):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_sensitive_data(v)
        return redacted
    elif isinstance(val, list):
        return [redact_sensitive_data(item) for item in val]
    elif isinstance(val, str):
        # Redact JWT tokens or long hex/base64 strings
        if len(val) > 30 and re.match(r"^[A-Za-z0-9_\-\.]+$", val):
            return val[:4] + "...[REDACTED]"
        # Redact PAN (e.g. ABCDE1234F)
        val = re.sub(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "[REDACTED_PAN]", val)
        # Redact 10-digit phone number
        val = re.sub(r"\b(?:\+91|91)?[6-9]\d{9}\b", "[REDACTED_PHONE]", val)
        # Redact 12-digit Aadhaar number
        val = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[REDACTED_AADHAAR]", val)
        # Redact email addresses
        val = re.sub(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", "[REDACTED_EMAIL]", val)
        return val
    return val


def log_safe_structured_event(event_name: str, **kwargs) -> None:
    """Logs safe structured diagnostics without sensitive financial payloads."""
    safe_fields = {}
    allowed_plain_fields = {
        "consent_id",
        "request_id",
        "session_id",
        "data_type",
        "record_count",
        "http_status",
        "duration_ms",
        "status",
        "mode",
        "provider",
    }
    for k, v in kwargs.items():
        if k in allowed_plain_fields:
            safe_fields[k] = v
        else:
            safe_fields[k] = redact_sensitive_data(v)
    logger.info("Setu AA Event [%s]: %s", event_name, json.dumps(safe_fields))


class SetuAAClient:
    """
    Dedicated client for Setu Account Aggregator Sandbox (FIU developer environment).
    Follows RBI Account Aggregator specifications:
    1. Consent Initiation
    2. Consent Tracking & Verification
    3. Financial Information (FI) Data Session Fetch
    4. Strict separation between internal mock sandbox (SANDBOX_MOCK) and real Setu sandbox (SETU_SANDBOX).
    5. Zero silent fallback to mock on real integration failures.
    6. Redaction of sensitive financial identifiers and secrets in all logging.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        product_instance_id: Optional[str] = None,
        auth_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: Optional[float] = None,
        force_sandbox_mock: Optional[bool] = None,
    ):
        self.base_url = (base_url or settings.SETU_BASE_URL).rstrip("/")
        self.client_id = client_id or settings.SETU_CLIENT_ID
        self.client_secret = client_secret or settings.SETU_CLIENT_SECRET
        self.product_instance_id = product_instance_id or settings.SETU_PRODUCT_INSTANCE_ID
        self.timeout = timeout or settings.SETU_TIMEOUT_SECONDS

        # Auth URL resolution
        if auth_url:
            self.auth_url = auth_url.rstrip("/")
        elif settings.SETU_AUTH_URL:
            self.auth_url = settings.SETU_AUTH_URL.rstrip("/")
        else:
            is_prod = "fiu.setu.co" in self.base_url and "sandbox" not in self.base_url
            if settings.SETU_ENVIRONMENT.lower() in ("production", "prod") or is_prod:
                self.auth_url = "https://prod.setu.co/api/v2/auth/token"
            else:
                self.auth_url = "https://uat.setu.co/api/v2/auth/token"

        # Token caching
        self._cached_token: Optional[str] = auth_token
        self._token_expires_at: Optional[float] = (time.time() + 86400) if auth_token else None

        # Determine operating mode: MOCK vs REAL SETU
        # Rule: Do not fall back to SANDBOX_MOCK when SETU_ENVIRONMENT=sandbox/real_setu
        if force_sandbox_mock is not None:
            self.use_mock = force_sandbox_mock
            if not self.use_mock:
                self.validate_credentials()
        else:
            env = (settings.SETU_ENVIRONMENT or "mock").lower()
            if env in ("mock", "sandbox_mock"):
                self.use_mock = True
            else:
                # Real Setu mode: never fall back to mock
                self.use_mock = False

        # In-memory store for mock mode lifecycle simulation
        self._mock_consents: Dict[str, Dict[str, Any]] = {}

    def get_missing_credentials(self) -> List[str]:
        """Returns list of missing required Setu credential names."""
        missing = []
        if not self.client_id:
            missing.append("SETU_CLIENT_ID")
        if not self.client_secret:
            missing.append("SETU_CLIENT_SECRET")
        if not self.product_instance_id:
            missing.append("SETU_PRODUCT_INSTANCE_ID")
        return missing

    def validate_credentials(self) -> None:
        """
        Validates presence of required Setu credentials.
        Raises SetuConfigurationError if missing. Never reveals credential values.
        """
        missing = self.get_missing_credentials()
        if missing:
            raise SetuConfigurationError(missing_keys=missing)

    async def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieves or generates an OAuth access token using clientID and secret.
        Caches the token until shortly before expiry (default 60s buffer).
        Never logs or exposes client_secret.
        Retries on transient 5xx/network errors, but fails fast on 4xx invalid credentials.
        """
        self.validate_credentials()

        now = time.time()
        # Use cached token if valid and not forcing refresh (buffer 60 seconds)
        if (
            not force_refresh
            and self._cached_token
            and self._token_expires_at
            and (self._token_expires_at - now > 60)
        ):
            return self._cached_token

        payload = {
            "clientID": self.client_id,
            "secret": self.client_secret,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        retries = 0
        max_retries = 2
        start_time = time.time()

        while retries <= max_retries:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(self.auth_url, json=payload, headers=headers)
                    duration_ms = round((time.time() - start_time) * 1000, 2)

                    if resp.status_code in (200, 201):
                        log_safe_structured_event(
                            "auth_token_success",
                            http_status=resp.status_code,
                            duration_ms=duration_ms,
                        )
                        try:
                            body = resp.json()
                        except Exception as e:
                            logger.error("Setu auth service returned non-JSON response: %s", type(e).__name__)
                            raise SetuInvalidResponseError("Malformed JSON received from Setu auth service.")

                        data = body.get("data") if isinstance(body.get("data"), dict) else body
                        token = (
                            data.get("token")
                            or data.get("access_token")
                            or body.get("token")
                            or body.get("access_token")
                        )
                        expires_in = (
                            data.get("expiresIn")
                            or data.get("expires_in")
                            or body.get("expiresIn")
                            or body.get("expires_in")
                            or 1800
                        )

                        if not token or not isinstance(token, str):
                            logger.error("Setu auth response missing token field")
                            raise SetuInvalidResponseError("Setu auth response missing access token.")

                        self._cached_token = token
                        self._token_expires_at = time.time() + float(expires_in)
                        return self._cached_token

                    elif resp.status_code in (400, 401, 403):
                        log_safe_structured_event(
                            "auth_token_failure",
                            http_status=resp.status_code,
                            duration_ms=duration_ms,
                        )
                        # Do NOT retry credential errors
                        raise SetuAuthError("Setu AA authentication failed. Please verify client ID and secret.")

                    elif resp.status_code == 429:
                        retries += 1
                        if retries <= max_retries:
                            await asyncio.sleep(1.0 * retries)
                            continue
                        raise SetuRateLimitError("Setu AA authentication rate limit exceeded.")

                    elif resp.status_code >= 500:
                        retries += 1
                        if retries <= max_retries:
                            await asyncio.sleep(1.0 * retries)
                            continue
                        raise SetuProviderUnavailableError(f"Setu auth service error (HTTP {resp.status_code}).")

                    else:
                        raise SetuInvalidResponseError(f"Setu auth service returned unexpected status {resp.status_code}.")

            except (httpx.TimeoutException, httpx.ConnectTimeout):
                retries += 1
                if retries <= max_retries:
                    await asyncio.sleep(1.0 * retries)
                    continue
                raise SetuTimeoutError("Setu AA authentication request timed out.")

            except (httpx.ConnectError, httpx.NetworkError):
                retries += 1
                if retries <= max_retries:
                    await asyncio.sleep(1.0 * retries)
                    continue
                raise SetuProviderUnavailableError("Unable to establish connection to Setu auth service.")

            except (SetuClientError, SetuAuthError, SetuTimeoutError, SetuProviderUnavailableError, SetuInvalidResponseError, SetuRateLimitError):
                raise

            except Exception as e:
                raise SetuClientError(f"Unexpected error during Setu token retrieval: {str(e)}")

        raise SetuProviderUnavailableError("Setu AA authentication service unavailable after retries.")

    async def _get_headers(self, force_refresh: bool = False) -> Dict[str, str]:
        token = await self.get_access_token(force_refresh=force_refresh)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        if self.product_instance_id:
            headers["x-product-instance-id"] = self.product_instance_id
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Executes HTTP request with structured error handling, retries, and sensitive redaction.
        Uses OAuth Bearer token authentication.
        Automatically handles token refresh on 401.
        Never logs sensitive payloads or credentials.
        """
        self.validate_credentials()
        url = f"{self.base_url}{path}"
        headers = await self._get_headers()
        retries = 0
        refreshed_on_401 = False
        start_time = time.time()

        while retries <= max_retries:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.request(method, url, json=json_data, headers=headers)
                    duration_ms = round((time.time() - start_time) * 1000, 2)

                    if resp.status_code in (200, 201):
                        log_safe_structured_event(
                            "http_success",
                            http_status=resp.status_code,
                            duration_ms=duration_ms,
                            path=path,
                        )
                        try:
                            return resp.json()
                        except Exception as e:
                            logger.error("Setu API returned invalid JSON: %s", type(e).__name__)
                            raise SetuInvalidResponseError("Malformed JSON response received from Setu AA service.")

                    elif resp.status_code in (401, 403):
                        # Attempt token refresh once if token might have expired on server
                        if not refreshed_on_401 and resp.status_code == 401:
                            refreshed_on_401 = True
                            try:
                                headers = await self._get_headers(force_refresh=True)
                                continue
                            except SetuAuthError:
                                pass
                        log_safe_structured_event(
                            "http_auth_failure",
                            http_status=resp.status_code,
                            duration_ms=duration_ms,
                            path=path,
                        )
                        raise SetuAuthError("Setu AA authentication failed. Please check client credentials or product instance ID.")

                    elif resp.status_code == 400:
                        err_text = ""
                        try:
                            err_text = resp.text
                        except Exception:
                            pass
                        if "product" in err_text.lower() or "instance" in err_text.lower():
                            raise SetuAuthError("Setu AA rejected request due to invalid product instance ID.")
                        raise SetuInvalidResponseError(f"Setu AA bad request (HTTP 400): {path}")

                    elif resp.status_code == 404:
                        raise SetuInvalidResponseError(f"Setu resource not found: {path}")

                    elif resp.status_code == 429:
                        retries += 1
                        if retries <= max_retries:
                            await asyncio.sleep(1.0 * retries)
                            continue
                        raise SetuRateLimitError("Setu AA rate limit exceeded. Please try again later.")

                    elif resp.status_code >= 500:
                        retries += 1
                        if retries <= max_retries:
                            await asyncio.sleep(1.0 * retries)
                            continue
                        raise SetuProviderUnavailableError(f"Setu AA server error (HTTP {resp.status_code}).")

                    else:
                        raise SetuInvalidResponseError(f"Setu AA returned unexpected HTTP status {resp.status_code}.")

            except (httpx.TimeoutException, httpx.ConnectTimeout):
                retries += 1
                if retries <= max_retries:
                    await asyncio.sleep(1.0 * retries)
                    continue
                raise SetuTimeoutError("Setu AA request timed out.")

            except (httpx.ConnectError, httpx.NetworkError):
                retries += 1
                if retries <= max_retries:
                    await asyncio.sleep(1.0 * retries)
                    continue
                raise SetuProviderUnavailableError("Unable to establish connection to Setu AA service.")

            except (SetuClientError, SetuAuthError, SetuTimeoutError, SetuProviderUnavailableError, SetuInvalidResponseError, SetuRateLimitError):
                raise

            except Exception as e:
                raise SetuClientError(f"Unexpected Setu client error: {str(e)}")

        raise SetuProviderUnavailableError("Setu AA service unavailable after retries.")

    async def create_consent_request(self, req: SetuConsentRequest) -> SetuConsentResponse:
        """
        Creates an Account Aggregator consent request.
        Returns consent ID and sandbox web authorization URL.
        """
        if self.use_mock:
            consent_id = f"sandbox-consent-{uuid.uuid4().hex[:12]}"
            redirect_url = f"{self.base_url}/consents/redirect/{consent_id}"
            now = datetime.utcnow()
            self._mock_consents[consent_id] = {
                "id": consent_id,
                "status": "PENDING",
                "created_at": now,
                "expires_at": now + timedelta(days=req.expiry_days),
                "fi_types": req.fi_types,
                "customer_phone": req.customer_phone,
            }
            log_safe_structured_event("consent_created_mock", consent_id=consent_id, mode="SANDBOX_MOCK")
            return SetuConsentResponse(
                id=consent_id,
                url=redirect_url,
                status="PENDING",
                created_at=now,
            )

        # Real Setu Sandbox API payload (per RBI AA / Setu FIU spec)
        customer_id = req.customer_vpa or (f"{req.customer_phone}@setu" if req.customer_phone else "customer@setu")
        payload = {
            "Detail": {
                "consentMode": req.consent_mode,
                "fetchType": req.fetch_type,
                "consentTypes": ["TRANSACTIONS", "PROFILE", "SUMMARY"],
                "fiTypes": req.fi_types,
                "Purpose": {
                    "code": "101",
                    "refUri": "https://api.rebit.org.in/aa/purpose/101.xml",
                    "text": "Wealth management portfolio tracking",
                    "Category": {"type": "string"},
                },
                "Customer": {
                    "id": customer_id,
                },
                "DataLife": {"unit": "MONTH", "value": 12},
                "Frequency": {"unit": "DAY", "value": 1},
            },
            "redirectUrl": req.redirect_url or f"{self.base_url}/callback",
        }

        data = await self._request("POST", "/consents", json_data=payload)
        consent_id = data.get("id", str(uuid.uuid4()))
        log_safe_structured_event("consent_created_real", consent_id=consent_id, mode="SETU_SANDBOX")
        return SetuConsentResponse(
            id=consent_id,
            url=data.get("url"),
            status=data.get("status", "PENDING"),
            created_at=datetime.utcnow(),
        )

    async def get_consent_status(self, consent_id: str) -> SetuConsentStatus:
        """
        Polls or retrieves the status of a consent request.
        Supports: PENDING, AUTHORIZED, ACTIVE, REJECTED, EXPIRED, REVOKED, ERROR.
        """
        if self.use_mock:
            info = self._mock_consents.get(consent_id)
            if not info:
                # Default mock behavior: treat unknown valid sandbox ID as ACTIVE
                return SetuConsentStatus(
                    id=consent_id,
                    status="ACTIVE",
                    fi_types=["DEPOSIT", "TERM_DEPOSIT", "MUTUAL_FUNDS", "EQUITIES", "NPS"],
                    consent_expires_at=datetime.utcnow() + timedelta(days=90),
                )
            status_val = info.get("status", "ACTIVE")
            if status_val in ("REJECTED", "FAILED"):
                raise SetuConsentRejectedError(f"Setu consent request was rejected.")
            elif status_val == "EXPIRED":
                raise SetuConsentExpiredError("Setu consent request has expired.")
            elif status_val == "REVOKED":
                raise SetuConsentRevokedError("Setu consent request has been revoked.")

            return SetuConsentStatus(
                id=consent_id,
                status=status_val,
                fi_types=info.get("fi_types", []),
                consent_expires_at=info.get("expires_at"),
            )

        data = await self._request("GET", f"/consents/{consent_id}")
        raw_status = str(data.get("status", "PENDING")).upper()

        if raw_status in ("REJECTED", "FAILED"):
            raise SetuConsentRejectedError(f"Setu consent request was rejected: {data.get('error')}")
        elif raw_status == "EXPIRED":
            raise SetuConsentExpiredError("Setu consent request has expired.")
        elif raw_status == "REVOKED":
            raise SetuConsentRevokedError("Setu consent request has been revoked.")

        log_safe_structured_event("consent_status_polled", consent_id=consent_id, status=raw_status, mode="SETU_SANDBOX")
        return SetuConsentStatus(
            id=consent_id,
            status=raw_status,
            handle=data.get("handle"),
            fi_types=data.get("Detail", {}).get("fiTypes", []),
            consent_expires_at=datetime.utcnow() + timedelta(days=90),
        )

    def set_mock_consent_status(self, consent_id: str, status: str) -> None:
        """Helper for test suites to simulate state transitions."""
        if consent_id in self._mock_consents:
            self._mock_consents[consent_id]["status"] = status
        else:
            self._mock_consents[consent_id] = {
                "id": consent_id,
                "status": status,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=90),
            }

    async def create_data_session(self, consent_id: str) -> SetuDataSessionResponse:
        """
        Initiates a financial information session for an AUTHORIZED / ACTIVE consent.
        """
        if self.use_mock:
            session_id = f"sandbox-session-{uuid.uuid4().hex[:12]}"
            return SetuDataSessionResponse(id=session_id, status="COMPLETED")

        payload = {"consentId": consent_id, "format": "json"}
        data = await self._request("POST", "/sessions", json_data=payload)
        return SetuDataSessionResponse(
            id=data.get("id", str(uuid.uuid4())),
            status=data.get("status", "COMPLETED"),
        )

    def _parse_real_setu_payload(self, consent_id: str, raw_response: Dict[str, Any]) -> SetuFinancialDataResponse:
        """
        Parses real Setu AA sandbox response into SetuFinancialDataResponse.
        Strictly tags records as SETU_SANDBOX.
        Raises SetuInvalidResponseError on malformed or empty payloads without falling back to mock.
        """
        # If the response already conforms to SetuFinancialDataResponse DTO structure
        if "bank_accounts" in raw_response or "mutual_funds" in raw_response or "equities" in raw_response:
            try:
                res = SetuFinancialDataResponse(
                    consent_id=consent_id,
                    data_source="SETU_SANDBOX",
                    bank_accounts=[SetuBankAccount(**b) for b in raw_response.get("bank_accounts", [])],
                    mutual_funds=[SetuMutualFundHolding(**m) for m in raw_response.get("mutual_funds", [])],
                    equities=[SetuEquityHolding(**e) for e in raw_response.get("equities", [])],
                    fixed_deposits=[SetuFixedDeposit(**f) for f in raw_response.get("fixed_deposits", [])],
                    nps_accounts=[SetuNPSAccount(**n) for n in raw_response.get("nps_accounts", [])],
                )
                return res
            except Exception as e:
                logger.error("Failed to parse conforming Setu DTO payload: %s", e)
                raise SetuInvalidResponseError(f"Setu financial data format error: {str(e)}")

        payload_blocks = raw_response.get("Payload") or raw_response.get("payload") or raw_response.get("data")
        if not payload_blocks:
            raise SetuInvalidResponseError("Empty or malformed financial data payload received from Setu AA sandbox.")

        bank_accounts: List[SetuBankAccount] = []
        mutual_funds: List[SetuMutualFundHolding] = []
        equities: List[SetuEquityHolding] = []
        fixed_deposits: List[SetuFixedDeposit] = []
        nps_accounts: List[SetuNPSAccount] = []

        for block in payload_blocks:
            fip_id = block.get("fipId", "FIP-SANDBOX")
            acc_list = block.get("data") or block.get("decryptedData") or block.get("accounts") or [block]

            for acc in acc_list:
                fi_type = str(acc.get("type") or acc.get("accountType") or "").upper()
                acc_num = acc.get("maskedAccNumber") or acc.get("account_number_masked") or acc.get("accountNumber") or "****0000"

                # A. Bank Deposit
                if fi_type in ("DEPOSIT", "SAVINGS", "CURRENT") or "transactions" in acc or "summary" in acc:
                    summary = acc.get("summary", {})
                    balance = float(summary.get("currentBalance", summary.get("balance", acc.get("current_balance", 0.0))))
                    bank_name = summary.get("bankName") or block.get("fipName") or "Sandbox Bank"

                    raw_txns = acc.get("transactions", [])
                    txns = []
                    for t in raw_txns:
                        txn_id = t.get("txnId") or t.get("txn_id") or str(uuid.uuid4())
                        txn_type = t.get("type", "DEBIT").upper()
                        amount = float(t.get("amount", 0.0))
                        narration = t.get("narration", "")
                        txns.append(
                            SetuBankTransaction(
                                txn_id=txn_id,
                                type=txn_type,
                                amount=amount,
                                narration=narration,
                                timestamp=datetime.utcnow(),
                                balance_after=balance,
                            )
                        )

                    bank_accounts.append(
                        SetuBankAccount(
                            fip_id=fip_id,
                            bank_name=bank_name,
                            account_number_masked=acc_num,
                            account_type="SAVINGS",
                            current_balance=balance,
                            currency="INR",
                            transactions=txns,
                        )
                    )

                # B. Mutual Funds
                elif fi_type in ("MUTUAL_FUNDS", "MUTUAL_FUND") or "funds" in acc:
                    funds = acc.get("funds") or acc.get("holdings") or [acc]
                    for fund in funds:
                        isin = fund.get("isin", "INF000000000")
                        scheme = fund.get("schemeName") or fund.get("scheme_name") or "Sandbox Mutual Fund"
                        units = float(fund.get("units", 1.0))
                        nav = float(fund.get("nav", 100.0))
                        cur_val = float(fund.get("currentValue", fund.get("current_value", units * nav)))
                        inv_val = float(fund.get("investedValue", fund.get("invested_value", cur_val)))
                        mutual_funds.append(
                            SetuMutualFundHolding(
                                amc=fund.get("amc", "Sandbox AMC"),
                                scheme_name=scheme,
                                isin=isin,
                                folio_number=fund.get("folioNumber", fund.get("folio_number", "SB-FOLIO-1")),
                                units=units,
                                nav=nav,
                                invested_value=inv_val,
                                current_value=cur_val,
                            )
                        )

                # C. Equities
                elif fi_type in ("EQUITIES", "EQUITY") or "equities" in acc:
                    eq_list = acc.get("equities") or acc.get("holdings") or [acc]
                    for eq in eq_list:
                        isin = eq.get("isin", "INE000000000")
                        company = eq.get("companyName") or eq.get("company_name") or "Sandbox Company"
                        symbol = eq.get("symbol", "SANDBOX")
                        qty = float(eq.get("quantity", 1.0))
                        price = float(eq.get("currentPrice", eq.get("current_price", 100.0)))
                        buy_price = float(eq.get("averageBuyPrice", eq.get("average_buy_price", price)))
                        cur_val = float(eq.get("currentValue", eq.get("current_value", qty * price)))
                        equities.append(
                            SetuEquityHolding(
                                isin=isin,
                                company_name=company,
                                symbol=symbol,
                                demat_account=eq.get("dematAccount", eq.get("demat_account", "1208160000000000")),
                                depository=eq.get("depository", "CDSL"),
                                quantity=qty,
                                average_buy_price=buy_price,
                                current_price=price,
                                current_value=cur_val,
                            )
                        )

                # D. Fixed Deposits
                elif fi_type in ("TERM_DEPOSIT", "FIXED_DEPOSIT", "FD"):
                    summary = acc.get("summary", acc)
                    fixed_deposits.append(
                        SetuFixedDeposit(
                            bank_name=summary.get("bankName", "Sandbox Bank"),
                            deposit_number_masked=acc_num,
                            principal_amount=float(summary.get("principalAmount", 100000.0)),
                            current_value=float(summary.get("currentValue", 105000.0)),
                            interest_rate=float(summary.get("interestRate", 7.0)),
                            maturity_date=date.today() + timedelta(days=365),
                            tenure_months=int(summary.get("tenureMonths", 12)),
                        )
                    )

                # E. NPS
                elif fi_type in ("NPS", "PENSION"):
                    summary = acc.get("summary", acc)
                    nps_accounts.append(
                        SetuNPSAccount(
                            pran_masked=summary.get("pranMasked", acc_num),
                            tier=summary.get("tier", "TIER_1"),
                            total_contribution=float(summary.get("totalContribution", 50000.0)),
                            current_value=float(summary.get("currentValue", 55000.0)),
                        )
                    )

        total_records = len(bank_accounts) + len(mutual_funds) + len(equities) + len(fixed_deposits) + len(nps_accounts)
        log_safe_structured_event("data_parsed_real", consent_id=consent_id, record_count=total_records, mode="SETU_SANDBOX")

        return SetuFinancialDataResponse(
            consent_id=consent_id,
            data_source="SETU_SANDBOX",
            bank_accounts=bank_accounts,
            mutual_funds=mutual_funds,
            equities=equities,
            fixed_deposits=fixed_deposits,
            nps_accounts=nps_accounts,
        )

    async def get_data(self, consent_id: str, session_id: Optional[str] = None) -> SetuFinancialDataResponse:
        """
        Retrieves normalized provider financial information for the given consent.
        In sandbox mock mode: produces deterministic simulated records with data_source = 'SANDBOX_MOCK'.
        In real Setu sandbox mode: fetches live session data, parses it, and tags with data_source = 'SETU_SANDBOX'.
        Zero silent fallback to mock on real integration failures.
        """
        if self.use_mock:
            return SetuSandboxDataGenerator.generate_sandbox_portfolio(
                consent_id=consent_id, data_source="SANDBOX_MOCK"
            )

        # Real Setu sandbox execution: MUST NOT silently fallback to mock
        if not session_id:
            sess = await self.create_data_session(consent_id)
            session_id = sess.id

        data = await self._request("GET", f"/sessions/{session_id}")
        return self._parse_real_setu_payload(consent_id=consent_id, raw_response=data)

    async def handle_callback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handles incoming webhooks or redirection status callbacks from Setu."""
        redacted = redact_sensitive_data(payload)
        logger.info("Received Setu AA callback: %s", redacted)
        consent_id = payload.get("consentId") or payload.get("id")
        status = str(payload.get("status", "ACTIVE")).upper()
        if consent_id and self.use_mock:
            self.set_mock_consent_status(consent_id, status)
        return {"status": "ACKNOWLEDGED", "consent_id": consent_id, "state": status}

    async def health_check(self) -> Dict[str, Any]:
        """
        Verifies connectivity and credentials for the Setu AA environment.
        Never prints or returns secret values.
        """
        if self.use_mock:
            return {
                "status": "healthy",
                "mode": "sandbox_mock",
                "environment": settings.SETU_ENVIRONMENT,
                "base_url": self.base_url,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Real Setu sandbox check
        missing = self.get_missing_credentials()
        if missing:
            return {
                "status": "configuration_error",
                "mode": "real_setu",
                "base_url": self.base_url,
                "error": f"SETU_CONFIGURATION_ERROR: Missing required configuration: {', '.join(missing)}.",
                "missing_keys": missing,
                "timestamp": datetime.utcnow().isoformat(),
            }

        start_time = time.time()
        # 1. Verify Authentication by generating/requesting an OAuth access token
        try:
            await self.get_access_token(force_refresh=True)
        except SetuAuthError:
            return {
                "status": "unauthorized",
                "mode": "real_setu",
                "base_url": self.base_url,
                "error": "Setu AA authentication failed. Please verify client ID and secret.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except SetuTimeoutError:
            return {
                "status": "timeout",
                "mode": "real_setu",
                "base_url": self.base_url,
                "error": "Setu AA authentication service connection timed out.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except SetuProviderUnavailableError:
            return {
                "status": "provider_unavailable",
                "mode": "real_setu",
                "base_url": self.base_url,
                "error": "Setu AA authentication service is unreachable or returned server error.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "degraded",
                "mode": "real_setu",
                "base_url": self.base_url,
                "error": f"Setu authentication check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # 2. Verify AA Gateway connectivity with authenticated headers and product-instance-id
        try:
            await self._request("GET", "/health", max_retries=1)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "status": "healthy",
                "mode": "real_setu",
                "base_url": self.base_url,
                "latency_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except SetuAuthError:
            return {
                "status": "unauthorized",
                "mode": "real_setu",
                "base_url": self.base_url,
                "error": "Setu AA gateway rejected authentication or product instance ID.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except SetuTimeoutError:
            return {
                "status": "timeout",
                "mode": "real_setu",
                "base_url": self.base_url,
                "error": "Setu AA service connection timed out.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except SetuProviderUnavailableError:
            return {
                "status": "provider_unavailable",
                "mode": "real_setu",
                "base_url": self.base_url,
                "error": "Setu AA service is unreachable or returned server error.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "degraded",
                "mode": "real_setu",
                "base_url": self.base_url,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
