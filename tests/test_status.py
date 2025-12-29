from sqlalchemy import select

from app.db.models import TaskStatusHistory
from tests.utils import register, login, create_task_form, change_status_form


def test_change_status_writes_history(client, db_session):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r = create_task_form(client, token, title="t1", priority="3")
    task_id = r.json()["id"]

    r = change_status_form(client, token, task_id, "in_progress")
    assert r.status_code == 200, r.text

    hist = db_session.execute(
        select(TaskStatusHistory).where(TaskStatusHistory.task_id == task_id)
    ).scalars().all()
    assert len(hist) >= 1

def test_change_status_invalid_code(client):
    register(client, "u1", "u1@test.com", "secret123")
    token = login(client, "u1@test.com", "secret123")

    r = create_task_form(client, token, title="t1", priority="3")
    task_id = r.json()["id"]

    r = change_status_form(client, token, task_id, "no_such_status")
    assert r.status_code in (400, 404)