from typing import Dict, List, Optional, Type
from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectionMethodStatus
from app.connectors.exceptions import ConnectorNotImplementedError

# Specialized connectors
from app.connectors.manual.manual import ManualConnector
from app.connectors.imports.base import ImportConnector
from app.connectors.brokers.groww import GrowwConnector
from app.connectors.brokers.zerodha import ZerodhaConnector
from app.connectors.brokers.upstox import UpstoxConnector
from app.connectors.brokers.dhan import DhanConnector
from app.connectors.brokers.angel_one import AngelOneConnector
from app.connectors.brokers.fyers import FYERSConnector
from app.connectors.account_aggregator.base import AccountAggregatorConnector
from app.connectors.account_aggregator.setu_connector import SetuAAConnector
from app.connectors.crypto.base import CryptoConnector
from app.connectors.gold.base import GoldConnector
from app.connectors.silver.base import SilverConnector
from app.connectors.p2p.base import P2PConnector


class ConnectorRegistry:
    """
    Central registry for all financial platform connectors.
    Provides connector lookup, capability introspection, and strictly prevents
    unsupported or unintegrated connectors from claiming live connections.
    """

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._platform_mappings: Dict[str, List[str]] = {}  # platform_slug -> list of connector_keys

    def register(
        self, connector: BaseConnector, platform_slugs: Optional[List[str]] = None
    ) -> None:
        """Registers a connector instance with optional platform slug mappings."""
        self._connectors[connector.connector_key] = connector
        if platform_slugs:
            for slug in platform_slugs:
                norm_slug = slug.strip().lower()
                if norm_slug not in self._platform_mappings:
                    self._platform_mappings[norm_slug] = []
                if connector.connector_key not in self._platform_mappings[norm_slug]:
                    self._platform_mappings[norm_slug].append(connector.connector_key)

    def get(self, connector_key: str) -> Optional[BaseConnector]:
        """Retrieves a connector by its unique key."""
        return self._connectors.get(connector_key)

    def get_or_raise(self, connector_key: str) -> BaseConnector:
        """Retrieves connector or raises ConnectorNotImplementedError."""
        conn = self.get(connector_key)
        if not conn:
            raise ConnectorNotImplementedError(
                f"Connector '{connector_key}' is not implemented."
            )
        return conn

    def get_for_platform(self, platform_slug: str) -> List[BaseConnector]:
        """
        Retrieves all connectors associated with a platform slug.
        Every platform always includes ManualConnector (AVAILABLE) and ImportConnector (COMING_SOON),
        plus any provider-specific or AA connector.
        """
        norm_slug = platform_slug.strip().lower()
        keys = self._platform_mappings.get(norm_slug, [])

        result = []
        # Add specific mapped connectors
        for k in keys:
            c = self._connectors.get(k)
            if c and c not in result:
                result.append(c)

        # Ensure universal manual and import connectors are present
        manual = self._connectors.get("manual_asset")
        if manual and manual not in result:
            result.append(manual)

        import_conn = self._connectors.get("statement_import")
        if import_conn and import_conn not in result:
            result.append(import_conn)

        return result

    def is_available(self, connector_key: str) -> bool:
        """Checks if a connector is implemented and available for live or sandbox connections."""
        c = self.get(connector_key)
        return c is not None and c.status in (ConnectionMethodStatus.AVAILABLE, ConnectionMethodStatus.SANDBOX)


# Global connector registry instance initialized with defined connectors
registry = ConnectorRegistry()

# Register core manual and statement import connectors
registry.register(ManualConnector())
registry.register(ImportConnector())

# Register broker connectors (Groww is AVAILABLE, others COMING_SOON)
registry.register(GrowwConnector(), ["groww"])
registry.register(ZerodhaConnector(), ["zerodha"])
registry.register(UpstoxConnector(), ["upstox"])
registry.register(DhanConnector(), ["dhan"])
registry.register(AngelOneConnector(), ["angel-one"])
registry.register(FYERSConnector(), ["fyers"])

# Register Account Aggregator Sandbox connector (SANDBOX available)
registry.register(SetuAAConnector(), ["account-aggregator", "setu_aa"])

# Register Account Aggregator connector for banks, mutual funds, and retirement schemes (COMING_SOON)
registry.register(
    AccountAggregatorConnector(),
    [
        "sbi",
        "hdfc-bank",
        "icici-bank",
        "axis-bank",
        "kotak-bank",
        "cams-kfintech-cas",
        "epfo",
        "nps",
    ],
)

# Register crypto, gold, silver, and P2P connectors (COMING_SOON)
registry.register(CryptoConnector(), ["coindcx", "zebpay", "mudrex", "coinswitch"])
registry.register(GoldConnector(), ["jar", "safegold", "augmont"])
registry.register(SilverConnector(), ["safegold", "augmont"])
registry.register(P2PConnector(), ["lendenclub", "faircent", "liquiloans"])
