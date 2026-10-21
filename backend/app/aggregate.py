from .cutoffs import RuleCutoffs


def aggregate(scores: list[float], cutoffs: RuleCutoffs) -> float:
    """Turn piece scores into one chat-level score.

    TODO: placeholder rule, not validated. The final rule is being chosen from
    call-level evaluation. Taking the highest piece score may raise false alarms
    on long chats, because every extra piece is another chance to cross a cut-off.
    `cutoffs` is unused here but kept so a replacement rule can use it.
    """
    if not scores:
        raise ValueError("no scores to aggregate")
    return max(scores)
