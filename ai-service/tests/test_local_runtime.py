import pytest
from app.local_runtime import audit_local_connections


@pytest.mark.parametrize("event,args", [
    ("socket.connect", (None, ("127.0.0.1", 8013))),
    ("socket.connect", (None, ("::1", 8013, 0, 0))),
    ("socket.getaddrinfo", ("localhost", 8013)),
])
def test_managed_inference_allows_loopback(event, args):
    audit_local_connections(event, args)


@pytest.mark.parametrize("event,args", [
    ("socket.connect", (None, ("192.0.2.1", 443))),
    ("socket.getaddrinfo", ("external.invalid", 443)),
])
def test_managed_inference_blocks_external_python_networking_without_sending(event, args):
    with pytest.raises(OSError, match="External Python network"):
        audit_local_connections(event, args)
