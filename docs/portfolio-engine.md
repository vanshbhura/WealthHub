# WealthHub Portfolio & Wealth Calculation Engine

This document provides a comprehensive technical reference for the core financial calculation and portfolio engine in WealthHub. It is written to give engineers and auditors a complete understanding of how financial numbers are calculated, tracked, and stored.

---

## 1. Core Financial Principles

1. **Zero Fabrication Policy**: WealthHub never invents synthetic prices, fake historical movements, or estimated transactions. All displayed metrics derive strictly from database-backed records.
2. **Backend Domain Isolation**: All financial logic and valuation algorithms reside exclusively in the backend domain (`app/domain/`) and services (`app/services/`), never in client-side React components.
3. **Internal Precision**: Financial amounts preserve native floating/decimal precision throughout internal calculations and are rounded solely at presentation boundaries (typically to 2 decimal places).
4. **Currency Standardization**: Primary display currency is Indian Rupee (`INR`), with explicit `currency` tagging on all assets, accounts, and transactions for future FX multi-currency support.

---

## 2. Normalized Financial Model

The engine operates on 19 canonical asset categories defined in `app.domain.enums.AssetCategory`:

| Category | Description | Valuation Method |
| :--- | :--- | :--- |
| `STOCK` | Direct equities | Quantity $\times$ Current Price |
| `ETF` | Exchange-Traded Funds | Quantity $\times$ Current Price |
| `MUTUAL_FUND` | Mutual fund units / folios | Quantity $\times$ Current NAV |
| `FD` | Fixed Deposits | Deposit principal + reported accrued interest |
| `RD` | Recurring Deposits | Cumulative deposits + reported accrued interest |
| `P2P` | Peer-to-Peer Loans | Principal outstanding + interest received - write-offs |
| `DIGITAL_GOLD` | Vaulted digital 24K gold | Grams $\times$ Current price per gram |
| `DIGITAL_SILVER`| Vaulted digital 99.9% silver | Grams $\times$ Current price per gram |
| `CRYPTO` | Cryptocurrencies | Quantity $\times$ Current Price |
| `BOND` | Government & Corporate Bonds | Clean/Dirty Price $\times$ Units or reported valuation |
| `SGB` | Sovereign Gold Bonds | Grams $\times$ Current Price + accrued interest |
| `NPS` | National Pension System | Tier 1/2 reported corpus valuation |
| `EPF` | Employee Provident Fund | Cumulative contribution balance + interest |
| `PPF` | Public Provident Fund | Cumulative balance + yearly accrued interest |
| `PHYSICAL_GOLD` | Physical jewelry/bullion | Grams $\times$ Benchmark gold rate |
| `PHYSICAL_SILVER`| Physical silver items | Grams $\times$ Benchmark silver rate |
| `REAL_ESTATE` | Property / Land | Reported appraisal / acquisition basis |
| `CASH` | Bank savings / Cash balances | Current ledger balance |
| `OTHER` | Miscellaneous alternative assets | Reported current valuation |

Legacy aliases (e.g. `STOCKS`, `FIXED_DEPOSITS`, `P2P_LOANS`) are automatically mapped to canonical categories via `normalize_asset_category()`.

---

## 3. Financial Calculation Formulas

### 3.1 Total Wealth
$$\text{Total Wealth} = \sum \text{current\_value of active user assets} + \sum \text{current\_value of standalone accounts}$$

- **Double-Counting Guard**: When an `Account` has child `Asset` holdings attached, the assets represent the underlying value and the parent account balance is not summed twice. Only standalone accounts (e.g., a pure bank savings ledger without sub-assets) are added directly.
- **User Isolation**: Strictly scoped to `WHERE user_id = :authenticated_user_id`.

### 3.2 Invested Amount
$$\text{Invested Amount} = \sum \text{invested\_amount of active assets} + \sum \text{invested\_value of standalone accounts}$$

Where transaction history is recorded, adjustments account for:
$$\text{Invested} = \text{BUY} + \text{DEPOSIT} - \text{Capital returned via SELL}$$

### 3.3 Absolute Profit / Loss
$$\text{Profit/Loss} = \text{Total Wealth} - \text{Invested Amount}$$

### 3.4 Profit / Loss Percentage (Return %)
$$\text{P\&L \%} = \begin{cases} \left(\frac{\text{Profit/Loss}}{\text{Invested Amount}}\right) \times 100 & \text{if } \text{Invested Amount} > 0 \\ \text{null} & \text{if } \text{Invested Amount} = 0 \end{cases}$$

> **Important**: When `Invested Amount == 0`, return percentage evaluates to `null` to avoid `ZeroDivisionError`, `NaN`, `Infinity`, or deceptive zero return claims.

