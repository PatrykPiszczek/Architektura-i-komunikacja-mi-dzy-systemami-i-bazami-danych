def test_register_returns_user(client):
    response = client.post(
        "/auth/register",
        json={"email": "new@test.pl", "password": "secret1", "display_name": "New"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@test.pl"
    assert "password" not in body


def test_register_duplicate_email_conflicts(client):
    payload = {"email": "dup@test.pl", "password": "secret1", "display_name": "Dup"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409


def test_login_returns_token(client):
    client.post(
        "/auth/register",
        json={"email": "log@test.pl", "password": "secret1", "display_name": "Log"},
    )
    response = client.post("/auth/login", data={"username": "log@test.pl", "password": "secret1"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password_unauthorized(client):
    client.post(
        "/auth/register",
        json={"email": "wp@test.pl", "password": "secret1", "display_name": "WP"},
    )
    response = client.post("/auth/login", data={"username": "wp@test.pl", "password": "nope"})
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client, auth):
    response = client.get("/auth/me", headers=auth)
    assert response.status_code == 200
    assert response.json()["email"] == "user@test.pl"
