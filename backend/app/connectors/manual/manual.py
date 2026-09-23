from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectionMethodStatus
from app.connectors.dtos import NormalizedPortfolio


class ManualConnector(BaseConnector):
    """
    Standard connector for manual asset, account, and transaction tracking.
    This connector is ACTIVE and AVAILABLE for all catalogued platforms, interfacing directly
    with the existing manual asset management engine.
    """
    connector_type = ConnectorType.MANUAL
    connector_key = "manual_asset"
    name = "Manual Entry"
    status = ConnectionMethodStatus.AVAILABLE

    supports_holdings = True
    supports_transactions = True
    supports_balances = True
    supports_orders = False
    supports_statements = False

    async def connect(self, user_id, credentials=None, **kwargs):
        return {"status": "CONNECTED", "connection_type": "MANUAL"}

    async def sync(self, connection) -> NormalizedPortfolio:
        # Manual platforms reflect existing committed database state
        return NormalizedPortfolio()
