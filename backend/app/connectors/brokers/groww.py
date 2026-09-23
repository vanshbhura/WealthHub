import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.connectors.brokers.base import BrokerConnector
from app.connectors.enums import ConnectionMethodStatus, ConnectorCapability
from app.connectors.dtos import (
    NormalizedAccount,
    NormalizedAsset,
    NormalizedHolding,
    NormalizedTransaction,
    NormalizedBalance,
    NormalizedPortfolio,
)
from app.connectors.exceptions import (
    AuthFailedError,
    TokenExpiredError,
    ConnectorError,
    DataValidationError,
)
from app.connectors.credentials import credential_store
from app.connectors.brokers.groww_client import GrowwApiClient

logger = logging.getLogger("wealthhub.connectors.groww")


class GrowwConnector(BrokerConnector):
    """
    Official live connector for Groww securities broker.
    Provides read-only access to equity holdings, cash positions, Demat profile, and settled cash balances.
    All communication is routed via official Groww Trading API endpoints.
    """

    connector_key: str = "groww_direct"
    name: str = "Groww Direct API"
    platform_slug: str = "groww"
    status: ConnectionMethodStatus = ConnectionMethodStatus.AVAILABLE

    # Capabilities
    supports_holdings: bool = True
    supports_positions: bool = True
    supports_balances: bool = True
    supports_transactions: bool = False
    supports_orders: bool = False
    supports_statements: bool = False

    def _get_client_for_connection(self, connection) -> GrowwApiClient:
        """Retrieves decrypted access token from credential store and builds API client."""
        user_id = connection.user_id
        connection_id = connection.id

        token = credential_store.get_secret(user_id, connection_id, "access_token")
        if not token:
            logger.error("No Groww access token found for connection %s", connection_id)
            raise AuthFailedError(
                "Groww credentials not found or session expired. Please re-authenticate."
            )
        return GrowwApiClient(access_token=token)

    async def connect(
        self,
        user_id: uuid.UUID,
        credentials: Optional[Dict[str, Any]] = None,
        connection_id: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Validates credentials with Groww API and saves encrypted secrets in CredentialStore.
        """
        if not credentials or not credentials.get("access_token"):
            raise AuthFailedError("Groww access token is required to establish connection.")

        access_token = str(credentials["access_token"]).strip()
        client = GrowwApiClient(access_token=access_token)

        # Validate token against Groww User Profile endpoint
        profile_res = await client.get_user_profile()
        payload = profile_res.get("payload") or {}

        ucc = payload.get("ucc")
        vendor_user_id = payload.get("vendor_user_id")

        # If connection_id provided, encrypt and store token
        if connection_id:
            credential_store.store_secret(user_id, connection_id, "access_token", access_token)
            if ucc:
                credential_store.store_secret(user_id, connection_id, "ucc", str(ucc))
            if vendor_user_id:
                credential_store.store_secret(user_id, connection_id, "vendor_user_id", str(vendor_user_id))

        return {
            "status": "CONNECTED",
            "ucc": ucc,
            "vendor_user_id": vendor_user_id,
            "active_segments": payload.get("active_segments", []),
        }

    async def disconnect(
        self, user_id: uuid.UUID, connection_id: uuid.UUID, **kwargs
    ) -> None:
        """Securely revokes all stored secrets for this Groww connection."""
        credential_store.delete_all_secrets(user_id=user_id, connection_id=connection_id)
        logger.info("Revoked Groww credentials for connection %s", connection_id)

    async def get_accounts(self, connection) -> List[NormalizedAccount]:
        """Fetches Groww user profile and creates normalized Demat account."""
        client = self._get_client_for_connection(connection)
        try:
            profile_res = await client.get_user_profile()
            payload = profile_res.get("payload") or {}
            ucc = payload.get("ucc") or connection.external_account_reference or "GROWW-DEMAT"
            masked_ucc = f"UCC-***{str(ucc)[-4:]}" if len(str(ucc)) >= 4 else str(ucc)

            return [
                NormalizedAccount(
                    account_name="Groww Demat Account",
                    account_type="DEMAT",
                    masked_identifier=masked_ucc,
                    currency="INR",
                    external_account_reference=str(ucc),
                    metadata={"active_segments": payload.get("active_segments", [])},
                )
            ]
        except ConnectorError:
            raise
        except Exception as e:
            logger.warning("Failed to fetch Groww account profile: %s", e)
            return [
                NormalizedAccount(
                    account_name="Groww Demat Account",
                    account_type="DEMAT",
                    masked_identifier="GROWW-DEMAT",
                    currency="INR",
                )
            ]

    async def get_holdings(self, connection) -> List[NormalizedHolding]:
        """
        Fetches Demat equity stock delivery holdings from Groww.
        Normalizes into NormalizedHolding DTOs with asset category STOCK.
        """
        client = self._get_client_for_connection(connection)
        res = await client.get_holdings()
        payload = res.get("payload") or {}
        holdings_list = payload.get("holdings", [])

        normalized: List[NormalizedHolding] = []
        for h in holdings_list:
            if not isinstance(h, dict):
                continue

            isin = h.get("isin")
            symbol = h.get("trading_symbol")
            if not isin and not symbol:
                continue

            qty = float(h.get("quantity") or 0.0)
            avg_price = float(h.get("average_price") or 0.0)
            if qty <= 0:
                continue

            invested = qty * avg_price
            # Market valuation: default to average_price if provider market price not in holding object
            current_price = float(h.get("ltp") or h.get("current_price") or avg_price)
            current_val = qty * current_price

            asset_dto = NormalizedAsset(
                name=symbol or isin or "Stock Holding",
                asset_type="STOCK",
                symbol=symbol,
                identifier=isin,
                quantity=qty,
                average_buy_price=avg_price,
                invested_amount=invested,
                current_price=current_price,
                current_value=current_val,
                currency="INR",
                metadata={
                    "pledged_quantity": h.get("pledge_quantity", 0),
                    "locked_quantity": h.get("demat_locked_quantity", 0),
                    "free_quantity": h.get("demat_free_quantity", qty),
                },
            )

            normalized.append(
                NormalizedHolding(
                    asset=asset_dto,
                    account_reference=connection.external_account_reference,
                )
            )

        return normalized

    async def get_positions(self, connection) -> List[NormalizedHolding]:
        """
        Fetches open cash positions from Groww.
        """
        client = self._get_client_for_connection(connection)
        try:
            res = await client.get_positions(segment="CASH")
            payload = res.get("payload") or {}
            positions_list = payload.get("positions", [])

            normalized: List[NormalizedHolding] = []
            for p in positions_list:
                if not isinstance(p, dict):
                    continue

                qty = float(p.get("quantity") or 0.0)
                if qty == 0:
                    continue

                isin = p.get("isin")
                symbol = p.get("trading_symbol")
                avg_price = float(p.get("average_price") or 0.0)
                invested = abs(qty) * avg_price
                current_price = float(p.get("ltp") or p.get("current_price") or avg_price)
                current_val = abs(qty) * current_price

                asset_dto = NormalizedAsset(
                    name=symbol or isin or "Cash Position",
                    asset_type="STOCK",
                    symbol=symbol,
                    identifier=isin,
                    quantity=qty,
                    average_buy_price=avg_price,
                    invested_amount=invested,
                    current_price=current_price,
                    current_value=current_val,
                    currency="INR",
                    metadata={"position_type": "INTRADAY_CASH"},
                )

                normalized.append(
                    NormalizedHolding(
                        asset=asset_dto,
                        account_reference=connection.external_account_reference,
                    )
                )

            return normalized
        except Exception as e:
            logger.warning("Error fetching Groww positions: %s", e)
            return []

    async def get_balances(self, connection) -> List[NormalizedBalance]:
        """
        Fetches settled clear cash balance from Groww margins endpoint.
        Distinguishes clear settled cash from margin/collateral facilities.
        Margin is NEVER added to total wealth.
        """
        client = self._get_client_for_connection(connection)
        res = await client.get_margin_details()
        payload = res.get("payload") or {}

        clear_cash = float(payload.get("clear_cash") or 0.0)

        return [
            NormalizedBalance(
                currency="INR",
                available_cash=clear_cash,
                invested_amount=0.0,
                total_balance=clear_cash,
                as_of=datetime.utcnow(),
            )
        ]

    async def get_transactions(
        self, connection, since: Optional[datetime] = None
    ) -> List[NormalizedTransaction]:
        """
        Groww API order endpoints are execution/trade specific.
        To maintain zero-fabrication and distinguish current holdings from historical ledger,
        transactions return empty. Users can import complete historical tradebooks via Statement Import.
        """
        return []

    async def sync(self, connection) -> NormalizedPortfolio:
        """
        Executes full synchronized retrieval of Demat accounts, delivery holdings,
        cash positions, and settled cash balance.
        """
        accounts = await self.get_accounts(connection)
        holdings = await self.get_holdings(connection)
        positions = await self.get_positions(connection)
        balances = await self.get_balances(connection)

        # Combine delivery holdings and active cash positions
        all_holdings = holdings + positions

        return NormalizedPortfolio(
            accounts=accounts,
            holdings=all_holdings,
            transactions=[],
            balances=balances,
        )
