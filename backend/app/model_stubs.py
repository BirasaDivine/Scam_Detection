"""STUB. Stand-ins until backend/model/masking.py and chunking.py arrive from the notebook.

These are NOT masking v2 and NOT the notebook's make_pieces. They exist only so the
pipeline runs in mock mode, and they are never used with the real model.
"""

PIECE_MAX_WORDS = 45


def mask(text: str) -> str:
    return text  # STUB: no masking at all


def chunk(messages: list[str]) -> list[str]:
    # STUB: all words in order, cut into pieces of at most 45 words
    words = " ".join(messages).split()
    return [" ".join(words[i:i + PIECE_MAX_WORDS]) for i in range(0, len(words), PIECE_MAX_WORDS)]
