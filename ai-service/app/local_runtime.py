"""Restrict Python networking in the managed inference process to loopback."""
import ipaddress
import os
import sys


def audit_local_connections(event, args):
    if event == "socket.connect":
        address = args[1]
        if not isinstance(address, tuple):
            raise OSError("Managed speech inference permits loopback IP sockets only")
        host = address[0]
    elif event == "socket.getaddrinfo":
        host = args[0]
        if host in {None, "localhost", b"localhost"}:
            return
    else:
        return
    if isinstance(host, bytes):
        host = host.decode("ascii")
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    if not loopback:
        raise OSError("External Python network access is disabled in managed speech inference")


def install_local_network_guard():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    sys.addaudithook(audit_local_connections)
