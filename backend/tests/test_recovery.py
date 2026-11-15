import hashlib
import smtplib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from email import policy
from email.parser import BytesParser
from socketserver import StreamRequestHandler, TCPServer
from threading import Barrier, Thread
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException, Request
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.mailer import MailConfigurationError, MailSettings, send_account_email
from app.mail_worker import deliver_one
from app.models import AccountAction, Base, LoginSession, User
from app.recovery import PasswordReset, action_token, now, queue_action, reset_password
from test_accounts import headers, signup
from test_cards import api


@pytest.fixture
def email_config(monkeypatch):
    for key, value in {
        "SMTP_HOST": "smtp.example.test", "SMTP_PORT": "587", "SMTP_FROM": "noreply@example.test",
        "SMTP_SECURITY": "starttls", "SMTP_USERNAME": "", "SMTP_PASSWORD": "",
        "APP_PUBLIC_URL": "https://learn.example.test",
    }.items():
        monkeypatch.setenv(key, value)
    return MailSettings.load()


def queued_token(engine, purpose):
    with Session(engine) as db:
        action = db.scalar(select(AccountAction).where(AccountAction.purpose == purpose).order_by(AccountAction.available_at.desc()))
        token = action_token(action)
        assert action.token_digest == hashlib.sha256(token.encode()).hexdigest()
        assert token not in repr(action.__dict__)
        return token


def test_password_recovery_invalidates_sessions_and_other_links(api, email_config):
    client, engine = api
    signed_in = signup(client)
    first = client.post("/auth/forgot-password", json={"email": "ACCOUNT@example.com"})
    unknown = client.post("/auth/forgot-password", json={"email": "unknown@example.com"})
    assert first.status_code == unknown.status_code == 202
    assert first.json() == unknown.json() and "token" not in first.text
    first_token = queued_token(engine, "reset_password")
    assert client.post("/auth/forgot-password", json={"email": "account@example.com"}).status_code == 202
    second_token = queued_token(engine, "reset_password")
    assert first_token != second_token
    result = client.post("/auth/reset-password", json={"token": first_token, "new_password": "new-secure-pass"})
    assert result.status_code == 204
    assert client.get("/me", headers=headers(signed_in)).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": signed_in["refresh_token"]}).status_code == 401
    for token in (first_token, second_token):
        assert client.post("/auth/reset-password", json={"token": token, "new_password": "another-pass"}).status_code == 400
    assert client.post("/auth/login", json={"email": "account@example.com", "password": "original-pass"}).status_code == 401
    assert client.post("/auth/login", json={"email": "account@example.com", "password": "new-secure-pass"}).status_code == 200
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AccountAction)) == 2
        assert all(session.revoked for session in db.scalars(select(LoginSession).where(LoginSession.id == signed_in["session_id"])))


def test_verification_is_single_use_and_cannot_reset_password(api, email_config):
    client, engine = api
    owner = signup(client)
    assert not client.get("/me", headers=headers(owner)).json()["email_verified"]
    assert client.post("/auth/verification/request").status_code == 401
    assert client.post("/auth/verification/request", headers=headers(owner)).status_code == 202
    token = queued_token(engine, "verify_email")
    assert client.post("/auth/reset-password", json={"token": token, "new_password": "invalid-purpose"}).status_code == 400
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 204
    assert client.get("/me", headers=headers(owner)).json()["email_verified"] is True
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 400
    assert client.post("/auth/verification/request", headers=headers(owner)).status_code == 202
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AccountAction)) == 1


def test_recovery_expiry_password_change_rate_limit_and_configuration(api, email_config, monkeypatch):
    client, engine = api
    owner = signup(client)
    assert client.post("/auth/forgot-password", json={"email": "account@example.com"}).status_code == 202
    token = queued_token(engine, "reset_password")
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 400
    with Session(engine) as db:
        db.scalar(select(AccountAction)).expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert client.post("/auth/reset-password", json={"token": token, "new_password": "valid-password"}).status_code == 400
    assert client.post("/auth/forgot-password", json={"email": "account@example.com"}).status_code == 202
    token = queued_token(engine, "reset_password")
    assert client.post("/auth/reset-password", json={"token": token, "new_password": "é" * 37}).status_code == 422
    assert client.post("/auth/password", headers=headers(owner), json={"current_password": "original-pass", "new_password": "replacement-pass"}).status_code == 204
    assert client.post("/auth/reset-password", json={"token": token, "new_password": "valid-password"}).status_code == 400
    assert client.post("/auth/forgot-password", json={"email": "account@example.com"}).status_code == 202
    limited = client.post("/auth/forgot-password", json={"email": "ACCOUNT@example.com"})
    assert limited.status_code == 429 and "retry-after" in limited.headers
    monkeypatch.setenv("SMTP_HOST", "")
    assert client.post("/auth/forgot-password", json={"email": "missing@example.com"}).status_code == 503


