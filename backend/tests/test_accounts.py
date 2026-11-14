from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.orm import Session

from app.models import LoginSession

from test_cards import api


def signup(client, email="account@example.com"):
    response = client.post("/auth/register", json={"email": email, "password": "original-pass"})
    assert response.status_code == 201
    return response.json()


def headers(token):
    return {"Authorization": f"Bearer {token['access_token']}"}


def test_refresh_rotation_replay_and_other_sessions(api):
    client, _ = api
    first = signup(client)
    other = client.post("/auth/login", json={
        "email": "account@example.com", "password": "original-pass",
    }).json()
    rotated = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200
    second = rotated.json()
    assert second["session_id"] == first["session_id"]
    assert second["refresh_token"] != first["refresh_token"]
    assert client.get("/me", headers=headers(second)).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
    assert client.get("/me", headers=headers(second)).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]}).status_code == 401
    assert client.get("/me", headers=headers(other)).status_code == 200


def test_profile_preferences_and_session_revocation(api):
    client, _ = api
    first = signup(client)
    other = signup(client, "other@example.com")
    profile = client.patch("/me", headers=headers(first), json={
        "display_name": "Minh", "timezone_name": "Asia/Tokyo", "cefr_level": "B1", "daily_goal": 25,
    })
    assert profile.status_code == 200
    assert "password_hash" not in profile.json()
    assert client.get("/progress", headers=headers(first)).json()["timezone"] == "Asia/Tokyo"
    assert client.post("/sessions", headers=headers(first), json={}).json()["cefr_level"] == "B1"
    assert client.patch("/me", headers=headers(first), json={"timezone_name": "unknown"}).status_code == 422
    assert client.patch("/me", headers=headers(first), json={"daily_goal": None}).status_code == 422
    sessions = client.get("/auth/sessions", headers=headers(first)).json()
    assert [session["id"] for session in sessions] == [first["session_id"]]
    assert client.delete(f"/auth/sessions/{first['session_id']}", headers=headers(other)).status_code == 404
    assert client.delete(f"/auth/sessions/{first['session_id']}", headers=headers(first)).status_code == 204
    assert client.get("/me", headers=headers(first)).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401


def test_password_change_revokes_sessions_and_legacy_tokens(api):
    client, _ = api
    token = signup(client)
    user_id = client.get("/me", headers=headers(token)).json()["id"]
    legacy = jwt.encode({
        "sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }, "test-secret-with-at-least-32-bytes", algorithm="HS256")
    legacy_headers = {"Authorization": f"Bearer {legacy}"}
    assert client.get("/me", headers=legacy_headers).status_code == 200
    assert client.post("/auth/password", headers=headers(token), json={
        "current_password": "incorrect", "new_password": "replacement-pass",
    }).status_code == 401
    assert client.post("/auth/password", headers=headers(token), json={
        "current_password": "original-pass", "new_password": "replacement-pass",
    }).status_code == 204
    assert client.get("/me", headers=headers(token)).status_code == 401
    assert client.get("/me", headers=legacy_headers).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": token["refresh_token"]}).status_code == 401
    assert client.post("/auth/login", json={
        "email": "account@example.com", "password": "original-pass",
    }).status_code == 401
    renewed = client.post("/auth/login", json={
        "email": "account@example.com", "password": "replacement-pass",
    })
    assert renewed.status_code == 200
    assert client.post("/auth/logout-all", headers=headers(renewed.json())).status_code == 204
    assert client.get("/me", headers=headers(renewed.json())).status_code == 401


def test_expired_refresh_cannot_extend_session(api):
    client, engine = api
    token = signup(client)
    with Session(engine) as db:
        session = db.get(LoginSession, token["session_id"])
        assert session.refresh_digest != token["refresh_token"]
        assert len(session.refresh_digest) == 64
        session.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
        db.commit()
    assert client.post("/auth/refresh", json={"refresh_token": token["refresh_token"]}).status_code == 401
    assert client.get("/me", headers=headers(token)).status_code == 401
