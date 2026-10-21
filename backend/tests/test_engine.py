import hashlib
import json

import pytest

from app.cutoffs import CutoffsFile, load_cutoffs
from app.engine import MODEL_FILES, Engine, load_engine, mock_engine, model_version_for
from app.model_stubs import chunk
from app.pipeline import analyze_text
from app.scoring import MockScorer, Scorer

RULE = {"fpr_01": 1.0, "fpr_05": 0.0, "fpr_10": -0.5}  # fixture values, not model cut-offs


def test_empty_model_dir_starts_in_mock_mode(tmp_path):
    engine = load_engine(tmp_path)
    assert engine.mock and engine.model_version == "mock-0"
    assert isinstance(engine.scorer, MockScorer)


def test_any_missing_file_starts_in_mock_mode(tmp_path):
    for name in MODEL_FILES[1:]:
        (tmp_path / name).write_text("x")
    assert load_engine(tmp_path).mock


def test_all_files_present_fails_loudly_until_wired(tmp_path):
    for name in MODEL_FILES:
        (tmp_path / name).write_text("x")
    with pytest.raises(RuntimeError):
        load_engine(tmp_path)


def test_cutoffs_file_shape(tmp_path):
    path = tmp_path / "cutoffs.json"
    path.write_text(json.dumps({
        "model_version": "v-test", "trained_on": "standard split, seed 42",
        "sms": RULE, "dialogue": RULE,
    }))
    cutoffs = load_cutoffs(path)
    assert cutoffs.for_rule("sms").fpr_01 == 1.0 and cutoffs.trained_on.startswith("standard")


def test_model_version_prefers_cutoffs_field(tmp_path):
    joblib_path = tmp_path / "svm_plain.joblib"
    joblib_path.write_bytes(b"model bytes")
    with_field = CutoffsFile(model_version="v-test", sms=RULE, dialogue=RULE)
    without = CutoffsFile(sms=RULE, dialogue=RULE)
    assert model_version_for(with_field, joblib_path) == "v-test"
    expected = "svm_plain-" + hashlib.sha256(b"model bytes").hexdigest()[:8]
    assert model_version_for(without, joblib_path) == expected


def test_stub_chunk_keeps_pieces_to_45_words():
    pieces = chunk(["word " * 100])
    assert [len(p.split()) for p in pieces] == [45, 45, 10]


class RecordingScorer(Scorer):
    def __init__(self):
        self.seen: list[str] = []

    def score_pieces(self, pieces):
        self.seen.extend(pieces)
        return [0.0 for _ in pieces]


def test_sender_names_do_not_reach_the_scorer():
    scorer = RecordingScorer()
    chat = "12/03/2024, 14:05 - Kwame Mensah: hello there\n12/03/2024, 14:06 - Abena: hi"
    analyze_text(chat, "whatsapp", mock_engine(scorer))
    assert scorer.seen and all("Kwame" not in p and "Abena" not in p for p in scorer.seen)


@pytest.mark.parametrize("source, rule", [("sms", "sms"), ("plain", "dialogue"), ("whatsapp", "dialogue")])
def test_rule_follows_source(source, rule):
    text = "12/03/2024, 14:05 - Ann: hello" if source == "whatsapp" else "hello"
    assert analyze_text(text, source, mock_engine()).source_rule == rule


def test_rule_picks_its_own_cutoffs():
    sms = {"fpr_01": 10.0, "fpr_05": 9.0, "fpr_10": 8.0}
    cutoffs = CutoffsFile(sms=sms, dialogue=RULE)
    engine = Engine(MockScorer(), cutoffs, str, lambda m: m, "t", True)
    # one trigger word scores 1.0: low under the sms fixture, medium under the dialogue one
    assert analyze_text("urgent", "sms", engine).band == "low"
    assert analyze_text("urgent", "plain", engine).band == "medium"
