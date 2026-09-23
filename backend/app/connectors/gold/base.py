from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectionMethodStatus


class GoldConnector(BaseConnector):
    """
    Base connector for vaulted digital gold providers (e.g. Augmont, MMTC-PAMP, SafeGold).
    Exposes vaulted gram holdings, purchase transactions, and live valuation.
    """
    connector_type = ConnectorType.PROVIDER_API
    connector_key = "gold_provider"
    name = "Digital Gold Provider API"
    status = ConnectionMethodStatus.COMING_SOON

    supports_holdings = True
    supports_transactions = True
    supports_balances = False
    supports_orders = False
    supports_statements = False
