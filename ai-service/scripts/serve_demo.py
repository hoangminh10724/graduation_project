"""Run the local MVP with authenticated, graceful restart of this launcher only.

No PID termination, process enumeration or external application shutdown is used.
"""
import argparse
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-service"))
DEFAULT_STATE = ROOT / "data/results/pronunciation_demo_runtime/managed_server.json"


def local_request(base, route, token=None):
    headers = {"X-WordSpeak-Token": token} if token else {}
    request = urllib.request.Request(base + route, data=b"" if token else None, headers=headers)
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=3) as response:
        return json.load(response)


def stop_owned_instance(state_path, base):
    if not state_path.is_file():
        return
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("base_url") != base:
        raise RuntimeError("Saved instance uses another port; it will not be stopped")
    try:
        identity = local_request(base, "/_local/identity")
    except urllib.error.URLError:
        return
    if (identity.get("instance_id") != state.get("instance_id") or
            identity.get("pid") != state.get("pid")):
        raise RuntimeError("The service identity differs; leaving it untouched")
    answer = local_request(base, "/_local/stop", state["stop_token"])
    if not answer.get("stopping"):
        raise RuntimeError("Graceful stop was not accepted")
    for _ in range(75):
        time.sleep(0.2)
        try:
            local_request(base, "/_local/identity")
        except urllib.error.URLError:
            return
    raise RuntimeError("The owned service is still finishing a request; retry later")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8013)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a local port from 1024 through 65535")
    base = f"http://127.0.0.1:{args.port}"
    if args.status:
        try:
            print(json.dumps({"running": True, "url": base + "/demo",
                              "identity": local_request(base, "/_local/identity"),
                              "model": local_request(base, "/demo/status")}))
        except urllib.error.URLError:
            print(json.dumps({"running": False, "url": base + "/demo"}))
        return
    if args.replace or args.stop:
        stop_owned_instance(args.state, base)
        if args.stop:
            print("The authenticated local instance has stopped or was already offline.")
            return
    from app.local_runtime import install_local_network_guard
    install_local_network_guard()
    speech_packages = ROOT / "data/speech-tools"
    if speech_packages.is_dir():
        sys.path.append(str(speech_packages))
    import uvicorn
    from fastapi import HTTPException, Request
    from app.main import app
    from app.pronunciation_demo import BUILD

    token, instance = secrets.token_hex(32), secrets.token_hex(16)
    identity = {"instance_id": instance, "pid": os.getpid(), "build": BUILD}
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="info"))

    @app.get("/_local/identity", include_in_schema=False)
    def local_identity():
        return identity

    @app.post("/_local/stop", include_in_schema=False)
    async def local_stop(request: Request):
        if (not request.client or request.client.host not in {"127.0.0.1", "::1"} or
                not hmac.compare_digest(request.headers.get("X-WordSpeak-Token", ""), token)):
            raise HTTPException(403, "This lifecycle request is not authorized")
        server.should_exit = True
        return {"stopping": True, "instance_id": instance}

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Bind before saving the nonce: never replace another service's state.
        sock.bind(("127.0.0.1", args.port))
        sock.listen(128)
        sock.setblocking(False)
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps({**identity, "base_url": base, "url": base + "/demo",
            "stop_token": token, "started_utc": datetime.now(timezone.utc).isoformat(),
            "running": True}, indent=2), encoding="utf-8")
        print(f"WordSpeak MVP: {base}/demo", flush=True)
        server.run(sockets=[sock])
    finally:
        sock.close()
        if args.state.is_file():
            saved = json.loads(args.state.read_text(encoding="utf-8"))
            if saved.get("instance_id") == instance:
                saved["running"] = False
                args.state.write_text(json.dumps(saved, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
