from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectionMethodStatus


class CryptoConnector(BaseConnector):
    """
    Base class for cryptocurrency exchange integrations (e.g. CoinDCX, ZebPay, Mudrex, CoinSwitch).
    Exposes holdings, wallet balances, and ledger transactions.
    """
    connector_type = ConnectorType.PROVIDER_API
    connector_key = "crypto_provider"
    name = "Crypto Exchange API"
    status = ConnectionMethodStatus.COMING_SOON

    supports_holdings = True
    supports_transactions = True
    supports_balances = True
    supports_orders = False
    supports_statements = False
