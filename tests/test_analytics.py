from tests.utils import register, login, auth_headers, create_task_form

def test_analytics_statuses_json(client):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    create_task_form(client, token, title="t1", priority="3")
    r = client.get("/analytics/statuses?format=json", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "total" in data
    assert "items" in data

def test_analytics_png(client):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    create_task_form(client, token, title="t1", priority="3")

    r = client.get("/analytics/statuses?format=png", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert len(r.content) > 1000