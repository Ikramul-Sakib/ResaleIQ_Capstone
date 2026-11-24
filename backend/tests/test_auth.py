from conftest import ADMIN, auth, register


def test_register_login_and_me(client):
    token = register(client)
    me = client.get("/api/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "user@test.local"
    assert me.get_json()["user"]["role"] == "user"

    login = client.post("/api/auth/login", json={"email": "USER@test.local", "password": "Secret123"})
    assert login.status_code == 200


def test_register_validates_fields(client):
    response = client.post("/api/auth/register", json={"name": "A", "email": "nope", "password": "short"})
    assert response.status_code == 422
    fields = response.get_json()["error"]["fields"]
    assert set(fields) == {"name", "email", "password"}


def test_duplicate_email_rejected(client):
    register(client)
    response = client.post(
        "/api/auth/register", json={"name": "Other", "email": "user@test.local", "password": "Secret123"}
    )
    assert response.status_code == 409


def test_wrong_password_and_missing_token(client):
    register(client)
    assert client.post("/api/auth/login", json={"email": "user@test.local", "password": "bad"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth("garbage")).status_code == 401


def test_admin_is_seeded(client):
    response = client.post("/api/auth/login", json=ADMIN)
    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "admin"


def test_password_reset_flow(client):
    register(client)
    response = client.post("/api/auth/forgot-password", json={"email": "user@test.local"})
    link = response.get_json()["dev_reset_link"]
    token = link.split("token=")[1]
    reset = client.post("/api/auth/reset-password", json={"token": token, "password": "NewPass456"})
    assert reset.status_code == 200
    assert client.post("/api/auth/login", json={"email": "user@test.local", "password": "NewPass456"}).status_code == 200
    # token can't be reused
    again = client.post("/api/auth/reset-password", json={"token": token, "password": "Another789"})
    assert again.status_code == 400


def test_forgot_password_does_not_reveal_accounts(client):
    response = client.post("/api/auth/forgot-password", json={"email": "nobody@test.local"})
    assert response.status_code == 200
    assert "dev_reset_link" not in response.get_json()


def test_password_change_invalidates_old_token(client):
    token = register(client)
    response = client.put(
        "/api/users/me/password",
        json={"current_password": "Secret123", "new_password": "Changed123"},
        headers=auth(token),
    )
    assert response.status_code == 200
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401
    assert client.get("/api/auth/me", headers=auth(response.get_json()["token"])).status_code == 200


def test_profile_update(client):
    token = register(client)
    response = client.put(
        "/api/users/me", json={"name": "New Name", "location": "Khulna", "phone": "017"}, headers=auth(token)
    )
    assert response.status_code == 200
    assert response.get_json()["user"]["location"] == "Khulna"
