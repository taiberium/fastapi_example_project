from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.entities import (  # noqa: F401  registers tables on SQLModel.metadata
    membership,
    person,
    user,
)
from app.main import create_app
from app.outbound.persistence.db.db import get_db
from app.outbound.queue.queue import get_job_queue
from tests.fakes import FakeJobQueue


def _make_test_sessionmaker() -> sessionmaker:
    # Fresh in-memory SQLite (shared via StaticPool), tables created.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(bind=engine)
    return sessionmaker(
        bind=engine, class_=Session, autoflush=False, expire_on_commit=False
    )


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    session = _make_test_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def fake_queue() -> FakeJobQueue:
    # Shared fake so tests can assert what the app enqueued.
    return FakeJobQueue()


@pytest.fixture()
def client(fake_queue: FakeJobQueue) -> Generator[TestClient, None, None]:
    app = create_app()
    test_sessionmaker = _make_test_sessionmaker()

    def override_get_db() -> Generator[Session, None, None]:
        db = test_sessionmaker()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # No broker in tests: swap the Celery queue for a no-op fake.
    app.dependency_overrides[get_job_queue] = lambda: fake_queue
    with TestClient(app) as test_client:
        yield test_client
