# WealthHub Account Aggregator (AA) Integration: Setu Sandbox & Hardening

> [!WARNING]
> **SANDBOX / DEVELOPER ENVIRONMENT ONLY**  
> This implementation connects strictly to the **Setu Developer Sandbox** (`https://fiu-sandbox.setu.co`) or runs in internal mock sandbox mode. It does **not** represent production AA/FIU authorization. We do not claim production Account Aggregator access, do not connect to real customer bank credentials, and do not bypass RBI FIU regulatory registration requirements. Production AA access requires the appropriate FIU/regulatory/provider onboarding and is outside this implementation.

---

## 1. Overview & Architecture

WealthHub's Account Aggregator (AA) layer enables consent-based financial data ingestion through RBI-regulated Account Aggregator rails using the **Setu AA Sandbox** environment.

The architecture strictly decouples provider-specific schemas from WealthHub's canonical domain layer:

```
Setu Sandbox AA API / Webhook (or Internal Mock Generator)
                          ↓
Setu Provider DTOs (SetuConsentRequest, SetuFinancialDataResponse, etc.)
                          ↓
      AAMapper (maps to canonical NormalizedPortfolio)
                          ↓
  DeduplicationEngine (cross-platform matching & double-counting guards)
                          ↓
  SyncService (idempotent database upsert & log persistence)
                          ↓
PortfolioService & SnapshotService (portfolio recalculation & daily snapshot)
                          ↓
                WealthHub Dashboard
```

This strict separation ensures that **Setu can be replaced at any time with another AA/TSP provider** (e.g. Sahamati-certified TSP, OneMoney, Finvu, Anumati) without modifying any domain models or the portfolio calculation engine.

---

## 2. Mock vs Real Setu Sandbox: Zero Silent Fallback

WealthHub supports two strictly separated execution modes:

| Mode | Data Source Tag | HTTP Calls to Setu | When Active |
|---|---|---|---|
| **Internal Mock Sandbox** | `SANDBOX_MOCK` | No (Offline) | Default in automated tests and local dev when live test flag is false. |
| **Real Setu Sandbox** | `SETU_SANDBOX` | Yes (`fiu-sandbox.setu.co`) | Opt-in via `SETU_LIVE_TEST=true` with valid Setu credentials. |

### The Non-Fallback Guarantee

> [!IMPORTANT]
> **Zero Silent Fallback**: During real integration mode (`SETU_LIVE_TEST=true` or non-mock operation), an API error or network failure from Setu is **never silently caught to return mock data**. A Setu failure is reported directly as a Setu failure (`SetuAuthError`, `SetuProviderUnavailableError`, `SetuTimeoutError`, or `SetuInvalidResponseError`). This guarantees that integration tests honestly verify Setu's live endpoints.

---

## 3. Environment Configuration & Required Credentials

The Account Aggregator layer is configured via environment variables in `backend/.env`:

| Variable | Type | Default | Description |
|---|---|---|---|
| `SETU_ENVIRONMENT` | String | `sandbox` | Environment mode (`sandbox` or `mock`). |
| `SETU_BASE_URL` | URL | `https://fiu-sandbox.setu.co` | Base URL for the Setu AA sandbox endpoints. |
| `SETU_CLIENT_ID` | String | None | Setu Developer Portal Client ID. |
| `SETU_CLIENT_SECRET` | String | None | Setu Developer Portal Client Secret. |
| `SETU_PRODUCT_INSTANCE_ID` | String | None | Setu Product Instance ID for FIU consent flow. |
| `SETU_TIMEOUT_SECONDS` | Float | `15.0` | HTTP request timeout in seconds. |
| `SETU_LIVE_TEST` | Boolean | `false` | When true, runs live integration tests against the Setu sandbox. |

### Startup & Configuration Validation

If real Setu mode is requested (`SETU_LIVE_TEST=true` or explicit real client invocation) but required credentials are missing, WealthHub returns:
```json
{
  "code": "SETU_CONFIGURATION_ERROR",
  "detail": "SETU_CONFIGURATION_ERROR: Missing required configuration: SETU_CLIENT_ID, SETU_CLIENT_SECRET, SETU_PRODUCT_INSTANCE_ID."
}
```
Secret values are **never printed, logged, or returned in error messages**. When credentials are not configured, the default application safely operates in internal mock mode without crashing.

---

## 4. Consent Lifecycle & Status Transitions

WealthHub implements the complete RBI AA consent state lifecycle:

```
[ PENDING ] ──(Customer authorizes in Setu Sandbox)──> [ AUTHORIZED / ACTIVE ]
     │                                                               │
     ├──(Customer denies consent)──────> [ REJECTED ]                │
     │                                                               │
     ├──(Validity window expires)──────> [ EXPIRED ]                 ▼
     │                                                     [ Fetch Financial Data ]
     └──(Customer revokes consent)─────> [ REVOKED ]                 │
                                                               [ SYNCED ]
```

### Supported Statuses:
- **`PENDING`**: Consent request created, waiting for customer authorization via Setu sandbox web URL.
- **`AUTHORIZED` / `ACTIVE`**: Consent approved by user; financial data sessions can now be created. Connection marked as `CONNECTED`.
- **`REJECTED`**: Consent denied by user in sandbox interface. Connection marked as `DISCONNECTED`.
- **`EXPIRED`**: Consent validity window lapsed. New consent required.
- **`REVOKED`**: Consent revoked by customer or FIU. Connection marked as `DISCONNECTED`.
- **`ERROR` / `FAILED`**: Provider error during consent handshake.

