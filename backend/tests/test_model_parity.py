"""The real model, through the same code the API uses.

Runs the golden cases exported from the notebook: the masked text must be identical and the
score must match. Any difference moves scores and breaks the cut-offs.

Skipped when the model files are not in backend/model (golden_cases.json is not in git).
"""

import json
from pathlib import Path

import pytest

from app.bands import band_for
from app.engine import MODEL_FILES, load_engine, load_module
from tests.conftest import make_client

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
GOLDEN = MODEL_DIR / "golden_cases.json"
HAVE_FILES = GOLDEN.is_file() and all((MODEL_DIR / f).is_file() for f in MODEL_FILES)

pytestmark = pytest.mark.skipif(not HAVE_FILES, reason="model files or golden_cases.json not in backend/model")

CASES = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"] if HAVE_FILES else []
LEVELS = ("fpr_01", "fpr_05", "fpr_10")


@pytest.fixture(scope="module")
def engine():
    return load_engine(MODEL_DIR)


@pytest.fixture(scope="module")
def masking():
    return load_module(MODEL_DIR / "masking.py")


def rule_for(case) -> str:
    return "sms" if case["kind"] == "sms_like" else "dialogue"


def test_the_real_model_is_loaded_not_the_mock(engine):
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert not engine.mock
    assert engine.model_version == golden["model_version"]


def test_cutoffs_come_from_the_file_not_the_code(engine):
    raw = json.loads((MODEL_DIR / "cutoffs.json").read_text(encoding="utf-8"))
    for rule in ("sms", "dialogue"):
        for level in LEVELS:
            assert getattr(engine.cutoffs.for_rule(rule), level) == raw[rule][level]


def test_there_are_20_cases():
    assert len(CASES) == 20


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"case{c['id']}-{c['kind']}")
class TestGoldenCase:
    def test_masked_text_is_identical(self, case, masking):
        assert masking.mask_texts([case["raw"]])[0] == case["expected_masked"]

    def test_adapter_hands_the_model_the_same_masked_text(self, case, engine):
        assert engine.prepare([case["raw"]], rule_for(case)) == [case["expected_masked"]]

    def test_score_is_identical(self, case, engine):
        pieces = engine.prepare([case["raw"]], rule_for(case))
        assert engine.scorer.score_pieces(pieces)[0] == pytest.approx(case["expected_score"], abs=1e-6)

    def test_verdict_at_every_cutoff_level(self, case, engine):
        score = case["expected_score"]
        for rule_key, rule in (("sms_rule", "sms"), ("dialogue_rule", "dialogue")):
            for level in LEVELS:
                expected = case["expected_verdict"][rule_key][level]
                got = "scam" if score > getattr(engine.cutoffs.for_rule(rule), level) else "not_scam"
                assert got == expected, (rule, level)

    def test_api_returns_the_band_for_the_golden_score(self, case, engine):
        source = "sms" if case["kind"] == "sms_like" else "plain"
        body = make_client(engine).post("/analyze", json={"text": case["raw"], "source": source}).json()
        verdict, band = band_for(case["expected_score"], engine.cutoffs.for_rule(rule_for(case)))
        assert (body["verdict"], body["band"]) == (verdict, band)
        assert body["pieces_scored"] == 1
        assert body["model_version"] == engine.model_version


def words(n: int) -> str:
    return " ".join(f"word{i}" for i in range(n))


@pytest.mark.parametrize(
    "n_words, pieces",
    [(9, None), (10, 1), (45, 1), (46, 1), (54, 1), (55, 2), (90, 2), (99, 2), (100, 3)],
)
def test_chat_pieces_follow_the_notebook_chunking(engine, n_words, pieces):
    # A leftover under 10 words is dropped, as in training: 46 to 54 words give 1 piece, 99 give 2 (45+45+9)
    out = engine.prepare([words(n_words)], "dialogue")
    assert len(out) == (pieces or 0)


def test_chunking_happens_before_masking(engine):
    # "RWF 500,000" is two words before masking and one after. Chunking the masked text
    # would cut in a different place from training.
    text = " ".join(["RWF 500,000"] * 30)  # 60 words raw
    assert len(engine.prepare([text], "dialogue")) == 2  # 45 + 15 raw words


def test_short_single_sms_is_scored_but_short_chat_is_refused(engine):
    client = make_client(engine)
    sms = client.post("/analyze", json={"text": "Send your PIN now", "source": "sms"})
    chat = client.post("/analyze", json={"text": "Send your PIN now", "source": "plain"})
    assert sms.status_code == 200 and sms.json()["pieces_scored"] == 1
    assert chat.status_code == 400 and "too short" in chat.json()["detail"]


def test_whatsapp_export_end_to_end_keeps_sender_names_out(engine):
    chat = "\n".join(
        f"12/03/2024, 14:{i:02d} - Zxqvlorn Mbeki: " + words(12) for i in range(10)
    )  # 120 words, one sender
    seen = []
    real = engine.scorer.score_pieces
    engine.scorer.score_pieces = lambda pieces: (seen.extend(pieces), real(pieces))[1]
    try:
        r = make_client(engine).post("/analyze", json={"text": chat, "source": "whatsapp"})
    finally:
        engine.scorer.score_pieces = real
    assert r.status_code == 200 and r.json()["source_rule"] == "dialogue"
    assert r.json()["pieces_scored"] == 3
    assert seen and all("Zxqvlorn" not in p and "Mbeki" not in p for p in seen)
