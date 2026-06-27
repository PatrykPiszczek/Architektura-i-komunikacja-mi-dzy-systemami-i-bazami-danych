import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test.db")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(client):
    client.post(
        "/auth/register",
        json={"email": "user@test.pl", "password": "secret1", "display_name": "Tester"},
    )
    token = client.post(
        "/auth/login",
        data={"username": "user@test.pl", "password": "secret1"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
