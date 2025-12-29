import pytest

from app.api import deps

class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_get_db_commits_and_closes(monkeypatch):
    fake = FakeSession()

    monkeypatch.setattr(deps, "SessionLocal", lambda: fake)

    gen = deps.get_db()
    s = next(gen)
    assert s is fake

    with pytest.raises(StopIteration):
        next(gen)

    assert fake.committed is True
    assert fake.closed is True
    assert fake.rolled_back is False


def test_get_db_rollbacks_on_exception(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(deps, "SessionLocal", lambda: fake)

    gen = deps.get_db()
    next(gen)

    with pytest.raises(ValueError):
        gen.throw(ValueError("boom"))

    assert fake.rolled_back is True
    assert fake.closed is True