### 3.5 Daily Movement (Today's Change)
Comparing current portfolio total to the most recent historical snapshot strictly before the current calendar day:
$$\text{today\_change} = \text{Current Total} - \text{Previous Snapshot Total}$$
$$\text{today\_change\_percentage} = \begin{cases} \left(\frac{\text{today\_change}}{\text{Previous Snapshot Total}}\right) \times 100 & \text{if } \text{Previous Snapshot Total} > 0 \\ \text{null} & \text{otherwise} \end{cases}$$

If no prior daily snapshot exists:
$$\text{today\_change} = \text{null}, \quad \text{today\_change\_percentage} = \text{null}$$

---

## 4. Extended Internal Rate of Return (XIRR)

The XIRR engine (`app/services/xirr_service.py`) calculates the exact annualized rate of return for irregular cash flows by solving the Net Present Value equation for $r$:

$$NPV(r) = \sum_{i=0}^{n} \frac{C_i}{(1 + r)^{\frac{d_i - d_0}{365}}} = 0$$

Where:
- $C_i$: Cash flow amount (Investments/deposits are **negative**, withdrawals/terminal portfolio value are **positive**)
- $d_i$: Date of the $i$-th cash flow
- $d_0$: Date of the first cash flow

### Algorithm:
1. **Newton-Raphson Iteration**:
   $$r_{k+1} = r_k - \frac{NPV(r_k)}{NPV'(r_k)}$$
   With derivative:
   $$NPV'(r) = \sum_{i=1}^{n} -\frac{d_i - d_0}{365} \cdot C_i \cdot (1 + r)^{-\frac{d_i - d_0}{365} - 1}$$
2. **Bounded Bisection Fallback**: If Newton-Raphson steps out of bounds ($r \le -0.999$ or $r > 50.0$) or derivative approaches zero, the engine automatically switches to a robust bisection search over $[-0.99, 10.0]$ (with expansion up to 100.0).
3. **Invalid Flow Guards**: Returns `null` if fewer than 2 dated flows exist, if all flows have identical signs, or if timespan is 0 days.

---

## 5. Internal Transfers & Cash Reconciliation

When a user transfers funds between two of their own connected platforms (e.g. ₹50,000 from SBI savings account to Groww trading balance):
- The outgoing transaction is recorded as `TRANSFER_OUT` with `transfer_id`.
- The incoming transaction is recorded as `TRANSFER_IN` with the identical `transfer_id`.
- Matching internal transfers net to zero ($\text{TRANSFER\_IN} + \text{TRANSFER\_OUT} = 0$).
- Net user wealth remains unchanged (₹50k decremented from SBI balance, ₹50k incremented on Groww balance).
- Net invested capital is not double-counted as new outside capital injection.

---

## 6. Portfolio Snapshot Engine

### 6.1 Data Model
Stored in `portfolio_snapshots` table:
- `user_id`: UUID
- `snapshot_date`: Date
- `total_value`: Float
- `invested_value`: Float
- `profit_loss`: Float
- `profit_loss_percentage`: Nullable Float
- `cash_value`: Float
- `asset_allocation`: JSON `{ category: value }`
- `platform_values`: JSON `{ platform_name: value }`

### 6.2 Idempotency Guarantee
Enforced by composite database constraint:
```sql
UNIQUE (user_id, snapshot_date)
```
Calling `SnapshotService.capture_daily_snapshot` multiple times on the same date safely executes an **UPSERT**, updating the existing snapshot record rather than duplicating portfolio history.

### 6.3 Historical Query Periods
Supported periods: `1M` (30 days), `2M` (60 days), `6M` (180 days), `12M` (365 days), `24M` (730 days), `5Y` (1825 days).
If fewer than 2 snapshots exist, the engine exposes `has_sufficient_history: false`.

---

## 7. Data Freshness Tracking

Every valuation exposes:
- `last_valued_at`: ISO UTC timestamp
- `data_source`: `BROKER_API`, `AA`, `PROVIDER_API`, `CSV`, `PDF`, or `MANUAL`
- `freshness_status`:
  - `REALTIME`: Automated API sync completed within the last 15 minutes.
  - `RECENT`: Synced within the last 24 hours.
  - `TODAY`: Synced earlier on the current calendar date.
  - `STALE`: Older than 1 calendar day.
  - `UNKNOWN`: Timestamp unavailable.

---

## 8. API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/portfolio/summary` | Consolidated wealth, invested amount, P&L, P&L %, today's change, and quality flags. |
| `GET` | `/api/portfolio/platforms` | Platform breakdown with cards metrics (value, invested, P&L, holdings count, freshness). |
| `GET` | `/api/portfolio/assets` | Granular asset list with calculated P&L, filtered by `platform`, `asset_type`, or `account`. |
| `GET` | `/api/portfolio/snapshots` | Chronological snapshot timeline filtered by `period` (`1M`, `2M`, `6M`, `12M`, `24M`, `5Y`). |
| `GET` | `/api/portfolio/allocation` | Portfolio allocation breakdown by asset type and platform with percentage bases. |
| `POST`| `/api/portfolio/snapshots/capture` | Immediate idempotent daily snapshot capture. |
