from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.engine import mock_engine
from app.main import create_app

FRONTEND_ORIGIN = "http://localhost:5173"


def make_client(engine=None, timeout_seconds: float = 5.0) -> TestClient:
    settings = Settings(
        allowed_origins=[FRONTEND_ORIGIN],
        timeout_seconds=timeout_seconds,
        model_dir=Path("does-not-exist"),
    )
    return TestClient(create_app(settings, engine or mock_engine()), raise_server_exceptions=False)


@pytest.fixture
def client() -> TestClient:
    return make_client()
