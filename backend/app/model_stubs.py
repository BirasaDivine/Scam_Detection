"""STUB. Stand-in used only in mock mode, when the files in backend/model/ are missing.

This is NOT masking v2 and NOT the notebook's make_pieces. It never runs with the real model.
"""

PIECE_MAX_WORDS = 45


def prepare(texts: list[str], rule: str) -> list[str]:
    if rule == "sms":
        whole = "\n".join(texts).strip()  # STUB: no masking at all
        return [whole] if whole else []
    words = " ".join(texts).split()
    return [" ".join(words[i:i + PIECE_MAX_WORDS]) for i in range(0, len(words), PIECE_MAX_WORDS)]
