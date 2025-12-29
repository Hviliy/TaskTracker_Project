from tests.utils import register, login, auth_headers, make_admin

def test_admin_can_change_role(client, db_session):
    register(client, "admin", "admin@test.com", "secret123")
    register(client, "u1", "u1@test.com", "secret123")

    make_admin(db_session, "admin@test.com")
    admin_token = login(client, "admin@test.com", "secret123")

    r = client.get("/users", headers=auth_headers(admin_token))
    assert r.status_code == 200
    users = r.json()
    u1_id = [u["id"] for u in users if u["email"] == "u1@test.com"][0]

    r = client.patch(f"/users/{u1_id}/role", data={"role": "admin"}, headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["role"] == "admin"