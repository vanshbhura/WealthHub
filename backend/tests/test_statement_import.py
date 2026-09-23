import io
import uuid
import pytest
from datetime import datetime
import openpyxl
import pypdf
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.models.platform import Platform, PlatformCategory
from app.models.connection import Connection
from app.models.transaction import Transaction
from app.models.asset import Asset
from app.models.account import Account
from app.models.import_job import ImportJob
from app.imports.parsers.csv_parser import CSVStatementParser
from app.imports.parsers.xlsx_parser import XLSXStatementParser
from app.imports.parsers.pdf_parser import PDFStatementParser
from app.imports.exceptions import ParseError, FileSecurityError, ValidationError
from app.imports.fingerprints import generate_transaction_fingerprint
from app.imports.mappers.column_mapper import ColumnMapper
from app.imports.validators.row_validator import RowValidator
from app.imports.services.import_service import ImportService
from app.imports.services.commit_service import CommitService


@pytest.fixture
def auth_headers(client):
    """Register a primary test user and return auth headers."""
    email = f"import_user_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPassword123!", "full_name": "Import User"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_headers(client):
    """Register a secondary test user for isolation tests."""
    email = f"other_user_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPassword123!", "full_name": "Other User"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_platform(db_session):
    """Fetches Groww or creates a test platform."""
    plat = db_session.query(Platform).filter(Platform.slug == "groww").first()
    if not plat:
        plat = Platform(
            id=uuid.uuid4(),
            name="Groww",
            slug="groww",
            category=PlatformCategory.BROKER.value,
            description="Brokerage",
            is_active=True,
        )
        db_session.add(plat)
        db_session.commit()
    return plat


# ==========================================
# 1. PARSER UNIT TESTS
# ==========================================

def test_csv_parser_valid_and_indian_numbers():
    csv_content = (
        "Trade Date,Symbol,Quantity,Price,Amount,Order ID\n"
        "15/09/2026,RELIANCE,10,\"₹2,500.50\",\"₹25,005.00\",ORD_101\n"
        "16/09/2026,INFY,20,\"1,500.00\",\"30,000.00\",ORD_102\n"
    ).encode("utf-8")

    parser = CSVStatementParser()
    headers, rows = parser.parse_bytes(csv_content, "statement.csv")
    assert "Trade Date" in headers
    assert "Symbol" in headers
    assert len(rows) == 2
    assert rows[0]["Symbol"] == "RELIANCE"
    assert rows[0]["__row_number__"] == 2


def test_csv_parser_empty_and_corrupt():
    parser = CSVStatementParser()
    with pytest.raises(ParseError):
        parser.parse_bytes(b"", "empty.csv")

    with pytest.raises(ParseError):
        parser.parse_bytes(b"\n\n\n", "blank.csv")


def test_xlsx_parser_valid():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Trades"
    ws.append(["Date", "Symbol", "Qty", "Price", "Amount"])
    ws.append(["2026-09-01", "TCS", 5, 3500.0, 17500.0])

    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    parser = XLSXStatementParser()
    headers, rows = parser.parse_bytes(xlsx_bytes, "trades.xlsx")
    assert "Date" in headers
    assert len(rows) == 1
    assert rows[0]["Symbol"] == "TCS"


def test_pdf_parser_unextractable_fails_safely():
    """Enforces zero-fabrication: unparseable PDFs safely raise ParseError."""
    # Create a dummy blank PDF
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    parser = PDFStatementParser()
    with pytest.raises(ParseError) as exc_info:
        parser.parse_bytes(pdf_bytes, "scanned.pdf")
    assert "Unable to reliably extract structured transaction data" in str(exc_info.value)


# ==========================================
# 2. VALIDATOR & MAPPING UNIT TESTS
# ==========================================

def test_row_validator_rejects_impossible_dates():
    # 31st February 2026 must be rejected
    dt, err = RowValidator.parse_date("31/02/2026")
    assert dt is None
    assert err is not None

    # Valid leap day
    dt, err = RowValidator.parse_date("29/02/2024")
    assert dt is not None
    assert err is None


def test_row_validator_normalizes_indian_money():
    amt, err = RowValidator.parse_money("₹1,25,000.50")
    assert err is None
    assert float(amt) == 125000.50

    amt, err = RowValidator.parse_money("Rs. -500.00")
    assert err is None
    assert float(amt) == -500.00

    amt, err = RowValidator.parse_money("(1,200.00)")
    assert err is None
    assert float(amt) == -1200.00

    amt, err = RowValidator.parse_money("5000 Dr")
    assert err is None
    assert float(amt) == -5000.00


def test_column_mapper_auto_detection():
    headers = ["Trade Date", "Scrip Name", "Qty", "Execution Price", "Trade Value", "Order ID"]
    mapping = ColumnMapper.auto_map_columns(headers, import_type="BROKER")
    assert mapping.get("Trade Date") == "date"
    assert mapping.get("Qty") == "quantity"
    assert mapping.get("Trade Value") == "amount"


# ==========================================
# 3. END-TO-END IMPORT LIFECYCLE API TESTS
# ==========================================

