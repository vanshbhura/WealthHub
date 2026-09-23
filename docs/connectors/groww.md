# Groww Live Financial Data Connector (Read-Only)

> **Important**: This integration is strictly **READ-ONLY**. WealthHub never places, modifies, or cancels trading orders, and never initiates automated trades.

---

## 1. Supported Capabilities

| Capability | Supported | Description |
| :--- | :--- | :--- |
| **User Profile / UCC** | Yes | Validates credentials via `GET /v1/user/detail`, extracts UCC and enabled segments. |
| **Demat Holdings** | Yes | Fetches delivery stock holdings via `GET /v1/holdings/user` with average buy price and current LTP. |
| **Cash Positions** | Yes | Retrieves open intraday/cash positions via `GET /v1/positions/user?segment=CASH`. |
| **Cash Balances** | Yes | Fetches settled clear cash via `GET /v1/margins/detail/user`. |
| **Orders / Trading** | **No** | Excluded by design. WealthHub does not support order placement. |
| **Mutual Funds** | **No** | Groww's official Trading API covers securities broker Demat assets. Mutual fund folios continue to be imported via WealthHub's Statement Import System (Prompt 6). |

---

## 2. Authentication Architecture & Token Lifecycle

Groww's official Trading API uses Bearer Access Tokens generated through the user's Groww Account portal:

1. **Token Generation**:
   Users generate an API Access Token from **Groww Profile > Settings > Trading APIs**.
2. **Credential Security**:
   - WealthHub encrypts access tokens at rest using `FernetCredentialStore` (AES-128-CBC + HMAC-SHA256).
   - Secret keys and tokens are never returned to the frontend, never stored in browser `localStorage`, and never logged.
   - WealthHub never prompts for or stores Groww login passwords, PINs, or TOTP codes.
3. **Token Expiry**:
   - If an API request receives HTTP 401 or an expired token response, the connection transitions to `AUTH_REQUIRED`.
   - The UI displays an "Authentication Required" status with a "Reconnect" action to update the token.
   - The connector does not retry expired tokens indefinitely.

---

## 3. Environment Configuration

Add the following optional variables to your `.env` file (configured in `backend/app/config.py`):

```bash
# Groww API Configuration
GROWW_API_BASE_URL="https://api.groww.in"
GROWW_API_VERSION="1.0"
GROWW_TIMEOUT_SECONDS=15.0

# Optional: Opt-in for live integration test
# GROWW_LIVE_TEST=1
# GROWW_ACCESS_TOKEN="your_test_token"
```

Never commit `GROWW_ACCESS_TOKEN` to source control.

---

## 4. API Endpoints Used

All requests include the headers:
- `Accept: application/json`
- `Authorization: Bearer <ACCESS_TOKEN>`
- `X-API-VERSION: 1.0`

| Purpose | Method | Official Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Profile Validation** | `GET` | `/v1/user/detail` | Retrieves vendor user ID, UCC, active segments (`CASH`, `FNO`). |
| **Delivery Holdings** | `GET` | `/v1/holdings/user` | Retrieves stock ISINs, trading symbols, quantities, and average prices. |
| **Cash Positions** | `GET` | `/v1/positions/user?segment=CASH` | Retrieves active open positions in the Cash segment. |
| **Margin & Cash** | `GET` | `/v1/margins/detail/user` | Retrieves `clear_cash`, margin used, and collateral. |

---

## 5. Data Normalization & Portfolio Engine Integration

### 5.1 Holdings Normalization
- `isin` $\rightarrow$ `identifier`
- `trading_symbol` $\rightarrow$ `symbol` & `name`
- `asset_type` $\rightarrow$ `STOCK`
- `quantity` $\rightarrow$ Delivery quantity
- `average_price` $\rightarrow$ Acquisition cost basis
- `current_price` $\rightarrow$ Last traded price (`ltp`) or average price fallback
- `current_value` $\rightarrow$ $\text{quantity} \times \text{current\_price}$

### 5.2 Settled Cash vs Margin
- `clear_cash` represents settled funds available in the trading account.
- **Margin Guard**: Collateral (`collateral_available`) and margin facilities (`adhoc_margin`, `net_margin_used`) are **never added directly to total wealth**. Only actual cash and asset equity are recognized.

### 5.3 Coexistence with Statement Imports (No Double-Counting)
- If a user previously imported a Groww statement (Prompt 6) and later connects the Live API:
  - Both resolve to the same underlying `Groww` platform card.
  - Live API becomes the authoritative source for current holding quantities and valuations.
  - Existing imported historical transactions are preserved in the ledger.
  - Holdings matching existing assets by ISIN or symbol update the existing asset in-place without creating duplicates.

---

## 6. Rate Limiting & Error Mapping

- **Limits**: Groww's Non-Trading APIs enforce a rate limit of 20 requests/sec and 500 requests/min.
- **Backoff**: Bounded retries (maximum 2 retries) with exponential backoff on HTTP 429 using the `Retry-After` header.
- **Error Mapping**:
  - `401 / 403` $\rightarrow$ `AuthFailedError` / `TokenExpiredError`
  - `429` $\rightarrow$ `RateLimitedError`
  - `5xx / Timeout` $\rightarrow$ `ProviderUnavailableError`
  - Malformed JSON / Failure status $\rightarrow$ `InvalidResponseError`

---

## 7. Security Policies

1. **Zero Password Collection**: Never ask for or store the user's Groww password.
2. **Encrypted at Rest**: Access tokens are stored using AES-128 via `FernetCredentialStore`.
3. **Strict User Isolation**: All connections, tokens, and records are isolated by authenticated `user_id`.
4. **Token Redaction**: Tokens and secrets are scrubbed from logs, exceptions, and frontend responses.

---

## 8. Testing Strategy

1. **Automated Unit & Integration Tests**:
   - 16 tests in `backend/tests/test_groww_connector.py` covering client headers, profile validation, auth failures, 429 rate limits, holdings normalization, settled cash mapping, idempotency, and import coexistence.
2. **Opt-in Live Test**:
   - `test_live_groww_api_read_only` runs against the official live endpoint only when `GROWW_LIVE_TEST=1` and `GROWW_ACCESS_TOKEN` are set.
