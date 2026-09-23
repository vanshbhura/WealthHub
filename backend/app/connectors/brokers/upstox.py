from app.connectors.brokers.base import BrokerConnector
from app.connectors.enums import ConnectionMethodStatus


class UpstoxConnector(BrokerConnector):
    connector_key = "upstox_direct"
    name = "Upstox API"
    platform_slug = "upstox"
    status = ConnectionMethodStatus.COMING_SOON
