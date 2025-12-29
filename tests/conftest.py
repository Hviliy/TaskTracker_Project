import os
import pytest
import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db
from app.db.base import Base
from app.db.models import TaskStatus

load_dotenv()

# создание тестовой бд
def _ensure_database_exists(db_url: str) -> None:
    url = make_url(db_url)
    db_name = url.database

    conn = psycopg2.connect(
        dbname="postgres",
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port or 5432,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db_name,))
        if cur.fetchone() is None:
            cur.execute(f'CREATE DATABASE "{db_name}"')
    conn.close()

def _seed_statuses(session) -> None:
    exists = session.execute(select(TaskStatus)).first()
    if exists:
        return
    session.add_all([
        TaskStatus(code="new", name="Новая", sort_order=10, is_terminal=False),
        TaskStatus(code="in_progress", name="В работе", sort_order=20, is_terminal=False),
        TaskStatus(code="review", name="На проверке", sort_order=30, is_terminal=False),
        TaskStatus(code="done", name="Сделано", sort_order=40, is_terminal=True),
    ])
    session.commit()

@pytest.fixture(scope="session")
def test_engine():
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        raise RuntimeError("TEST_DATABASE_URL is not set")

    _ensure_database_exists(test_db_url)

    engine = create_engine(test_db_url, pool_pre_ping=True)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def db_session(test_engine):
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

@pytest.fixture()
def client(db_session):
    _seed_statuses(db_session)

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def _clean_db(db_session):
    db_session.execute(text("TRUNCATE TABLE task_status_history RESTART IDENTITY CASCADE;"))
    db_session.execute(text("TRUNCATE TABLE tasks RESTART IDENTITY CASCADE;"))
    db_session.execute(text("TRUNCATE TABLE topics RESTART IDENTITY CASCADE;"))
    db_session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;"))
    db_session.commit()
    yield