from datetime import date, timedelta

from sqlalchemy import select

from app.db.models import TaskStatus, Task, TaskStatusHistory
from tests.utils import register, login, auth_headers, create_task_form, create_topic_form, make_admin


def _mark_task_done(db_session, task_id: int, user_id: int):
    done = db_session.execute(select(TaskStatus).where(TaskStatus.code == "done")).scalar_one()
    task = db_session.get(Task, task_id)
    old_status = task.status_id

    task.status_id = done.id
    db_session.add(task)
    db_session.add(TaskStatusHistory(
        task_id=task_id,
        from_status_id=old_status,
        to_status_id=done.id,
        changed_by_id=user_id,
    ))
    db_session.commit()

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

def test_statuses_json_total_zero_when_no_tasks(client):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r = client.get("/analytics/statuses?format=json", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 0
    assert "items" in data

def test_topics_404_when_no_topics(client):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r = client.get("/analytics/topics?format=json", headers=auth_headers(token))
    assert r.status_code == 404

def test_topics_and_assignees_png_and_json(client, db_session):
    register(client, "admin", "admin@test.com", "secret123")
    make_admin(db_session, "admin@test.com")
    admin_token = login(client, "admin@test.com", "secret123")

    r = create_topic_form(client, admin_token, name="Backend", description="API")
    assert r.status_code == 201
    topic_id = r.json()["id"]

    register(client, "u1", "u1@test.com", "secret123")
    u1_token = login(client, "u1@test.com", "secret123")

    r = create_task_form(client, u1_token, title="t1", priority="3", topic_id=str(topic_id))
    assert r.status_code == 201
    task_id = r.json()["id"]

    r = client.get("/analytics/topics?format=json", headers=auth_headers(u1_token))
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = client.get("/analytics/topics?format=png", headers=auth_headers(u1_token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert len(r.content) > 1000

    r = client.get("/analytics/assignees?format=json", headers=auth_headers(u1_token))
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(x["assignee"] == "Без исполнителя" for x in items)

    r = client.get("/analytics/assignees?format=json&include_unassigned=false", headers=auth_headers(u1_token))
    assert r.status_code == 200

    r = client.get("/analytics/assignees?format=png", headers=auth_headers(u1_token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")


def test_summary_burndown_lead_time_json_and_png(client, db_session):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    # создаём 2 задачи: одну просрочим, одну закроем
    past = date.today() - timedelta(days=3)
    r1 = create_task_form(client, token, title="overdue", priority="3", due_date=str(past))
    r2 = create_task_form(client, token, title="done", priority="3")
    assert r1.status_code == 201 and r2.status_code == 201

    me = client.get("/users/me", headers=auth_headers(token)).json()
    user_id = me["id"]

    r = client.get("/analytics/lead_time?format=json", headers=auth_headers(token))
    assert r.status_code == 404

    _mark_task_done(db_session, r2.json()["id"], user_id)

    r = client.get("/analytics/summary", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert {"total", "open", "done", "overdue", "created_last_7_days"} <= set(data.keys())
    assert data["overdue"] >= 1

    r = client.get("/analytics/burndown?format=json", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    assert "items" in r.json()
    assert len(r.json()["items"]) >= 1

    r = client.get("/analytics/burndown?format=png", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")

    r = client.get("/analytics/lead_time?format=json", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    lt = r.json()
    assert lt["count"] >= 1
    assert lt["avg_hours"] >= 0

    r = client.get("/analytics/lead_time?format=png", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")