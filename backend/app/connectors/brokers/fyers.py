from app.connectors.brokers.base import BrokerConnector
from app.connectors.enums import ConnectionMethodStatus


class FYERSConnector(BrokerConnector):
    connector_key = "fyers_api"
    name = "FYERS API"
    platform_slug = "fyers"
    status = ConnectionMethodStatus.COMING_SOON
