from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectionMethodStatus


class P2PConnector(BaseConnector):
    """
    Base connector for NBFC-P2P lending platforms (e.g. LenDenClub, Faircent, LiquiLoans).
    Exposes loan investments, repayments, accrued interest, and outstanding principal.
    """
    connector_type = ConnectorType.PROVIDER_API
    connector_key = "p2p_provider"
    name = "P2P Lending Provider API"
    status = ConnectionMethodStatus.COMING_SOON

    supports_holdings = True
    supports_transactions = True
    supports_balances = True
    supports_orders = False
    supports_statements = False
