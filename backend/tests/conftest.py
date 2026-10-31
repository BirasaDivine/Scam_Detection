import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# app.main builds an app on import; keep it off the local database file.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.config import Settings  # noqa: E402
from app.engine import mock_engine  # noqa: E402
from app.main import create_app  # noqa: E402

FRONTEND_ORIGIN = "http://localhost:5173"


ADMIN_TOKEN = "test-admin-token"


def make_client(engine=None, timeout_seconds: float = 5.0, store=None, admin_token: str = ADMIN_TOKEN) -> TestClient:
    settings = Settings(
        allowed_origins=[FRONTEND_ORIGIN],
        timeout_seconds=timeout_seconds,
        model_dir=Path("does-not-exist"),
        database_url="sqlite:///:memory:",
        admin_token=admin_token,
    )
    return TestClient(create_app(settings, engine or mock_engine(), store), raise_server_exceptions=False)


@pytest.fixture
def client() -> TestClient:
    return make_client()
