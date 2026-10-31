import sqlite3

import pytest

from app.insights import build_stats, recommend
from app.stats import StatsStore
from tests.conftest import ADMIN_TOKEN, make_client

SCAM_SMS = {"text": "Urgent: pay the fee to verify your PIN", "source": "sms"}
SAFE_SMS = {"text": "see you at lunch", "source": "sms"}
AUTH = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def stats(client):
    r = client.get("/stats", headers=AUTH)
    assert r.status_code == 200
    return r.json()


def test_each_successful_check_is_counted_by_verdict_and_format(client):
    client.post("/analyze", json=SCAM_SMS)
    client.post("/analyze", json=SCAM_SMS)
    client.post("/analyze", json=SAFE_SMS)
    client.post("/analyze", json={"text": "see you at lunch", "source": "plain"})
    body = stats(client)
    assert (body["total"], body["scam"], body["not_scam"]) == (4, 2, 2)
    assert body["by_input_format"]["sms"] == {"scam": 2, "not_scam": 1}
    assert body["by_input_format"]["plain"] == {"scam": 0, "not_scam": 1}
    assert body["by_input_format"]["whatsapp"] == {"scam": 0, "not_scam": 0}
    assert body["scam_origin_unreported"] == 2


def test_failed_checks_are_not_counted(client):
    client.post("/analyze", json={"text": "", "source": "plain"})
    client.post("/analyze", json={"text": "hi", "source": "whatsapp"})
    assert stats(client)["total"] == 0


def test_origin_can_be_added_once_to_a_scam(client):
    record_id = client.post("/analyze", json=SCAM_SMS).json()["record_id"]
    r = client.post(f"/checks/{record_id}/origin", json={"origin": "whatsapp"})
    assert r.status_code == 204
    again = client.post(f"/checks/{record_id}/origin", json={"origin": "email"})
    assert again.status_code == 409
    body = stats(client)
    assert body["scam_origins"]["whatsapp"] == 1
    assert body["scam_origins"]["email"] == 0
    assert body["scam_origin_unreported"] == 0


def test_origin_is_refused_for_a_not_scam_check(client):
    record_id = client.post("/analyze", json=SAFE_SMS).json()["record_id"]
    assert client.post(f"/checks/{record_id}/origin", json={"origin": "sms"}).status_code == 409


def test_origin_for_unknown_check_is_404(client):
    assert client.post("/checks/nope/origin", json={"origin": "sms"}).status_code == 404


@pytest.mark.parametrize("body", [{"origin": "carrier_pigeon"}, {}, {"origin": "sms", "text": "hi"}])
def test_bad_origin_body_is_422(client, body):
    record_id = client.post("/analyze", json=SCAM_SMS).json()["record_id"]
    assert client.post(f"/checks/{record_id}/origin", json=body).status_code == 422


def test_stats_need_the_admin_token(client):
    assert client.get("/stats").status_code == 401
    assert client.get("/stats", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_stats_are_off_without_an_admin_token():
    assert make_client(admin_token="").get("/stats", headers=AUTH).status_code == 404


class BrokenStore(StatsStore):
    def __init__(self):
        super().__init__("sqlite:///:memory:")

    def record(self, verdict, input_format):
        raise sqlite3.OperationalError("disk full")


def test_verdict_is_returned_when_the_store_fails():
    r = make_client(store=BrokenStore()).post("/analyze", json=SCAM_SMS)
    assert r.status_code == 200
    assert r.json()["verdict"] == "scam" and r.json()["record_id"] is None


def test_store_keeps_no_chat_text():
    store = StatsStore("sqlite:///:memory:")
    client = make_client(store=store)
    canary = "zqcanary7f3a9c"
    client.post("/analyze", json={"text": f"{canary} pay the fee to verify your pin", "source": "sms"})
    rows = store._sqlite.execute("SELECT * FROM checks").fetchall()
    assert len(rows) == 1
    assert canary not in repr(rows)
    assert set(rows[0][2:]) <= {"scam", "sms", None}


def test_sqlite_file_keeps_counts_between_restarts(tmp_path):
    url = f"sqlite:///{tmp_path / 'sub' / 'stats.db'}"
    StatsStore(url).record("scam", "whatsapp")
    assert StatsStore(url).counts() == [("scam", "whatsapp", None, 1)]


def test_recommendation_needs_enough_checks():
    assert recommend(4, 4, {"whatsapp": 4}) == ["Not enough checks yet for a recommendation."]


def test_recommendation_waits_for_enough_reported_origins():
    tips = recommend(10, 4, {"whatsapp": 4, "sms": 0})
    assert tips[0] == "40% of checks were scams (4 of 10)."
    assert "Not enough scam sources" in tips[1]


def test_recommendation_names_the_main_channel():
    rows = [("scam", "whatsapp", "whatsapp", 3), ("scam", "sms", "sms", 2), ("not_scam", "plain", None, 5)]
    tips = build_stats(rows).recommendations
    assert tips[0] == "50% of checks were scams (5 of 10)."
    assert tips[1].startswith("Most reported scams came from WhatsApp (60%).")


def test_recommendation_when_no_channel_stands_out():
    origins = {"whatsapp": 1, "sms": 1, "telegram": 1, "email": 1, "facebook": 1, "other": 1}
    assert "No single channel stands out" in recommend(10, 6, origins)[1]


def test_cors_allows_the_authorization_header(client):
    r = client.options("/stats", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    assert r.status_code == 200