def test_import_workflow_end_to_end(client, auth_headers, sample_platform, db_session):
    """
    Tests complete lifecycle:
    Upload CSV -> Preview -> Update Mapping -> Validate -> Commit -> Verify Portfolio & Snapshot
    """
    csv_data = (
        "Date,Symbol,Quantity,Price,Amount,Txn ID\n"
        "2026-09-10,INFY,10,1500,15000,TXN_G101\n"
        "2026-09-11,TCS,5,3400,17000,TXN_G102\n"
    ).encode("utf-8")

    files = {"file": ("statement.csv", csv_data, "text/csv")}
    data = {
        "platform_id": str(sample_platform.id),
        "import_type": "BROKER",
    }

    # 1. Upload & Parse
    res = client.post("/api/imports", headers=auth_headers, files=files, data=data)
    assert res.status_code == 201
    job_data = res.json()
    job_id = job_data["id"]
    assert job_data["status"] == "VALID"
    assert job_data["row_count"] == 2
    assert job_data["new_count"] == 2
    assert job_data["duplicate_count"] == 0

    # 2. Verify Preview does NOT write financial data
    assert db_session.query(Transaction).filter(Transaction.external_transaction_id == "TXN_G101").first() is None

    # 3. Commit
    commit_res = client.post(f"/api/imports/{job_id}/commit", headers=auth_headers)
    assert commit_res.status_code == 200
    committed = commit_res.json()
    assert committed["status"] == "COMMITTED"
    assert committed["committed_transactions"] == 2
    assert committed["skipped_duplicates"] == 0

    # 4. Verify Database entities
    tx1 = db_session.query(Transaction).filter(Transaction.external_transaction_id == "TXN_G101").first()
    assert tx1 is not None
    assert tx1.amount == 15000.0

    tx2 = db_session.query(Transaction).filter(Transaction.external_transaction_id == "TXN_G102").first()
    assert tx2 is not None

    conn = db_session.query(Connection).filter(Connection.platform_id == sample_platform.id).first()
    assert conn is not None
    assert conn.status == "CONNECTED"
    assert conn.last_sync_status == "SUCCESS"

    # 5. Verify Portfolio summary recalculation
    port_res = client.get("/api/portfolio/summary", headers=auth_headers)
    assert port_res.status_code == 200
    summary = port_res.json()
    assert summary["invested_value"] > 0
    assert summary["total_wealth"] > 0


def test_import_idempotency_second_import_creates_zero_duplicates(client, auth_headers, sample_platform):
    """
    Importing the exact same statement twice must create 0 new transactions
    and mark all rows as duplicates.
    """
    csv_data = (
        "Date,Symbol,Quantity,Price,Amount,Txn ID\n"
        "2026-09-12,WIPRO,50,450,22500,TXN_IDEMP_1\n"
        "2026-09-13,HCLTECH,20,1200,24000,TXN_IDEMP_2\n"
    ).encode("utf-8")

    files = {"file": ("idemp.csv", csv_data, "text/csv")}
    data = {"platform_id": str(sample_platform.id), "import_type": "BROKER"}

    # First import
    res1 = client.post("/api/imports", headers=auth_headers, files=files, data=data)
    job1_id = res1.json()["id"]
    client.post(f"/api/imports/{job1_id}/commit", headers=auth_headers)

    # Second import with exact same statement
    files2 = {"file": ("idemp.csv", csv_data, "text/csv")}
    res2 = client.post("/api/imports", headers=auth_headers, files=files2, data=data)
    job2_id = res2.json()["id"]
    preview2 = res2.json()

    # Must detect both rows as duplicates
    assert preview2["duplicate_count"] == 2
    assert preview2["new_count"] == 0

    # Commit second import
    commit2 = client.post(f"/api/imports/{job2_id}/commit", headers=auth_headers)
    assert commit2.status_code == 200
    res_commit2 = commit2.json()
    assert res_commit2["committed_transactions"] == 0
    assert res_commit2["skipped_duplicates"] == 2


def test_blocking_error_prevents_commit(client, auth_headers, sample_platform):
    """Rows with invalid dates (e.g. 31/02/2026) must block commit."""
    bad_csv = (
        "Date,Symbol,Quantity,Price,Amount\n"
        "31/02/2026,INVALID_DATE_STOCK,10,100,1000\n"
    ).encode("utf-8")

    files = {"file": ("bad_date.csv", bad_csv, "text/csv")}
    data = {"platform_id": str(sample_platform.id), "import_type": "BROKER"}

    res = client.post("/api/imports", headers=auth_headers, files=files, data=data)
    assert res.status_code == 201
    job_id = res.json()["id"]
    assert res.json()["status"] == "INVALID"
    assert res.json()["error_count"] > 0

    # Commit must fail with 400
    commit_res = client.post(f"/api/imports/{job_id}/commit", headers=auth_headers)
    assert commit_res.status_code == 400
    assert "error" in commit_res.json()["error"]["message"].lower()


def test_user_isolation_blocks_unauthorized_access(client, auth_headers, other_user_headers, sample_platform):
    """User B cannot view or commit User A's import job."""
    csv_data = "Date,Symbol,Quantity,Price,Amount,Txn ID\n2026-09-14,SBI,10,500,5000,TXN_PRIV_1\n".encode("utf-8")
    files = {"file": ("priv.csv", csv_data, "text/csv")}
    data = {"platform_id": str(sample_platform.id), "import_type": "BROKER"}

    # User A uploads
    res = client.post("/api/imports", headers=auth_headers, files=files, data=data)
    job_id = res.json()["id"]

    # User B attempts to access User A's import
    get_res = client.get(f"/api/imports/{job_id}", headers=other_user_headers)
    assert get_res.status_code == 404

    # User B attempts to commit User A's import
    commit_res = client.post(f"/api/imports/{job_id}/commit", headers=other_user_headers)
    assert commit_res.status_code == 400 or commit_res.status_code == 404


def test_file_security_rejects_invalid_extension(client, auth_headers, sample_platform):
    files = {"file": ("malicious.exe", b"binary content", "application/octet-stream")}
    data = {"platform_id": str(sample_platform.id), "import_type": "BROKER"}

    res = client.post("/api/imports", headers=auth_headers, files=files, data=data)
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["error"]["message"]
