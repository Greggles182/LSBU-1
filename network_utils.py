"""
Shared helpers for making HTTP requests bound to a specific network interface
(e.g. "ppp0" or "eth0"), and for inspecting which interface the OS would use.

Binding requires Linux (SO_BINDTODEVICE) and typically root or CAP_NET_RAW --
this app already runs with elevated privileges for GPIO/PiJuice/subprocess work.
"""

import socket
import subprocess

import requests


class InterfaceAdapter(requests.adapters.HTTPAdapter):
    """HTTPAdapter that binds its sockets to a specific network interface."""

    def __init__(self, iface, *args, **kwargs):
        self.iface = iface
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["socket_options"] = (
            requests.packages.urllib3.util.connection.HTTPConnection.default_socket_options
            + [(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, self.iface.encode())]
        )
        super().init_poolmanager(*args, **kwargs)


def resolve_interface(uplink_mode):
    """
    Given config_data["uplink_mode"] ("ppp0" | "eth0" | "auto"), return the
    interface name to bind to, or None to mean "don't force a binding, let the
    OS routing table decide" (used for "auto").
    """
    if uplink_mode in ("ppp0", "eth0"):
        return uplink_mode
    return None


def get_session(interface=None, logger=None):
    """
    Return a requests.Session, optionally bound to a specific network interface.

    interface: "ppp0", "eth0", or None (unbound, default OS routing).
    logger: optional object with .error(msg) / .warning(msg) methods (either the
        stdlib logging.Logger used in thingsboard_uploader.py, or a small shim
        wrapping log_and_print in servertesting.py) for reporting bind failures.

    If binding fails, logs a warning and falls back to an unbound session rather
    than raising.
    """
    session = requests.Session()

    if interface is None:
        return session

    try:
        adapter = InterfaceAdapter(interface)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    except Exception as e:
        msg = (
            f"Failed to bind session to interface '{interface}', falling back to "
            f"default routing: {e}"
        )
        if logger is not None:
            try:
                logger.warning(msg)
            except Exception:
                pass
        else:
            print(msg)
        return requests.Session()

    return session


def get_route_interface(dest="1.1.1.1", timeout=3):
    """
    Ask the kernel which interface it would currently use to reach `dest`,
    without binding or sending any traffic there. Returns the interface name
    as a string, or None if it can't be determined.
    """
    try:
        out = subprocess.check_output(
            ["ip", "-o", "route", "get", dest],
            text=True,
            timeout=timeout,
            stderr=subprocess.DEVNULL,
        )
        tokens = out.split()
        if "dev" in tokens:
            idx = tokens.index("dev")
            return tokens[idx + 1]
    except Exception:
        return None
    return None


def interface_exists(iface):
    """Return True if the named network interface currently exists on the host."""
    try:
        out = subprocess.check_output(
            ["ip", "-o", "link", "show", iface],
            text=True,
            timeout=3,
            stderr=subprocess.DEVNULL,
        )
        return bool(out.strip())
    except Exception:
        return False
