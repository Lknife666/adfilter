"""Rule format handlers."""

from .base import Handler, discover_plugins, get_handler, register_handler
from .clash_handler import ClashHandler
from .dns_handler import DnsHandler
from .dnsmasq_handler import DnsmasqHandler
from .easylist_handler import EasylistHandler
from .hosts_handler import HostsHandler
from .loon_handler import LoonHandler
from .mikrotik_handler import MikrotikHandler
from .quantumult_handler import QuantumultHandler
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
    QuantumultHandler(),
    LoonHandler(),
)

# v0.4: discover third-party plugins
discover_plugins()

__all__ = [
    "ClashHandler",
    "DnsHandler",
    "DnsmasqHandler",
    "EasylistHandler",
    "Handler",
    "HostsHandler",
    "LoonHandler",
    "MikrotikHandler",
    "QuantumultHandler",
    "SingboxHandler",
    "SmartdnsHandler",
    "SurgeHandler",
    "UnboundHandler",
    "discover_plugins",
    "get_handler",
    "register_handler",
]
