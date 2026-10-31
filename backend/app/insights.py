from typing import get_args

from .schemas import FormatCounts, Origin, Source, StatsResponse

MIN_CHECKS = 5
MIN_REPORTED = 5
MAIN_CHANNEL_SHARE = 0.4

ORIGIN_LABEL: dict[Origin, str] = {
    "whatsapp": "WhatsApp",
    "sms": "SMS",
    "telegram": "Telegram",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "email": "Email",
    "phone_call": "Phone calls",
    "other": "Other sources",
}

ORIGIN_TIP: dict[Origin, str] = {
    "whatsapp": "Warn people about messages from unknown numbers, and remind them never to share a WhatsApp verification code.",
    "sms": "Remind people that banks and mobile money providers never ask for a PIN or code by SMS.",
    "telegram": "Warn people about investment and job offers in Telegram groups and from accounts they do not know.",
    "facebook": "Warn people about Facebook messages and Marketplace sellers that ask for payment before meeting.",
    "instagram": "Warn people about Instagram accounts that offer giveaways, jobs or investments by direct message.",
    "email": "Remind people to check the sender's address and not to open links or attachments they did not expect.",
    "phone_call": "Remind people to hang up and call back on an official number before sending money or codes.",
    "other": "Ask people to choose a named source when they can, so the advice can be more specific.",
}


def build_stats(rows: list[tuple[str, str, str | None, int]]) -> StatsResponse:
    scam = sum(n for v, _, _, n in rows if v == "scam")
    not_scam = sum(n for v, _, _, n in rows if v == "not_scam")
    by_format = {f: FormatCounts(scam=0, not_scam=0) for f in get_args(Source)}
    origins: dict[str, int] = {o: 0 for o in get_args(Origin)}
    unreported = 0
    for verdict, fmt, origin, n in rows:
        if fmt in by_format:
            counts = by_format[fmt]
            if verdict == "scam":
                counts.scam += n
            else:
                counts.not_scam += n
        if verdict == "scam":
            if origin in origins:
                origins[origin] += n
            else:
                unreported += n
    return StatsResponse(
        total=scam + not_scam,
        scam=scam,
        not_scam=not_scam,
        by_input_format=by_format,
        scam_origins=origins,
        scam_origin_unreported=unreported,
        recommendations=recommend(scam + not_scam, scam, origins),
    )


def recommend(total: int, scam: int, origins: dict[str, int]) -> list[str]:
    if total < MIN_CHECKS:
        return ["Not enough checks yet for a recommendation."]
    tips = [f"{round(100 * scam / total)}% of checks were scams ({scam} of {total})."]
    reported = sum(origins.values())
    if reported < MIN_REPORTED:
        tips.append("Not enough scam sources reported yet to name a main channel.")
        return tips
    top = max(origins, key=lambda o: origins[o])
    share = origins[top] / reported
    if share >= MAIN_CHANNEL_SHARE:
        tips.append(f"Most reported scams came from {ORIGIN_LABEL[top]} ({round(100 * share)}%). {ORIGIN_TIP[top]}")
    else:
        tips.append("Reported scams are spread across several channels. No single channel stands out yet.")
    return tips