def test_durable_email_retry_and_expired_or_invalidated_tokens(api, email_config, monkeypatch, caplog):
    client, engine = api
    owner = signup(client)
    client.post("/auth/forgot-password", json={"email": "account@example.com"})
    token = queued_token(engine, "reset_password")
    calls = []

    def unavailable(*args):
        calls.append(args)
        raise smtplib.SMTPException(f"Sensitive response containing {token}")

    monkeypatch.setattr("app.mail_worker.send_account_email", unavailable)
    sessions = sessionmaker(engine)
    assert deliver_one(sessions, email_config)
    assert token not in caplog.text and "account@example.com" not in caplog.text
    with Session(engine) as db:
        action = db.scalar(select(AccountAction))
        assert action.delivery_status == "pending" and action.delivery_attempts == 1
        assert action.available_at > now()
        action.available_at = now() - timedelta(seconds=1)
        db.commit()
    monkeypatch.setattr("app.mail_worker.send_account_email", lambda *args: calls.append(args))
    assert deliver_one(sessions, email_config)
    assert calls[-1][1:4] == ("account@example.com", "reset_password", token)
    assert not deliver_one(sessions, email_config)
    with Session(engine) as db:
        action = db.scalar(select(AccountAction))
        assert action.delivery_status == "sent" and action.delivery_attempts == 2
    client.post("/auth/verification/request", headers=headers(owner))
    client.post("/auth/logout-all", headers=headers(owner))
    assert not deliver_one(sessions, email_config)
    assert len(calls) == 2
    with Session(engine) as db:
        assert db.scalar(select(AccountAction).where(AccountAction.purpose == "verify_email")).delivery_status == "failed"


def test_worker_reclaims_crashed_delivery_and_stops_after_five_attempts(api, email_config, monkeypatch):
    client, engine = api
    signup(client)
    client.post("/auth/forgot-password", json={"email": "account@example.com"})
    with Session(engine) as db:
        action = db.scalar(select(AccountAction))
        action.delivery_status = "sending"
        action.lease_token = "old-worker"
        action.lease_until = now() - timedelta(seconds=1)
        action.delivery_attempts = 4
        db.commit()

    def unavailable(*args):
        raise OSError("offline")

    monkeypatch.setattr("app.mail_worker.send_account_email", unavailable)
    assert deliver_one(sessionmaker(engine), email_config)
    assert not deliver_one(sessionmaker(engine), email_config)
    with Session(engine) as db:
        action = db.scalar(select(AccountAction))
        assert action.delivery_status == "failed" and action.delivery_attempts == 5


def test_concurrent_password_resets_allow_only_one_password_change(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-with-at-least-32-bytes")
    engine = create_engine(f"sqlite:///{tmp_path / 'recovery.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="concurrent@example.test", password_hash="unused")
        db.add(user)
        db.flush()
        queue_action(db, user, "reset_password")
        queue_action(db, user, "reset_password")
        db.commit()
        tokens = [action_token(action) for action in db.scalars(select(AccountAction))]
    barrier = Barrier(2)

    def worker(token):
        with Session(engine) as db:
            barrier.wait(timeout=5)
            try:
                response = reset_password(
                    PasswordReset(token=token, new_password="replacement-password"), db,
                    Request({"type": "http", "client": ("127.0.0.1", 1234)}),
                )
                return response.status_code
            except HTTPException as error:
                return error.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(worker, tokens)) == [204, 400]
        with Session(engine) as db:
            assert db.scalar(select(User.token_version)) == 1
            assert all(action.consumed for action in db.scalars(select(AccountAction)))
    finally:
        engine.dispose()


def test_smtp_transport_to_local_capture_server(email_config):
    captured = []

    class SMTPHandler(StreamRequestHandler):
        def handle(self):
            self.wfile.write(b"220 local test SMTP\r\n")
            while line := self.rfile.readline():
                command = line.split(b" ", 1)[0].strip().upper()
                if command == b"DATA":
                    self.wfile.write(b"354 send message\r\n")
                    data = bytearray()
                    while (line := self.rfile.readline()) != b".\r\n":
                        if not line:
                            return
                        data.extend(line)
                    captured.append(BytesParser(policy=policy.default).parsebytes(bytes(data)))
                    self.wfile.write(b"250 accepted\r\n")
                elif command == b"QUIT":
                    self.wfile.write(b"221 bye\r\n")
                    return
                else:
                    self.wfile.write(b"250 ok\r\n")

    with TCPServer(("127.0.0.1", 0), SMTPHandler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        settings = MailSettings("127.0.0.1", server.server_address[1], email_config.sender, "plain", "", "", email_config.public_url)
        try:
            send_account_email(settings, "recipient@example.test", "reset_password", "test-token", "test-action")
        finally:
            server.shutdown()
            thread.join(timeout=3)
    assert len(captured) == 1
    message = captured[0]
    assert message["To"] == "recipient@example.test"
    link = next(line for line in message.get_content().splitlines() if line.startswith("https://"))
    url = urlsplit(link)
    assert url.netloc == "learn.example.test" and url.path == "/reset-password" and not url.query
    assert parse_qs(url.fragment) == {"token": ["test-token"]}


def test_smtp_starttls_precedes_login_and_delivery(email_config, monkeypatch):
    events = []

    class SMTP:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def starttls(self, context):
            assert context.check_hostname
            events.append("tls")
        def login(self, username, password):
            events.append("login")
        def send_message(self, message):
            events.append("send")
            return {}

    monkeypatch.setattr("app.mailer.smtplib.SMTP", SMTP)
    settings = MailSettings(email_config.host, 587, email_config.sender, "starttls", "user", "password", email_config.public_url)
    send_account_email(settings, "recipient@example.test", "verify_email", "test-token", "test-action")
    assert events == ["tls", "login", "send"]


@pytest.mark.parametrize("url", ["http://evil.example", "https://user:password@example.com", "https://example.com?next=evil", "javascript:alert(1)"])
def test_public_links_require_configured_secure_origin(email_config, monkeypatch, url):
    monkeypatch.setenv("APP_PUBLIC_URL", url)
    with pytest.raises(MailConfigurationError):
        MailSettings.load()
