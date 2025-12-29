from tests.utils import register, login, auth_headers

def test_health_and_auth(client):
    r = client.get("/start")
    assert r.status_code == 200

    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r = client.get("/users/me", headers=auth_headers(token))
    assert r.status_code == 200