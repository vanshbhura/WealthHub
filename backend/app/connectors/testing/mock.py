from typing import List, Optional
from datetime import datetime
from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectionMethodStatus
from app.connectors.dtos import (
    NormalizedAccount,
    NormalizedAsset,
    NormalizedHolding,
    NormalizedTransaction,
    NormalizedBalance,
    NormalizedPortfolio,
)


class MockConnector(BaseConnector):
    """
    STRICTLY FOR AUTOMATED TESTING ONLY.
    
    This connector must NEVER be registered in the production catalog or presented to real users.
    It simulates a provider yielding predictable normalized DTOs to test:
    provider data -> normalization -> idempotent database upsert -> portfolio engine calculation.
    """
    connector_key = "mock_test_connector"
    name = "Mock Test Connector (Internal Tests Only)"
    connector_type = ConnectorType.DIRECT_API
    status = ConnectionMethodStatus.AVAILABLE

    supports_holdings = True
    supports_transactions = True
    supports_balances = True

    def __init__(self, sample_portfolio: Optional[NormalizedPortfolio] = None):
        self.sample_portfolio = sample_portfolio

    async def connect(self, user_id, credentials=None, **kwargs):
        return {"status": "CONNECTED", "mock": True}

    async def sync(self, connection) -> NormalizedPortfolio:
        if self.sample_portfolio:
            return self.sample_portfolio

        # Default predictable test dataset
        account = NormalizedAccount(
            account_name="Test Demat Account",
            account_type="DEMAT",
            masked_identifier="****1234",
            currency="INR",
            external_account_reference="ext_acc_001",
        )

        stock_asset = NormalizedAsset(
            name="Infosys Limited",
            asset_type="STOCKS",
            symbol="INFY",
            identifier="INE009A01021",
            quantity=10.0,
            average_buy_price=1400.0,
            invested_amount=14000.0,
            current_price=1500.0,
            current_value=15000.0,
        )

        holding = NormalizedHolding(
            asset=stock_asset,
            account_reference="ext_acc_001",
        )

        tx = NormalizedTransaction(
            external_transaction_id="tx_infy_buy_001",
            transaction_type="BUY",
            transaction_date=datetime(2026, 1, 15, 10, 0, 0),
            quantity=10.0,
            price=1400.0,
            amount=14000.0,
            asset_identifier="INE009A01021",
        )

        balance = NormalizedBalance(
            currency="INR",
            available_cash=5000.0,
            invested_amount=14000.0,
            total_balance=19000.0,
        )

        return NormalizedPortfolio(
            accounts=[account],
            holdings=[holding],
            transactions=[tx],
            balances=[balance],
        )
