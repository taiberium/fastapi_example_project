from fastapi.testclient import TestClient

FAKE_CLAIMS = {
    "sub": "google-123",
    "email": "alice@example.com",
    "email_verified": True,
    "name": "Alice",
}


def _login(client: TestClient, monkeypatch, claims=FAKE_CLAIMS) -> str:
    # Bypass the real Google network call — verify returns our fake claims.
    monkeypatch.setattr("app.core.security.verify_google_id_token", lambda token: claims)
    response = client.post("/auth/google", json={"id_token": "fake-google-token"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_google_login_issues_token(client: TestClient, monkeypatch) -> None:
    token = _login(client, monkeypatch)
    assert isinstance(token, str) and token


def test_invalid_google_token_is_rejected(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.core.security.verify_google_id_token", lambda token: None)
    response = client.post("/auth/google", json={"id_token": "bad"})
    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient, monkeypatch) -> None:
    token = _login(client, monkeypatch)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice"
    assert body["is_active"] is True


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_rejects_garbage_token(client: TestClient) -> None:
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


def test_repeated_login_reuses_same_user(client: TestClient, monkeypatch) -> None:
    token1 = _login(client, monkeypatch)
    token2 = _login(client, monkeypatch)
    me1 = client.get("/auth/me", headers={"Authorization": f"Bearer {token1}"}).json()
    me2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token2}"}).json()
    assert me1["id"] == me2["id"]


def test_login_rejected_when_email_unverified(client: TestClient, monkeypatch) -> None:
    claims = {**FAKE_CLAIMS, "email_verified": False}
    monkeypatch.setattr("app.core.security.verify_google_id_token", lambda token: claims)
    response = client.post("/auth/google", json={"id_token": "x"})
    assert response.status_code == 401


def test_login_rejected_when_email_missing(client: TestClient, monkeypatch) -> None:
    claims = {"sub": "google-1", "email_verified": True, "name": "NoEmail"}
    monkeypatch.setattr("app.core.security.verify_google_id_token", lambda token: claims)
    response = client.post("/auth/google", json={"id_token": "x"})
    assert response.status_code == 401


def test_me_rejects_token_with_non_numeric_sub(client: TestClient) -> None:
    # A token validly signed with our secret but carrying a non-numeric subject
    # must be a clean 401, not a 500 from int() blowing up.
    from app.core.security import create_access_token

    token = create_access_token(subject="not-an-int")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
