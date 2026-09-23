import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import SessionLocal, engine, Base
from app.models.platform import Platform, PlatformCategory, IntegrationType
from app.models.platform_connector import PlatformConnector, ConnectorType, ConnectorStatus

# Define platform metadata catalog
PLATFORMS_SEED_DATA = [
    {
        "name": "Groww",
        "slug": "groww",
        "category": PlatformCategory.BROKER,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Stocks, Mutual Funds, and Direct investments platform.",
        "logo_url": "https://assets.groww.in/logo-groww270.png",
    },
    {
        "name": "Zerodha",
        "slug": "zerodha",
        "category": PlatformCategory.BROKER,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Kite brokerage platform for stocks, ETFs, and derivatives.",
        "logo_url": "https://zerodha.com/static/images/logo.svg",
    },
    {
        "name": "Upstox",
        "slug": "upstox",
        "category": PlatformCategory.BROKER,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Equities, IPOs, and Mutual Funds brokerage platform.",
        "logo_url": "https://upstox.com/assets/svg/brand/logo.svg",
    },
    {
        "name": "Angel One",
        "slug": "angel-one",
        "category": PlatformCategory.BROKER,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Full-service online brokerage and investment platform.",
        "logo_url": "https://www.angelone.in/static/images/logo.svg",
    },
    {
        "name": "Dhan",
        "slug": "dhan",
        "category": PlatformCategory.BROKER,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Fast tech-first trading platform for Indian equity markets.",
        "logo_url": "https://dhan.co/images/dhan-logo.svg",
    },
    {
        "name": "SBI",
        "slug": "sbi",
        "category": PlatformCategory.BANK,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "State Bank of India — Savings, Term Deposits, and MOD accounts.",
        "logo_url": "https://sbi.co.in/assets/images/logo.png",
    },
    {
        "name": "HDFC Bank",
        "slug": "hdfc-bank",
        "category": PlatformCategory.BANK,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "HDFC Bank savings, fixed deposits, and recurring deposits.",
        "logo_url": "https://www.hdfcbank.com/content/api/contentstream-id/723fb80a-2dde-42a3-9793-7ae1be57c87f/logo.svg",
    },
    {
        "name": "ICICI Bank",
        "slug": "icici-bank",
        "category": PlatformCategory.BANK,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "ICICI Bank savings, iWish, and fixed deposits.",
        "logo_url": "https://www.icicibank.com/assets/images/logo.png",
    },
    {
        "name": "Axis Bank",
        "slug": "axis-bank",
        "category": PlatformCategory.BANK,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Axis Bank retail banking, deposits, and digital accounts.",
        "logo_url": "https://www.axisbank.com/assets/images/logo.png",
    },
    {
        "name": "Kotak Mahindra Bank",
        "slug": "kotak-bank",
        "category": PlatformCategory.BANK,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Kotak 811 savings and ActivMoney sweep accounts.",
        "logo_url": "https://www.kotak.com/content/dam/Kotak/logo.png",
    },
    {
        "name": "LenDenClub",
        "slug": "lendenclub",
        "category": PlatformCategory.P2P,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "RBI-registered NBFC-P2P lending platform for fixed-yield loan pools.",
        "logo_url": "https://www.lendenclub.com/assets/logo.svg",
    },
    {
        "name": "Jar",
        "slug": "jar",
        "category": PlatformCategory.DIGITAL_GOLD,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "SafeGold 24K 995 pure digital gold micro-savings and roundups.",
        "logo_url": "https://myjar.app/logo.png",
    },
    {
        "name": "PhonePe",
        "slug": "phonepe",
        "category": PlatformCategory.DIGITAL_GOLD,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "PhonePe MMTC-PAMP 24K 999.9 vaulted digital gold locker.",
        "logo_url": "https://www.phonepe.com/assets/images/logo.svg",
    },
    {
        "name": "CoinDCX",
        "slug": "coindcx",
        "category": PlatformCategory.CRYPTO,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Crypto spot exchange and portfolio tracking.",
        "logo_url": "https://coindcx.com/assets/images/logo.svg",
    },
    {
        "name": "CAMS / KFintech CAS",
        "slug": "cams-kfintech-cas",
        "category": PlatformCategory.MUTUAL_FUND,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Official Consolidated Account Statement (CAS) covering all Indian mutual funds.",
        "logo_url": "https://mycams.camsonline.com/images/logo.png",
    },
    {
        "name": "Digital Silver Provider",
        "slug": "digital-silver",
        "category": PlatformCategory.DIGITAL_SILVER,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "99.9% fine vaulted physical silver bullion provider.",
        "logo_url": None,
    },
    {
        "name": "EPFO",
        "slug": "epfo",
        "category": PlatformCategory.RETIREMENT,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Employees' Provident Fund Organisation — EPF & EPS accounts.",
        "logo_url": "https://www.epfindia.gov.in/images/logo.png",
    },
    {
        "name": "NPS (National Pension System)",
        "slug": "nps",
        "category": PlatformCategory.RETIREMENT,
        "integration_type": IntegrationType.STATEMENT_IMPORT,
        "description": "Protean / NSDL CRA Tier 1 and Tier 2 pension folios.",
        "logo_url": "https://npscra.nsdl.co.in/images/logo.png",
    },
    {
        "name": "Account Aggregator",
        "slug": "account-aggregator",
        "category": PlatformCategory.AGGREGATOR.value,
        "integration_type": IntegrationType.ACCOUNT_AGGREGATOR.value,
        "description": "RBI-regulated consent-based financial data aggregation (Sandbox).",
        "logo_url": "https://assets.setu.co/logo/setu-logo.svg",
    },
]


