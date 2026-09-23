# WealthHub Statement Import System Architecture & Reference

This document provides a technical specification of the CSV, Excel, and PDF Statement Import Subsystem in WealthHub. It outlines the design, parsing mechanics, column mapping heuristics, deduplication pipeline, transactional commit lifecycle, and security model.

---

## 1. Architectural Overview

The Statement Import System bridges semi-structured offline records (brokerage tradebooks, bank account statements, mutual fund CAS reports) into WealthHub's canonical portfolio engine.

```
                          ┌────────────────────────┐
                          │   Frontend Wizard UI   │
                          │(4-step React component)│
                          └───────────┬────────────┘
                                      │
                         REST API (Multipart/JSON)
                                      ▼
                       ┌──────────────────────────────┐
                       │  routers/imports.py          │
                       │  - POST /api/imports         │
                       │  - PATCH /api/imports/{id}   │
                       │  - POST .../commit           │
                       └──────────────┬───────────────┘
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
┌───────────────────────┐                           ┌───────────────────────┐
│ app/imports/parsers/  │                           │ app/imports/services/ │
│ - CSVParser (sniffed) │                           │ - PreviewService      │
│ - XLSXParser (openpyxl│                           │ - DeduplicationService│
│ - PDFParser (pypdf)   │                           │ - CommitService       │
└───────────┬───────────┘                           └───────────┬───────────┘
            │                                                   │
            └─────────────────────────┬─────────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │ app/connectors/           │
                        │ - ImportConnector         │
                        │ - SyncService             │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
             ┌─────────────────────────────────────────────────┐
             │ Atomic Database Transaction (PostgreSQL)        │
             │ - Connection (platform-linked)                  │
             │ - Accounts & Assets (holdings)                  │
             │ - Transactions (with SHA-256 fingerprint)       │
             │ - SyncLog (AUDIT trail)                         │
             │ - ImportJob (COMPLETED state)                   │
             └─────────────────────────────────────────────────┘
```

---

## 2. Core Security & Data Principles

1. **Zero Data Fabrication**: WealthHub never synthesizes rows or guesses missing numbers. Scanned/rasterized PDFs lacking extractable text streams are rejected with safe, actionable error messages.
2. **Strict User Isolation**: All jobs, uploaded data, preview caches, and commit transactions are strictly partitioned by `user_id`. Attempting to access another user's `job_id` returns `404 Not Found`.
3. **Atomic Commit & Rollback**: Commits execute inside a single transactional database session. If any row fails validation or DB integrity rules, the entire batch rolls back.
4. **Idempotent Imports**: Statements can be uploaded repeatedly without duplicating entries. Duplication is evaluated through both provider transaction IDs and canonical deterministic SHA256 fingerprints.
5. **No File Persistence**: Uploaded statement files are parsed in-memory, converted to validated JSON preview payloads within `import_jobs`, and never written to unsecured disk storage.

---

## 3. Supported File Formats & Parsers

| Format | Library | Detection & Parsing Logic |
| :--- | :--- | :--- |
| **CSV** (`.csv`) | Standard `csv.Sniffer` | Detects delimiter (comma, semicolon, tab). Auto-handles Windows (`\r\n`) and Unix (`\n`) newlines. Strips byte-order marks (`utf-8-sig`). Skips metadata headers. |
| **Excel** (`.xlsx`, `.xls`) | `openpyxl` | Reads active sheet dataOnly mode to evaluate computed formulas. Normalizes Python `datetime` objects and Excel numeric serial dates. |
| **PDF** (`.pdf`) | `pypdf` | Extracts textual streams page-by-page. Tabular regex parsers isolate tabular transaction rows. Fails safely if zero text characters or empty tables are extracted. |

Files with unsupported extensions (e.g. `.exe`, `.zip`) are rejected immediately with HTTP 400.

---

## 4. Column Mapping & Format Normalization

### 4.1 Auto-Detection Profiles

The system maintains built-in mapping profiles in `app/imports/mappers/mapping_profiles.py`:
- **Zerodha Tradebook / Holdings**: `symbol`, `isin`, `trade_date`, `trade_type`, `quantity`, `price`
- **Groww**: `Stock Name`, `Type`, `Shares`, `Avg. Price`, `Total Value`
- **Upstox**: `Scrip Name`, `Side`, `Qty`, `Price`, `Execution Time`
- **Bank Statements (HDFC, ICICI, SBI)**: `Date`, `Narration / Description`, `Withdrawal (Dr)`, `Deposit (Cr)`, `Balance`
- **CAMS / KFintech CAS**: `Folio Number`, `Scheme Name`, `Purchase Date`, `NAV`, `Units`

If headers do not match a known profile, `ColumnMapper.auto_detect()` computes header string similarity (Levenshtein distance & normalized token matching) to propose a mapping. Users can re-map or override columns via `PATCH /api/imports/{id}/mapping`.

### 4.2 Indian Number System Normalization

Statements commonly represent numbers in Indian formatting (`12,34,567.89`) or parenthesized negative numbers (`(1,500.00)`). The parser normalizes these values deterministically:

$$\text{"₹ 12,34,567.89"} \longrightarrow 1234567.89$$
$$\text{"(1,500.00)"} \longrightarrow -1500.00$$

### 4.3 Date Normalization

Supports diverse regional date formats:
- `YYYY-MM-DD`
- `DD/MM/YYYY` and `DD-MM-YYYY`
- `MM/DD/YYYY`
- `DD-Mon-YYYY` (e.g., `14-Sep-2026`)

Future dates and invalid calendar dates (e.g., February 31) are marked as validation errors.

---

## 5. Deduplication Engine

Every parsed transaction row is inspected against existing transactions for the platform connection:

```
Row to Check
   │
   ├─► Does row have provider_transaction_id?
   │     ├─ YES: Check if connection already has this provider_transaction_id
   │     │        ├─ Match Found: Mark EXACT_DUPLICATE
   │     │        └─ No Match: Proceed to fingerprint check
   │     └─ NO: Proceed to fingerprint check
   │
   └─► Compute Canonical SHA256 Fingerprint:
         hash = SHA256(user_id + "|" + platform_id + "|" + date + "|" + 
                       type + "|" + amount + "|" + symbol)
         ├─ Match Found: Mark EXACT_DUPLICATE
         └─ Same Date & Symbol with ~1% Amount Difference:
              Mark POSSIBLE_DUPLICATE (Warning)
```

- **`EXACT_DUPLICATE`**: Skipped automatically during commit to ensure 100% idempotency.
- **`POSSIBLE_DUPLICATE`**: Surfaced in the preview table as a warning for user inspection.
- **`NEW`**: Committed as a new record.

---

## 6. Database Schema (`import_jobs`)

Defined in `app/models/import_job.py` and tracked in Alembic migration `004_add_import_jobs.py`:

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary Key |
| `user_id` | `UUID` (FK) | Scoped to authenticated user |
| `platform_id` | `UUID` (FK) | Target financial platform |
| `connection_id`| `UUID` (FK, Nullable) | Associated connection record |
| `filename` | `String(255)` | Original uploaded file name |
| `file_type` | `String(20)` | `CSV`, `XLSX`, `PDF` |
| `import_type` | `String(50)` | `BROKER`, `BANK`, `MUTUAL_FUND`, `CRYPTO`, `GENERIC` |
| `status` | `String(50)` | `UPLOADED`, `PARSED`, `VALIDATED`, `INVALID`, `COMPLETED`, `FAILED` |
| `preview_data` | `JSONB` | Extracted rows, parsed columns, duplicate statuses, warnings/errors |
| `column_mapping`| `JSONB` | Canonical target-to-source column map |
| `total_rows` | `Integer` | Total rows extracted |
| `valid_rows` | `Integer` | Rows passing all validation checks |
| `error_count` | `Integer` | Rows with blocking errors |
| `warning_count`| `Integer` | Rows with non-blocking warnings |
| `duplicate_count`| `Integer` | Rows flagged as exact duplicates |
| `committed_count`| `Integer` | Rows successfully committed to portfolio |
| `created_at` | `DateTime` | Ingestion timestamp |
| `updated_at` | `DateTime` | Last status update timestamp |

---

## 7. REST API Reference

All endpoints require standard `Authorization: Bearer <access_token>` headers.

### `POST /api/imports`
Upload a statement file and initiate parsing.
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: Statement file (`.csv`, `.xlsx`, `.pdf`)
  - `platform_id`: UUID of target platform
  - `import_type`: `BROKER`, `BANK`, `MUTUAL_FUND`, `CRYPTO`, `GENERIC`
  - `connection_id` *(optional)*: Existing connection UUID
- **Response**: `201 Created` with full `ImportJobResponse` schema.

### `GET /api/imports/{id}`
Fetch status and cached preview data of an import job.
- **Response**: `200 OK` with rows, validation issues, detected columns, and duplicate statuses.

### `PATCH /api/imports/{id}/mapping`
Apply custom column mappings and trigger immediate re-validation.
- **Body**: `{"column_mapping": {"date": "Trade Date", "amount": "Net Amount", ...}}`
- **Response**: `200 OK` with refreshed preview payload and updated counts.

### `POST /api/imports/{id}/commit`
Execute atomic commit of all non-duplicate valid rows.
- **Constraints**: Rejects if `status == 'INVALID'` or `error_count > 0`.
- **Response**: `200 OK` with `{ "committed_count": N, "duplicate_count": M, "asset_count": P }`.

---

## 8. Frontend User Experience

Integrated directly into `PlatformDetailPage` and `AddPlatformModal`:

1. **Step 1: Category & File Upload**: User chooses category and drops/selects a statement file with drag-and-drop support.
2. **Step 2: Column Mapping**: Visual table mapping required and optional fields with confidence indicators and live sample values.
3. **Step 3: Preview & Validation**: Interactive table with color-coded rows (`Valid`, `Duplicate`, `Error`, `Warning`), filter tabs (`All`, `New`, `Duplicates`, `Errors`), and error popovers.
4. **Step 4: Commit & Summary**: Instant completion stats showing added assets, recorded transactions, and skipped duplicates with automatic dashboard re-sync.
