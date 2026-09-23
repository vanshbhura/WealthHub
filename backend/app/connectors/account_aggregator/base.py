from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectionMethodStatus


class AccountAggregatorConnector(BaseConnector):
    """
    Base class for RBI-regulated Account Aggregator (AA) ecosystem connectors.
    Designed to aggregate consent-based financial information from Financial Information Providers (FIPs)
    such as Banks (Savings, Current, FDs, RDs), Mutual Funds, Insurance, and Pension schemes.
    
    IMPORTANT: This connector is strictly separated from single-broker direct APIs.
    Mutual fund holdings purchased via Groww or Zerodha Coin are fetched via AA or CAS,
    not broker equity APIs.
    """
    connector_type = ConnectorType.ACCOUNT_AGGREGATOR
    connector_key = "account_aggregator"
    name = "Account Aggregator"
    status = ConnectionMethodStatus.COMING_SOON

    supports_holdings = True
    supports_transactions = True
    supports_balances = True
    supports_orders = False
    supports_statements = False