def seed_platforms():
    """Idempotently seed platforms metadata and platform connectors."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    inserted = 0
    updated = 0
    connectors_count = 0

    try:
        for item in PLATFORMS_SEED_DATA:
            stmt = select(Platform).where(Platform.slug == item["slug"])
            plat = db.execute(stmt).scalar_one_or_none()

            if plat:
                plat.name = item["name"]
                plat.category = item["category"]
                plat.integration_type = item["integration_type"]
                plat.description = item["description"]
                plat.logo_url = item["logo_url"]
                updated += 1
            else:
                plat = Platform(
                    id=uuid.uuid4(),
                    name=item["name"],
                    slug=item["slug"],
                    category=item["category"],
                    integration_type=item["integration_type"],
                    description=item["description"],
                    logo_url=item["logo_url"],
                    is_active=True,
                )
                db.add(plat)
                db.flush()
                inserted += 1

            # Seed PlatformConnectors for this platform
            # 1. Manual Entry (always AVAILABLE)
            _ensure_connector(
                db=db,
                platform_id=plat.id,
                connector_type=ConnectorType.MANUAL.value,
                connector_key="manual_asset",
                status=ConnectorStatus.AVAILABLE.value,
                capabilities=["HOLDINGS", "TRANSACTIONS", "BALANCES", "ASSETS"],
                is_enabled=True,
            )
            connectors_count += 1

            # 2. Statement Import (AVAILABLE)
            _ensure_connector(
                db=db,
                platform_id=plat.id,
                connector_type=ConnectorType.IMPORT.value,
                connector_key="statement_import",
                status=ConnectorStatus.AVAILABLE.value,
                capabilities=["HOLDINGS", "TRANSACTIONS", "STATEMENTS"],
                is_enabled=True,
            )
            connectors_count += 1

            # 3. Provider/Broker/AA Connector (all COMING_SOON)
            cat = plat.category
            if cat == PlatformCategory.BROKER.value:
                is_groww = plat.slug == "groww"
                _ensure_connector(
                    db=db,
                    platform_id=plat.id,
                    connector_type=ConnectorType.DIRECT_API.value,
                    connector_key=f"{plat.slug}_direct",
                    status=ConnectorStatus.AVAILABLE.value if is_groww else ConnectorStatus.COMING_SOON.value,
                    capabilities=["HOLDINGS", "POSITIONS", "BALANCES"] if is_groww else ["HOLDINGS", "POSITIONS", "TRANSACTIONS", "BALANCES"],
                    is_enabled=is_groww,
                )
                connectors_count += 1
            elif cat in (PlatformCategory.BANK.value, PlatformCategory.MUTUAL_FUND.value, PlatformCategory.RETIREMENT.value):
                _ensure_connector(
                    db=db,
                    platform_id=plat.id,
                    connector_type=ConnectorType.ACCOUNT_AGGREGATOR.value,
                    connector_key="account_aggregator",
                    status=ConnectorStatus.COMING_SOON.value,
                    capabilities=["HOLDINGS", "TRANSACTIONS", "BALANCES"],
                    is_enabled=False,
                )
                connectors_count += 1
            elif cat in (PlatformCategory.DIGITAL_GOLD.value, PlatformCategory.DIGITAL_SILVER.value, PlatformCategory.P2P.value, PlatformCategory.CRYPTO.value):
                _ensure_connector(
                    db=db,
                    platform_id=plat.id,
                    connector_type=ConnectorType.PROVIDER_API.value,
                    connector_key=f"{plat.slug}_api",
                    status=ConnectorStatus.COMING_SOON.value,
                    capabilities=["HOLDINGS", "TRANSACTIONS", "BALANCES"],
                    is_enabled=False,
                )
                connectors_count += 1
            elif cat == PlatformCategory.AGGREGATOR.value or plat.slug == "account-aggregator":
                _ensure_connector(
                    db=db,
                    platform_id=plat.id,
                    connector_type=ConnectorType.ACCOUNT_AGGREGATOR.value,
                    connector_key="setu_aa",
                    status=ConnectorStatus.SANDBOX.value,
                    capabilities=["HOLDINGS", "BALANCES", "TRANSACTIONS", "INVESTMENTS", "ASSETS"],
                    is_enabled=True,
                )
                connectors_count += 1

        db.commit()
        print(f"Platform Seed Completed: {inserted} platforms inserted, {updated} updated, {connectors_count} connectors configured.")
    except Exception as e:
        db.rollback()
        print(f"Error during platform seed: {e}")
        raise
    finally:
        db.close()


def _ensure_connector(db: Session, platform_id: uuid.UUID, connector_type: str, connector_key: str, status: str, capabilities: list, is_enabled: bool):
    stmt = select(PlatformConnector).where(
        PlatformConnector.platform_id == platform_id,
        PlatformConnector.connector_type == connector_type,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        existing.connector_key = connector_key
        existing.status = status
        existing.capabilities = capabilities
        existing.is_enabled = is_enabled
    else:
        conn = PlatformConnector(
            platform_id=platform_id,
            connector_type=connector_type,
            connector_key=connector_key,
            status=status,
            capabilities=capabilities,
            is_enabled=is_enabled,
        )
        db.add(conn)


if __name__ == "__main__":
    seed_platforms()
