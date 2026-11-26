"""Run the account review browser test with a disposable receiving-backend database."""
import argparse
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from threading import Thread

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend",type=Path,required=True)
    parser.add_argument("--course",action="store_true")
    args=parser.parse_args()
    sys.path.insert(0,str(args.backend.resolve()))
    from app.main import app as backend
    from app.models import Base
    from app.db import get_db
    from app import llm

    async def test_reply(messages):
        if "Assessment hint: Recording-based" in messages[-1]["content"]:
            yield "Let's listen to your recording together."
            return
        if messages[-1]["content"] == "Unavailable":
            raise llm.LLMError("simulated outage")
        previous = any(m["role"] == "assistant" for m in messages)
        yield "See you there!" if previous else "Where shall we meet?"

    llm.stream_reply = test_reply

    engine=create_engine("sqlite://",poolclass=StaticPool,connect_args={"check_same_thread":False})
    Base.metadata.create_all(engine)
    def db():
        with Session(engine) as session:
            yield session
    backend.dependency_overrides[get_db]=db
    os.environ["JWT_SECRET"]=secrets.token_hex(32)
    os.environ["AI_SERVICE_URL"]="http://127.0.0.1:8013"
    app=FastAPI()
    assets=ROOT/"ai-service/app/demo_static"
    app.mount("/api",backend)
    @app.api_route("/demo/course",methods=["GET"])
    @app.api_route("/demo/course/{path:path}",methods=["GET","POST"])
    @app.post("/transcribe")
    async def relay(request:Request,path:str=""):
        url="http://127.0.0.1:8013"+request.url.path
        async with httpx.AsyncClient(timeout=90) as client:
            result=await client.request(request.method,url,params=request.query_params,
                content=await request.body(),headers={"Content-Type":request.headers.get("content-type","")})
        return Response(result.content,status_code=result.status_code,media_type=result.headers.get("content-type"))
    @app.post("/tutor/observe")
    async def observe(request:Request):
        async with httpx.AsyncClient(timeout=120) as client:
            result=await client.post("http://127.0.0.1:8013/tutor/observe",
                                     content=await request.body(),headers={"Content-Type":request.headers["content-type"]})
        return Response(result.content,status_code=result.status_code,media_type="application/json")
    app.mount("/demo/assets",StaticFiles(directory=assets))
    @app.get("/demo")
    def lab():
        return FileResponse(assets/"index.html")
    @app.get("/demo/review")
    def page():
        return FileResponse(assets/"account-review.html")
    @app.get("/demo/config")
    def config():
        return httpx.get("http://127.0.0.1:8013/demo/config").raise_for_status().json()

    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        url=f"http://127.0.0.1:{sock.getsockname()[1]}"
        backend.state.cors_origins=[url]
        server=uvicorn.Server(uvicorn.Config(app,log_level="error"))
        thread=Thread(target=server.run,kwargs={"sockets":[sock]},daemon=True)
        thread.start()
        try:
            script="browser_course.cjs" if args.course else "browser_account_review.cjs"
            subprocess.run(["node",str(ROOT/"ai-service/tests"/script),url],check=True,timeout=240)
        finally:
            server.should_exit=True
            thread.join(10)
            engine.dispose()


if __name__=="__main__":
    main()
