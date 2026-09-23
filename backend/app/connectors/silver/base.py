from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectionMethodStatus


class SilverConnector(BaseConnector):
    """
    Base connector for digital silver vaulted providers (e.g. Augmont, MMTC-PAMP, SafeGold).
    Exposes vaulted gram holdings, purity, and transactions.
    """
    connector_type = ConnectorType.PROVIDER_API
    connector_key = "silver_provider"
    name = "Digital Silver Provider API"
    status = ConnectionMethodStatus.COMING_SOON

    supports_holdings = True
    supports_transactions = True
    supports_balances = False
    supports_orders = False
    supports_statements = False
