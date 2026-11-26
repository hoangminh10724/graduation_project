"""Start WordSpeak on localhost with PostgreSQL or a local SQLite database."""

import argparse
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request


FRONTEND = Path(__file__).resolve().parents[1]
ROOT = FRONTEND.parent
BACKEND = ROOT / "backend"
SPEECH = ROOT / "ai-service"


def node_executable():
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    node = shutil.which("node")
    if node:
        return node
    if bundled.is_file():
        return str(bundled)
    raise RuntimeError("Không tìm thấy Node.js. Cài Node.js rồi chạy lại.")


def prepare_python(directory):
    venv = directory / f"venv-{sys.version_info.major}.{sys.version_info.minor}"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        subprocess.run([sys.executable, "-m", "venv", venv], check=True)
    requirements = [BACKEND / "requirements.txt", SPEECH / "requirements.txt"]
    digest = hashlib.sha256(b"\0".join(path.read_bytes() for path in requirements)).hexdigest()
    stamp = venv / "wordspeak-requirements"
    if not stamp.is_file() or stamp.read_text().strip() != digest:
        args = [argument for path in requirements for argument in ("-r", str(path))]
        subprocess.run([python, "-m", "pip", "install", *args], check=True)
        stamp.write_text(digest + "\n")
    return python


def check_ports():
    for port in (3000, 8000, 8001):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(f"Cổng {port} đang được sử dụng. Dừng dịch vụ ở cổng này rồi chạy lại.")


def wait_http(url, service):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline and service.poll() is None:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except OSError:
            time.sleep(0.35)
    raise RuntimeError(f"Dịch vụ chưa sẵn sàng tại {url}. Xem thông báo phía trên.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "WordSpeak"
    parser.add_argument("--data-dir", type=Path, default=default_dir)
    parser.add_argument("--build", action="store_true", help="Build lại giao diện trước khi chạy.")
    parser.add_argument("--python", type=Path, help="Dùng môi trường Python đã cài dependencies và PyTorch.")
    args = parser.parse_args()
    node = node_executable()
    check_ports()
    directory = args.data_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    secret_file = directory / "jwt-secret"
    if not secret_file.is_file():
        secret_file.write_text(secrets.token_urlsafe(32), encoding="ascii")

    env = dict(os.environ)
    env.update(
        DATABASE_URL=os.getenv("DATABASE_URL") or f"sqlite:///{(directory / 'wordspeak.db').as_posix()}",
        JWT_SECRET=secret_file.read_text(encoding="ascii").strip(),
        CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000",
        AI_SERVICE_URL="http://127.0.0.1:8001",
        NEXT_PUBLIC_API_URL="",
        NEXT_TELEMETRY_DISABLED="1",
        PORT="3000",
        HOSTNAME="127.0.0.1",
    )
    next_cli = FRONTEND / "node_modules/next/dist/bin/next"
    if not next_cli.is_file():
        raise RuntimeError("Chưa có dependencies của frontend. Chạy npm install trong thư mục frontend.")
    python = args.python.resolve() if args.python else prepare_python(directory)
    if args.build or not (FRONTEND / ".next/BUILD_ID").is_file():
        subprocess.run([node, next_cli, "build"], cwd=FRONTEND, env=env, check=True)

    subprocess.run([python, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True)
    processes = []
    try:
        for path, port in ((SPEECH, 8001), (BACKEND, 8000)):
            service = subprocess.Popen(
                [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=path,
                env=env,
            )
            processes.append(service)
            wait_http(f"http://127.0.0.1:{port}/health", service)
        ui = subprocess.Popen([node, "scripts/start.mjs"], cwd=FRONTEND, env=env)
        processes.append(ui)
        wait_http("http://127.0.0.1:3000/dang-nhap", ui)
        print("\nWordSpeak: http://localhost:3000  |  Ctrl+C để dừng.", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise RuntimeError("Một dịch vụ WordSpeak đã dừng. Xem thông báo phía trên.")
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(processes):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(f"WordSpeak: {error}")