The frontend modal displays the actual provider state and **never shows "Connected"** until consent authorization has actually succeeded.

---

## 5. Redirect & Callback Handling

1. **Initiation**: `POST /api/account-aggregator/consent` creates a consent request with Setu sandbox and returns a web authorization URL (`https://fiu-sandbox.setu.co/consents/{id}`).
2. **Redirect**: The frontend modal presents this URL with an external link button allowing the tester to open the Setu sandbox flow in a new browser tab.
3. **Callback**: Setu notifies completion via webhook or browser callback to `/api/account-aggregator/callback`, updating the connection's `consent_status` and triggering synchronization.

---

## 6. Financial Information Data Flow & Supported Data Types

After consent authorization, financial data is ingested via Setu data sessions (`POST /sessions` -> `GET /sessions/{id}`):

| Data Type | Setu FIP Source | Canonical Asset Category | Extracted Data Fields |
|---|---|---|---|
| **Bank Account** | Savings / Current FIP | `AssetCategory.CASH` | Bank name, masked account number, balance, credit/debit transactions with narrations. |
| **Mutual Funds** | CAS (CAMS / KFintech) FIP | `AssetCategory.MUTUAL_FUND` | Scheme name, ISIN, folio number, units, NAV, NAV date, invested amount, current value. |
| **Equities** | Depository (CDSL / NSDL) FIP | `AssetCategory.STOCK` | Company name, symbol, ISIN, Demat account number, quantity, buy price, current price, current value. |
| **Fixed Deposit** | Term Deposit FIP | `AssetCategory.FD` | Bank name, deposit number, principal amount, current value, interest rate, maturity date, tenure. |
| **NPS** | Pension CRA FIP | `AssetCategory.NPS` | Masked PRAN, Tier (Tier-1), total contributions, current value. |

All records are tagged with `data_source = "SETU_SANDBOX"` (or `"SANDBOX_MOCK"` in mock mode) and persisted in the database.

---

## 7. Raw Response Logging & Sensitive Data Redaction

WealthHub enforces strict redaction on all Account Aggregator log streams:
- **Redacted fields**: Account numbers, Demat account numbers, PRAN, PAN (`[REDACTED_PAN]`), Aadhaar (`[REDACTED_AADHAAR]`), phone numbers (`[REDACTED_PHONE]`), email addresses (`[REDACTED_EMAIL]`), auth tokens, client secrets, and transaction details.
- **Safe structured logging**: Only operational metadata is logged:
  ```json
  {"event": "data_parsed_real", "consent_id": "consent-uuid", "record_count": 7, "mode": "SETU_SANDBOX", "duration_ms": 142.5}
  ```

---

## 8. Double-Counting Protection & Wealth Engine

Holdings imported from Account Aggregator (e.g. Reliance, TCS, or Mutual Funds) may overlap with direct broker integrations (such as Groww) or imported CAS statements:
1. `DeduplicationEngine` detects overlaps across platforms using **ISIN**, **Symbol**, and **Demat Account**.
2. Overlapping AA assets are marked with `is_duplicate: true` in `metadata_json`.
3. `ValuationService` excludes duplicate assets from total wealth and invested value calculations.
4. Second and subsequent sync runs are strictly idempotent with zero duplicate transactions.
5. `SnapshotService` creates a daily snapshot capturing verified net worth for the dashboard graph without synthesizing fake historical data.

---

## 9. Testing Commands

### Normal Offline Test Suite
Does not require internet access, credentials, or live sandbox connectivity:
```bash
./backend/.venv_linux/bin/pytest backend/tests/ -q
```

### Opt-In Real Setu Sandbox Integration Test
Runs only when explicitly enabled:
```bash
SETU_LIVE_TEST=true ./backend/.venv_linux/bin/pytest backend/tests/test_account_aggregator.py -v
```
- If Setu credentials are not configured in `.env`, the live test is **honestly SKIPPED** explaining which credentials are missing (`SETU_CLIENT_ID`, `SETU_CLIENT_SECRET`, `SETU_PRODUCT_INSTANCE_ID`).
- If credentials are configured, the test makes real HTTP requests to the Setu Sandbox API and records actual PASS/FAIL results without faking passes.

### Frontend Lint and Build Verification
```bash
npm run lint
npm run build
```

---

## 10. Known Setu Sandbox Limitations & Production Boundary

### Sandbox Limitations:
- The Setu sandbox environment returns simulated FIP data for testing.
- Live bank accounts or real user OTPs do not function in the sandbox environment.
- Special test mobile numbers (e.g. `9876543210`) and VPA handles (`9876543210@setu` or `customer@setu`) must be used for sandbox authorization.

### Production Boundary:
- Production AA access requires:
  - Official Non-Banking Financial Company - Account Aggregator (NBFC-AA) or regulated Financial Information User (FIU) onboarding.
  - Sahamati certification and membership.
  - End-to-end data encryption implementation (ECDH key exchange, XML digital signatures per RBI AA specifications).
  - Production TSP agreement with Setu or certified TSP.
- The WealthHub UI is strictly labeled **SETU SANDBOX** and does not make claims of connecting to live customer bank accounts.
