import abc
import uuid
from typing import List, Optional, Set
from datetime import datetime

from app.connectors.enums import ConnectorType, ConnectorCapability, ConnectionMethodStatus
from app.connectors.dtos import (
    NormalizedAccount,
    NormalizedHolding,
    NormalizedTransaction,
    NormalizedBalance,
    NormalizedPortfolio,
)
from app.connectors.exceptions import ConnectorNotImplementedError


class BaseConnector(abc.ABC):
    """
    Abstract base class representing a financial platform connector.
    Connectors are responsible for communicating with external providers,
    authenticating, and transforming provider-specific payloads into WealthHub normalized DTOs.
    """

    connector_key: str = "base"
    connector_type: ConnectorType = ConnectorType.DIRECT_API
    name: str = "Base Connector"
    status: ConnectionMethodStatus = ConnectionMethodStatus.COMING_SOON

    # Capability detection flags
    supports_holdings: bool = False
    supports_positions: bool = False
    supports_transactions: bool = False
    supports_balances: bool = False
    supports_orders: bool = False
    supports_statements: bool = False

    def get_capabilities(self) -> List[ConnectorCapability]:
        """Returns the list of capabilities supported by this connector."""
        caps: List[ConnectorCapability] = []
        if self.supports_holdings:
            caps.append(ConnectorCapability.HOLDINGS)
        if self.supports_positions:
            caps.append(ConnectorCapability.POSITIONS)
        if self.supports_transactions:
            caps.append(ConnectorCapability.TRANSACTIONS)
        if self.supports_balances:
            caps.append(ConnectorCapability.BALANCES)
        if self.supports_orders:
            caps.append(ConnectorCapability.ORDERS)
        if self.supports_statements:
            caps.append(ConnectorCapability.STATEMENTS)
        return caps

    def is_available(self) -> bool:
        """Indicates whether this connector is actively implemented and available for live or sandbox use."""
        return self.status in (ConnectionMethodStatus.AVAILABLE, ConnectionMethodStatus.SANDBOX)

    async def connect(
        self, user_id: uuid.UUID, credentials: Optional[dict] = None, **kwargs
    ) -> dict:
        """
        Initiates authorization or connection to the provider.
        Raises ConnectorNotImplementedError if the connector is not live.
        """
        if not self.is_available():
            raise ConnectorNotImplementedError(
                f"{self.name} is coming soon and direct connection is not yet implemented."
            )
        return {"status": "CONNECTED"}

    async def disconnect(
        self, user_id: uuid.UUID, connection_id: uuid.UUID, **kwargs
    ) -> None:
        """Performs any provider-side token revocation upon disconnection."""
        pass

    async def get_accounts(self, connection) -> List[NormalizedAccount]:
        """Fetches and normalizes accounts belonging to this connection."""
        if not self.is_available():
            raise ConnectorNotImplementedError(f"{self.name} accounts fetching is not implemented.")
        return []

    async def get_holdings(self, connection) -> List[NormalizedHolding]:
        """Fetches and normalizes investment holdings."""
        if not self.is_available():
            raise ConnectorNotImplementedError(f"{self.name} holdings fetching is not implemented.")
        return []

    async def get_transactions(
        self, connection, since: Optional[datetime] = None
    ) -> List[NormalizedTransaction]:
        """Fetches and normalizes transaction history."""
        if not self.is_available():
            raise ConnectorNotImplementedError(f"{self.name} transactions fetching is not implemented.")
        return []

    async def get_balances(self, connection) -> List[NormalizedBalance]:
        """Fetches and normalizes cash / portfolio balances."""
        if not self.is_available():
            raise ConnectorNotImplementedError(f"{self.name} balances fetching is not implemented.")
        return []

    async def sync(self, connection) -> NormalizedPortfolio:
        """
        Orchestrates full sync of accounts, holdings, transactions, and balances.
        Returns aggregated NormalizedPortfolio.
        """
        if not self.is_available():
            raise ConnectorNotImplementedError(
                f"{self.name} sync is not implemented yet."
            )

        accounts = await self.get_accounts(connection)
        holdings = await self.get_holdings(connection)
        transactions = await self.get_transactions(connection)
        balances = await self.get_balances(connection)

        return NormalizedPortfolio(
            accounts=accounts,
            holdings=holdings,
            transactions=transactions,
            balances=balances,
        )
