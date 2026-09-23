from app.connectors.brokers.base import BrokerConnector
from app.connectors.enums import ConnectionMethodStatus


class DhanConnector(BrokerConnector):
    connector_key = "dhan_direct"
    name = "Dhan HQ API"
    platform_slug = "dhan"
    status = ConnectionMethodStatus.COMING_SOON
