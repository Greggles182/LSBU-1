"""
Shared helpers for making diagnostic HTTP requests bound to a specific network
interface (e.g. "ppp0" or "eth0"). Normal application traffic stays unbound so
the kernel's routing table chooses the uplink.

Binding requires Linux (SO_BINDTODEVICE) and typically root or CAP_NET_RAW --
this app already runs with elevated privileges for GPIO/PiJuice/subprocess work.
"""

import socket

import requests


class InterfaceAdapter(requests.adapters.HTTPAdapter):
    """HTTPAdapter that binds its sockets to a specific network interface."""

    def __init__(self, iface, *args, **kwargs):
        self.iface = iface
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["socket_options"] = (
            requests.packages.urllib3.connection.HTTPConnection.default_socket_options
            + [(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, self.iface.encode())]
        )
        super().init_poolmanager(*args, **kwargs)


def get_session(interface=None):
    """
    Return a requests.Session, optionally bound to a specific network interface.

    interface: "ppp0", "eth0", or None (unbound, default OS routing).

    If binding fails, raise an error instead of silently allowing the request to
    use another interface.
    """
    session = requests.Session()

    if interface is None:
        return session

    adapter = InterfaceAdapter(interface)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session
