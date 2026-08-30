"""Process-local outbound-network deny guard for Solid AI development runs.

Only loopback destinations are allowed. This blocks accidental Internet access from the
Python GUI/MCP processes while preserving the localhost HTTP link to SolidPilot.
"""

from __future__ import annotations

import ipaddress
import socket

_ALLOWED_NAMES = {"localhost"}
_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_GETADDRINFO = socket.getaddrinfo


def _allowed_host(host: object) -> bool:
    if not isinstance(host, str):
        return False
    value = host.strip().strip("[]").lower()
    if value in _ALLOWED_NAMES:
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def _guard_getaddrinfo(host, port, *args, **kwargs):
    if not _allowed_host(host):
        raise OSError(
            f"Solid_Ai offline policy blocked DNS/network access to {host!r}; "
            "only localhost/loopback is allowed."
        )
    return _ORIGINAL_GETADDRINFO(host, port, *args, **kwargs)


def _guard_connect(self, address):
    host = address[0] if isinstance(address, tuple) and address else None
    if not _allowed_host(host):
        raise OSError(
            f"Solid_Ai offline policy blocked network connection to {host!r}; "
            "only localhost/loopback is allowed."
        )
    return _ORIGINAL_CONNECT(self, address)


socket.getaddrinfo = _guard_getaddrinfo
socket.socket.connect = _guard_connect
