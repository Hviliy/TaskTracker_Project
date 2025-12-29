from tests.utils import register, login, auth_headers

def test_unauthorized_requests_are_blocked(client):
    r = client.get("/tasks")
    assert r.status_code == 401

def test_invalid_token_blocked(client):
    r = client.get("/tasks", headers={"Authorization": "Bearer bad.token"})
    assert r.status_code == 401

def test_me_endpoint(client):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")
    r = client.get("/users/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["email"] == "u1@test.com"

def test_register_duplicate_email(client):
    register(client, "u1", "u1@test.com", "secret123")
    r = client.post("/auth/register", data={"name": "u2", "email": "u1@test.com", "password": "secret123"})
    assert r.status_code == 400

def test_login_wrong_password(client):
    register(client, "u1", "u1@test.com", "secret123")
    r = client.post(
        "/auth/login",
        data={"username": "u1@test.com", "password": "badpass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code in (400, 401)