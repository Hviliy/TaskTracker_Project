from tests.utils import register, login, create_topic_form, auth_headers, make_admin

def test_topics_list_requires_auth(client):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r = client.get("/topics", headers=auth_headers(token))
    assert r.status_code == 200

def test_only_admin_can_create_topic(client, db_session):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r = create_topic_form(client, token, name="Backend", description="API")
    assert r.status_code == 403  # не админ

    make_admin(db_session, "u1@test.com")
    token2 = login(client, "u1@test.com", "secret123")

    r = create_topic_form(client, token2, name="Backend", description="API")
    assert r.status_code == 201, r.text

def test_topics_create_forbidden_for_user(client, db_session):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r = create_topic_form(client, token, name="Backend", description="API")
    assert r.status_code == 403

def test_topics_create_ok_for_admin(client, db_session):
    register(client, "u1", "u1@test.com", "secret123")
    make_admin(db_session, "u1@test.com")
    token = login(client, "u1@test.com", "secret123")

    r = create_topic_form(client, token, name="Backend", description="API")
    assert r.status_code in (200, 201), r.text

    r = client.get("/topics", headers=auth_headers(token))
    assert r.status_code == 200
    assert any(t["name"] == "Backend" for t in r.json())