"""Verify the account-word migration and concurrent saves in a disposable PostgreSQL cluster."""
import argparse
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text


@contextmanager
def temporary_cluster_dir():
    # Windows initdb drops its administrator token. Inherit the parent ACL.
    root=Path(tempfile.gettempdir())/("wordspeak-pg-audit-"+uuid4().hex)
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend",type=Path,required=True)
    args=parser.parse_args()
    backend=args.backend.resolve()
    pg_ctl=shutil.which("pg_ctl")
    initdb=shutil.which("initdb")
    if not pg_ctl or not initdb:
        parser.error("PostgreSQL server binaries must be on PATH")
    sys.path.insert(0,str(backend))
    from app.main import app
    from app.db import get_engine
    with temporary_cluster_dir() as root:
        cluster=root/"cluster"
        password=secrets.token_hex(24)
        pwfile=root/"password"
        pwfile.write_text(password,encoding="ascii")
        subprocess.run([initdb,"-D",str(cluster),"-U","wordspeak_audit","-A","scram-sha-256",
                        "--pwfile",str(pwfile),"--no-locale","-E","UTF8"],check=True,stdout=subprocess.DEVNULL)
        pwfile.unlink()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0))
            port=sock.getsockname()[1]
        subprocess.run([pg_ctl,"-D",str(cluster),"-l",str(root/"postgres.log"),"-w","-o",
                        f"-h 127.0.0.1 -p {port}","start"],check=True,stdout=subprocess.DEVNULL)
        try:
            os.environ["DATABASE_URL"]=f"postgresql+psycopg://wordspeak_audit:{password}@127.0.0.1:{port}/postgres"
            os.environ["JWT_SECRET"]=secrets.token_hex(32)
            os.chdir(backend)
            config=Config(backend/"alembic.ini")
            command.upgrade(config,"head")
            command.check(config)
            with TestClient(app) as client:
                credentials={"email":"tester@example.test","password":secrets.token_urlsafe(20)}
                auth=client.post("/auth/register",json=credentials).raise_for_status().json()
                headers={"Authorization":"Bearer "+auth["access_token"]}
                payload={"word":"catch up","phrase":"Let's catch up.","situation":"When are you free?"}
                def save(_):
                    return client.put("/practice-words",headers=headers,json=payload).raise_for_status().json()
                with ThreadPoolExecutor(max_workers=8) as pool:
                    ids={card["id"] for card in pool.map(save,range(24))}
                assert len(ids)==1
                queue=client.get("/cards/due",headers=headers).raise_for_status().json()
                assert len(queue)==1 and queue[0]["id"] in ids
                review={"card_id":queue[0]["id"],"rating":3,"request_id":str(uuid4())}
                rated=client.post("/reviews",headers=headers,json=review).raise_for_status().json()["card"]
                edited=client.put("/practice-words",headers=headers,json={**payload,"situation":"Can we talk tomorrow?"}).raise_for_status().json()
                assert all(edited[k]==rated[k] for k in ("id","due","stability","difficulty"))
            command.downgrade(config,"0003_review_retries")
            with get_engine().connect() as conn:
                assert conn.scalar(text("SELECT count(*) FROM cards"))==1 and conn.scalar(text("SELECT count(*) FROM reviews"))==1
            print("Disposable PostgreSQL: migration validated, 24 saves with 8 workers created one card, review state survived editing and downgrade.")
        finally:
            get_engine().dispose()
            subprocess.run([pg_ctl,"-D",str(cluster),"-m","fast","-w","stop"],check=True,stdout=subprocess.DEVNULL)


if __name__=="__main__":
    main()
