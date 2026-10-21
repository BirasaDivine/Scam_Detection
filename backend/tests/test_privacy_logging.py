"""Request bodies must never reach logs, console output or error messages."""

import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from app.engine import mock_engine
from app.scoring import Scorer
from tests.conftest import make_client

CANARY = "zqcanary7f3a9c"
BACKEND_DIR = Path(__file__).resolve().parent.parent


class LeakyScorer(Scorer):
    """Fails with the chat text in its message, as a careless library might."""

    def score_pieces(self, pieces):
        raise RuntimeError(f"could not score {pieces!r}")


def send_every_kind_of_request(client):
    chat = f"12/03/2024, 14:05 - Ann: {CANARY} pay the fee\n".encode()
    return [
        client.post("/analyze", json={"text": f"{CANARY} urgent", "source": "sms"}),
        client.post("/analyze", json={"text": f"{CANARY}", "source": "whatsapp"}),  # 400
        client.post("/analyze", json={"text": "hi", "source": CANARY}),  # 422
        client.post("/analyze", json={"text": "hi", "source": "sms", CANARY: 1}),  # 422
        client.post("/analyze", content=f'{{"text": "{CANARY}'.encode(),
                    headers={"Content-Type": "application/json"}),  # 400
        client.post("/analyze", content=CANARY.encode(), headers={"Content-Type": "text/plain"}),  # 415
        client.post("/analyze", files={"file": ("chat.txt", chat, "text/plain")}, data={"source": "whatsapp"}),
        client.post("/analyze", files={"file": (f"{CANARY}.pdf", chat, "text/plain")}, data={"source": "plain"}),
        client.post("/analyze", files={"file": ("chat.txt", chat * 50_000, "text/plain")},
                    data={"source": "plain"}),  # 413
        client.post("/analyze", json={"text": f"{CANARY}\n" * 2001, "source": "plain"}),  # 413
    ]


def test_request_bodies_never_reach_logs_or_error_messages(caplog, capfd):
    caplog.set_level(logging.DEBUG)
    for name in ("uvicorn", "uvicorn.error", "fastapi", "starlette", "scamguard"):
        logging.getLogger(name).setLevel(logging.DEBUG)

    responses = send_every_kind_of_request(make_client())
    leaky = make_client(mock_engine(LeakyScorer()))
    responses.append(leaky.post("/analyze", json={"text": f"{CANARY} hi", "source": "sms"}))

    assert {r.status_code for r in responses} >= {200, 400, 413, 415, 422, 500}
    for r in responses:
        assert CANARY not in r.text
    assert "analyze failed: RuntimeError" in caplog.text  # logging was captured at all
    assert CANARY not in caplog.text
    out, err = capfd.readouterr()
    assert CANARY not in out and CANARY not in err


def test_access_log_is_disabled():
    make_client()
    assert logging.getLogger("uvicorn.access").disabled


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_real_uvicorn_server_never_prints_request_bodies(tmp_path):
    port = _free_port()
    env = {**os.environ, "SCAMGUARD_MODEL_DIR": str(tmp_path), "PYTHONUNBUFFERED": "1"}
    # Deliberately without --no-access-log: the app must stay quiet on its own.
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "debug"],
        cwd=BACKEND_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                if httpx.get(f"{base}/health").status_code == 200:
                    break
            except httpx.TransportError:
                time.sleep(0.1)
        else:
            pytest.fail("server did not start")
        send_every_kind_of_request(httpx.Client(base_url=base, timeout=10))
    finally:
        proc.terminate()
        output = proc.communicate(timeout=10)[0].decode("utf-8", "replace")
    assert "Application startup complete" in output  # the log stream was captured
    assert CANARY not in output
    assert "POST /analyze" not in output  # access log is off
