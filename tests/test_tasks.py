from tests.utils import register, login, auth_headers, create_task_form, patch_task_form, change_status_form


def test_user_can_crud_own_task(client):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r = create_task_form(client, token, title="t1", description="d1", priority="3")
    assert r.status_code == 201, r.text
    task_id = r.json()["id"]

    r = client.get(f"/tasks/{task_id}", headers=auth_headers(token))
    assert r.status_code == 200

    r = patch_task_form(client, token, task_id, title="t1-upd")
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "t1-upd"

    r = client.delete(f"/tasks/{task_id}", headers=auth_headers(token))
    assert r.status_code == 204

def test_user_cannot_edit_foreign_task(client):
    register(client, "u1", "u1@test.com", "secret123")
    register(client, "u2", "u2@test.com", "secret123")

    t1 = login(client, "u1@test.com", "secret123")
    t2 = login(client, "u2@test.com", "secret123")

    r = create_task_form(client, t1, title="t1", priority="3")
    task_id = r.json()["id"]

    r = patch_task_form(client, t2, task_id, title="hack")
    assert r.status_code == 403

def test_list_tasks_sort_and_filter(client):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r1 = create_task_form(client, token, title="b-task", priority="2")
    r2 = create_task_form(client, token, title="a-task", priority="5")
    id1 = r1.json()["id"]
    id2 = r2.json()["id"]

    change_status_form(client, token, id1, "in_progress")

    r = client.get("/tasks?sort_by=title&sort_dir=asc", headers=auth_headers(token))
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert titles == sorted(titles)

    r = client.get("/tasks?assignee_id=99999", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json() == []

    r = client.get(f"/tasks/{id1}", headers=auth_headers(token))
    status_id = r.json()["status_id"]

    r = client.get(f"/tasks?status_id={status_id}", headers=auth_headers(token))
    assert r.status_code == 200
    assert all(t["status_id"] == status_id for t in r.json())

    r = client.get(f"/tasks/{id2}", headers=auth_headers(token))
    assert r.status_code == 200