from sqlalchemy import update
from app.db.models import User, UserRole

def register(client, name: str, email: str, password: str):
    r = client.post(
        "/auth/register",
        data={"name": name, "email": email, "password": password},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()

def login(client, email: str, password: str) -> str:
    r = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def make_admin(db_session, email: str):
    db_session.execute(update(User).where(User.email == email).values(role=UserRole.admin))
    db_session.commit()

def create_task_form(client, token: str, **fields):
    r = client.post("/tasks", data=fields, headers={"Authorization": f"Bearer {token}"})
    return r

def patch_task_form(client, token: str, task_id: int, **fields):
    r = client.patch(f"/tasks/{task_id}", data=fields, headers={"Authorization": f"Bearer {token}"})
    return r

def change_status_form(client, token: str, task_id: int, status_code: str):
    r = client.patch(
        f"/tasks/{task_id}/status",
        data={"status_code": status_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    return r

def create_topic_form(client, token: str, **fields):
    r = client.post("/topics", data=fields, headers={"Authorization": f"Bearer {token}"})
    return r