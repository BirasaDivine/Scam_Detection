import time

import pytest
from pydantic import ValidationError

from app.config import MAX_FILE_BYTES
from app.engine import mock_engine
from app.schemas import AnalyzeResponse
from app.scoring import Scorer
from tests.conftest import FRONTEND_ORIGIN, make_client

RESPONSE_KEYS = {"verdict", "band", "pieces_scored", "source_rule", "model_version", "disclaimer"}
DISCLAIMER = (
    "This is a research demonstration. It has not been validated for use in Africa, "
    "and it can be wrong."
)
CHAT = b"12/03/2024, 14:05 - Ann: Your account is blocked\n12/03/2024, 14:06 - Bo: ok\n"


def upload(client, data=CHAT, name="chat.txt", source="whatsapp", content_type="text/plain"):
    return client.post("/analyze", files={"file": (name, data, content_type)}, data={"source": source})


# Health and the happy paths

def test_health_reports_mock_mode(client):
    assert client.get("/health").json() == {"status": "ok", "model_version": "mock-0", "mock": True}


def test_json_text_returns_exactly_the_contract(client):
    r = client.post("/analyze", json={"text": "Urgent: pay the fee to verify your PIN", "source": "sms"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == RESPONSE_KEYS
    assert body == {
        "verdict": "scam", "band": "high", "pieces_scored": 1, "source_rule": "sms",
        "model_version": "mock-0", "disclaimer": DISCLAIMER,
    }


def test_file_upload_returns_exactly_the_contract(client):
    r = upload(client)
    assert r.status_code == 200
    assert set(r.json()) == RESPONSE_KEYS
    assert r.json()["source_rule"] == "dialogue"


@pytest.mark.parametrize(
    "text, verdict, band",
    [
        ("pay the fee to verify your pin", "scam", "high"),
        ("pay the fee to verify", "scam", "medium"),
        ("pay the fee", "not_scam", "borderline"),
        ("see you at lunch", "not_scam", "low"),
    ],
)
def test_mock_mode_can_show_every_band(client, text, verdict, band):
    body = client.post("/analyze", json={"text": text, "source": "sms"}).json()
    assert (body["verdict"], body["band"]) == (verdict, band)


def test_utf16_file_is_read(client):
    assert upload(client, data=CHAT.decode().encode("utf-16")).status_code == 200


# Schema

def test_response_model_forbids_extra_fields():
    good = dict(verdict="scam", band="high", pieces_scored=1, source_rule="sms",
                model_version="m", disclaimer="d")
    AnalyzeResponse(**good)
    with pytest.raises(ValidationError):
        AnalyzeResponse(**good, reasons=[])
    assert AnalyzeResponse.model_json_schema()["additionalProperties"] is False


def test_json_request_forbids_extra_fields(client):
    r = client.post("/analyze", json={"text": "hi", "source": "sms", "consent_to_store": True})
    assert r.status_code == 422


# 400

@pytest.mark.parametrize("text", ["", "   \n\t "])
def test_empty_text_is_400(client, text):
    r = client.post("/analyze", json={"text": text, "source": "plain"})
    assert r.status_code == 400 and r.json()["detail"].startswith("The chat is empty")


def test_plain_text_sent_as_whatsapp_is_400(client):
    r = client.post("/analyze", json={"text": "just a note", "source": "whatsapp"})
    assert r.status_code == 400 and "WhatsApp export" in r.json()["detail"]


def test_export_with_only_system_lines_is_400(client):
    r = upload(client, data=b"12/03/2024, 14:00 - Messages and calls are end-to-end encrypted.")
    assert r.status_code == 400 and r.json()["detail"] == "We found no messages to check in this chat."


def test_malformed_json_is_400(client):
    r = client.post("/analyze", content=b'{"text": "hi", ', headers={"Content-Type": "application/json"})
    assert r.status_code == 400


def test_undecodable_file_is_400(client):
    r = upload(client, data=b"\x80\x81\x82 not text")
    assert r.status_code == 400 and "UTF-8" in r.json()["detail"]


# 413

def test_file_at_exactly_1_mb_is_accepted(client):
    assert upload(client, data=b"a" * MAX_FILE_BYTES, source="plain").status_code == 200


def test_file_over_1_mb_is_413(client):
    r = upload(client, data=b"a" * (MAX_FILE_BYTES + 1), source="plain")
    assert r.status_code == 413 and "1 MB" in r.json()["detail"]


def test_much_larger_file_is_refused_before_parsing(client):
    assert upload(client, data=b"a" * (5 * MAX_FILE_BYTES), source="plain").status_code == 413


@pytest.mark.parametrize("extra", [1, 3 * MAX_FILE_BYTES])
def test_text_over_1_mb_is_413(client, extra):
    r = client.post("/analyze", json={"text": "a" * (MAX_FILE_BYTES + extra), "source": "plain"})
    assert r.status_code == 413 and "1 MB" in r.json()["detail"]


def test_2000_messages_are_accepted_and_2001_are_413(client):
    ok = client.post("/analyze", json={"text": "hi\n" * 2000, "source": "plain"})
    too_many = client.post("/analyze", json={"text": "hi\n" * 2001, "source": "plain"})
    assert ok.status_code == 200
    assert too_many.status_code == 413 and "2,000 messages" in too_many.json()["detail"]


# 415

@pytest.mark.parametrize("name", ["chat.pdf", "chat.txt.exe", "chat", "chat.zip"])
def test_non_txt_file_name_is_415(client, name):
    r = upload(client, name=name)
    assert r.status_code == 415 and r.json()["detail"] == "Only .txt files are supported."


def test_txt_name_with_wrong_content_type_is_415(client):
    assert upload(client, content_type="application/pdf").status_code == 415


def test_unsupported_request_content_type_is_415(client):
    r = client.post("/analyze", content=b"<chat/>", headers={"Content-Type": "application/xml"})
    assert r.status_code == 415


# 422

@pytest.mark.parametrize(
    "payload",
    [{"text": "hi", "source": "email"}, {"text": "hi"}, {"source": "sms"}, {"text": 5, "source": "sms"}],
)
def test_invalid_json_fields_are_422(client, payload):
    r = client.post("/analyze", json=payload)
    assert r.status_code == 422 and r.json()["detail"].startswith("Some details are missing")


def test_upload_with_bad_source_is_422(client):
    assert upload(client, source="email").status_code == 422


def test_upload_without_file_is_422(client):
    r = client.post("/analyze", data={"source": "plain"}, files={"other": ("x.txt", b"hi")})
    assert r.status_code == 422


# Timeout

class SlowScorer(Scorer):
    def score_pieces(self, pieces):
        time.sleep(1.0)
        return [0.0 for _ in pieces]


def test_slow_analysis_times_out_with_504():
    # Kept open so TestClient does not shut its event loop (and wait for the thread) per request
    with make_client(mock_engine(SlowScorer()), timeout_seconds=0.1) as client:
        started = time.monotonic()
        r = client.post("/analyze", json={"text": "hi", "source": "sms"})
        elapsed = time.monotonic() - started
    assert r.status_code == 504 and "too long" in r.json()["detail"]
    assert elapsed < 0.9  # answered without waiting for the scorer


# CORS

def test_cors_allows_only_the_configured_origin(client):
    def preflight(origin):
        return client.options("/analyze", headers={
            "Origin": origin, "Access-Control-Request-Method": "POST",
        })

    assert preflight(FRONTEND_ORIGIN).headers.get("access-control-allow-origin") == FRONTEND_ORIGIN
    assert "access-control-allow-origin" not in preflight("https://evil.example").headers
