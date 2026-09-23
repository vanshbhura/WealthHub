from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectionMethodStatus


class BrokerConnector(BaseConnector):
    """Base class for online stock and securities broker integrations."""
    connector_type = ConnectorType.DIRECT_API
    supports_holdings = True
    supports_positions = True
    supports_transactions = True
    supports_balances = True
    supports_orders = False
    status = ConnectionMethodStatus.COMING_SOON
