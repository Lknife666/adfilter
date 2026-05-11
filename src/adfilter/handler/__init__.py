"""Rule format handlers."""

from .base import Handler, get_handler, register_handler
from .clash_handler import ClashHandler
from .dns_handler import DnsHandler
from .dnsmasq_handler import DnsmasqHandler
from .easylist_handler import EasylistHandler
from .hosts_handler import HostsHandler
from .smartdns_handler import SmartdnsHandler

# eager registration
_ALL_HANDLERS = (
    EasylistHandler(),
    DnsHandler(),
    DnsmasqHandler(),
    SmartdnsHandler(),
    ClashHandler(),
    HostsHandler(),
)

__all__ = [
    "ClashHandler",
    "DnsHandler",
    "DnsmasqHandler",
    "EasylistHandler",
    "Handler",
    "HostsHandler",
    "SmartdnsHandler",
    "get_handler",
    "register_handler",
]
