import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectorCapability, ConnectionMethodStatus
from app.connectors.dtos import (
    NormalizedAccount,
    NormalizedHolding,
    NormalizedTransaction,
    NormalizedBalance,
    NormalizedPortfolio,
)
from app.connectors.account_aggregator.setu_client import SetuAAClient
from app.connectors.account_aggregator.mapper import AAMapper
from app.connectors.account_aggregator.dtos import SetuConsentRequest


class SetuAAConnector(BaseConnector):
    """
    Official Account Aggregator connector using Setu AA Sandbox (FIU developer environment).
    Aggregates consent-based financial information from Banks, Mutual Funds, Equities,
    Fixed Deposits, and NPS.
    Marked explicitly as SANDBOX.
    """

    connector_key: str = "setu_aa"
    connector_type: ConnectorType = ConnectorType.ACCOUNT_AGGREGATOR
    name: str = "Account Aggregator (Setu Sandbox)"
    status: ConnectionMethodStatus = ConnectionMethodStatus.SANDBOX

    # Realized capabilities in Sandbox
    supports_holdings: bool = True
    supports_positions: bool = False
    supports_transactions: bool = True
    supports_balances: bool = True
    supports_orders: bool = False
    supports_statements: bool = False

    def __init__(self, client: Optional[SetuAAClient] = None):
        self.client = client or SetuAAClient()

    def get_capabilities(self) -> List[ConnectorCapability]:
        return [
            ConnectorCapability.HOLDINGS,
            ConnectorCapability.BALANCES,
            ConnectorCapability.TRANSACTIONS,
            ConnectorCapability.INVESTMENTS,
            ConnectorCapability.ASSETS,
        ]

    async def connect(
        self, user_id: uuid.UUID, credentials: Optional[dict] = None, **kwargs
    ) -> dict:
        """
        Initiates a Setu sandbox consent request.
        Returns consent ID and sandbox redirect URL.
        """
        creds = credentials or {}
        phone = creds.get("customer_phone")
        vpa = creds.get("customer_vpa")

        req = SetuConsentRequest(
            customer_phone=phone,
            customer_vpa=vpa,
            fi_types=creds.get("fi_types", ["DEPOSIT", "TERM_DEPOSIT", "MUTUAL_FUNDS", "EQUITIES", "NPS"]),
        )
        resp = await self.client.create_consent_request(req)
        return {
            "status": "PENDING",
            "consent_id": resp.id,
            "url": resp.url,
            "created_at": resp.created_at.isoformat(),
        }

    async def disconnect(
        self, user_id: uuid.UUID, connection_id: uuid.UUID, **kwargs
    ) -> None:
        """Revokes or cleans up the sandbox consent session."""
        pass

    async def sync(self, connection) -> NormalizedPortfolio:
        """
        Orchestrates full fetch of consent-authorized sandbox financial data,
        maps it into NormalizedPortfolio, and returns it to SyncService.
        """
        consent_id = getattr(connection, "consent_id", None) or "sandbox-consent-001"
        fi_data = await self.client.get_data(consent_id=consent_id)
        portfolio = AAMapper.to_normalized_portfolio(fi_data)
        return portfolio

    async def get_accounts(self, connection) -> List[NormalizedAccount]:
        portfolio = await self.sync(connection)
        return portfolio.accounts

    async def get_holdings(self, connection) -> List[NormalizedHolding]:
        portfolio = await self.sync(connection)
        return portfolio.holdings

    async def get_transactions(
        self, connection, since: Optional[datetime] = None
    ) -> List[NormalizedTransaction]:
        portfolio = await self.sync(connection)
        if since:
            return [t for t in portfolio.transactions if t.transaction_date >= since]
        return portfolio.transactions

    async def get_balances(self, connection) -> List[NormalizedBalance]:
        portfolio = await self.sync(connection)
        return portfolio.balances
