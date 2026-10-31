from .cutoffs import RuleCutoffs


def aggregate(scores: list[float], cutoffs: RuleCutoffs) -> float:
    """Turn piece scores into one chat-level score: the highest piece score.

    One clearly scam-like piece is enough to flag a chat, because a scam often sits in a
    few messages of an otherwise normal conversation.

    Known limitation: this rule has not been checked on whole chats yet. Every extra piece
    is another chance to cross a cut-off, so long chats may raise more false alarms.
    `cutoffs` is part of the signature so a rule that needs them can replace this one
    without changing the caller.
    """
    if not scores:
        raise ValueError("no scores to aggregate")
    return max(scores)
