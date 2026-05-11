"""Rule format handlers."""

from .base import Handler, get_handler, register_handler
from .clash_handler import ClashHandler
from .dns_handler import DnsHandler
from .dnsmasq_handler import DnsmasqHandler
from .easylist_handler import EasylistHandler
from .hosts_handler import HostsHandler
from .mikrotik_handler import MikrotikHandler
from .singbox_handler import SingboxHandler
from .smartdns_handler import SmartdnsHandler
from .surge_handler import SurgeHandler
from .unbound_handler import UnboundHandler

# eager registration — order matters only for DnsHandler overriding EasylistHandler
_ALL_HANDLERS = (
    EasylistHandler(),
    DnsHandler(),
    DnsmasqHandler(),
    SmartdnsHandler(),
    ClashHandler(),
    HostsHandler(),
    SurgeHandler(),
    SingboxHandler(),
    MikrotikHandler(),
    UnboundHandler(),
)

__all__ = [
    "ClashHandler",
    "DnsHandler",
    "DnsmasqHandler",
    "EasylistHandler",
    "Handler",
    "HostsHandler",
    "MikrotikHandler",
    "SingboxHandler",
    "SmartdnsHandler",
    "SurgeHandler",
    "UnboundHandler",
    "get_handler",
    "register_handler",
]
