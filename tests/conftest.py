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
def client() -> Generator[TestClient, None, None]:
    # Point the transaction middleware at an in-memory DB; it owns the per-request
    # session/commit, so there is nothing else to override.
    app = create_app()
    app.state.db_sessionmaker = _make_test_sessionmaker()
    with TestClient(app) as test_client:
        yield test_client
