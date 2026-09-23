from app.connectors.brokers.base import BrokerConnector
from app.connectors.enums import ConnectionMethodStatus


class ZerodhaConnector(BrokerConnector):
    connector_key = "zerodha_kite"
    name = "Zerodha Kite Connect"
    platform_slug = "zerodha"
    status = ConnectionMethodStatus.COMING_SOON
