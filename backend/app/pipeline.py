from . import errors
from .aggregate import aggregate
from .bands import band_for
from .config import DISCLAIMER, MAX_MESSAGES
from .engine import Engine
from .errors import AppError
from .parsing import ParseError, parse
from .schemas import AnalyzeResponse, Source


def analyze_text(raw: str, source: Source, engine: Engine) -> AnalyzeResponse:
    if not raw.strip():
        raise AppError(400, errors.EMPTY)
    try:
        messages = parse(raw, source)
    except ParseError:
        raise AppError(400, errors.NOT_WHATSAPP) from None
    if not messages:
        raise AppError(400, errors.NO_MESSAGES)
    if len(messages) > MAX_MESSAGES:
        raise AppError(413, errors.TOO_MANY_MESSAGES)

    rule = "sms" if source == "sms" else "dialogue"
    # Only message text goes on. Sender names stay in the parser's output.
    texts = [engine.mask(m.text) for m in messages]
    pieces = [p for p in engine.chunk(texts) if p.strip()]
    if not pieces:
        raise AppError(400, errors.NO_MESSAGES)

    cutoffs = engine.cutoffs.for_rule(rule)
    verdict, band = band_for(aggregate(engine.scorer.score_pieces(pieces), cutoffs), cutoffs)
    return AnalyzeResponse(
        verdict=verdict,
        band=band,
        pieces_scored=len(pieces),
        source_rule=rule,
        model_version=engine.model_version,
        disclaimer=DISCLAIMER,
    )
