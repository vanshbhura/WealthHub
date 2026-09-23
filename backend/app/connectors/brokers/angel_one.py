from app.connectors.brokers.base import BrokerConnector
from app.connectors.enums import ConnectionMethodStatus


class AngelOneConnector(BrokerConnector):
    connector_key = "angel_one_smartapi"
    name = "Angel One SmartAPI"
    platform_slug = "angel-one"
    status = ConnectionMethodStatus.COMING_SOON
