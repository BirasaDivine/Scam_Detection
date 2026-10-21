import re
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Message:
    sender: Optional[str]
    text: str


class ParseError(Exception):
    """The text was meant to be a WhatsApp export but no message lines were found."""


# Date is day-first or month-first, with a 2 or 4 digit year. Time is 24h or 12h.
_DATE = r"(?P<d1>\d{1,2})[/.\-](?P<d2>\d{1,2})[/.\-](?P<y>\d{4}|\d{2})"
_TIME = r"(?P<h>\d{1,2})[:.](?P<mi>\d{2})(?:[:.](?P<s>\d{2}))?(?:\s?(?P<ampm>[AaPp]\.?\s?[Mm]\.?))?"
# Android: 12/03/2024, 14:05 - Name: text
ANDROID = re.compile(rf"^{_DATE},?\s+{_TIME}\s+-\s+(?P<rest>.*)$")
# iPhone:  [12/03/24, 14:05:11] Name: text
IOS = re.compile(rf"^\[{_DATE},?\s+{_TIME}\]\s*(?P<rest>.*)$")

SENDER = re.compile(r"^(?P<sender>[^:]{1,80}):(?: (?P<text>.*))?$")
# Group events that can contain ": " and would otherwise look like a message
GROUP_EVENT = re.compile(
    r"^[^:]{1,80}? (?:changed the subject|changed the group description|changed this group's)",
    re.IGNORECASE,
)
SYSTEM_TEXT = re.compile(
    r"end-to-end encrypted"
    r"|^this message was deleted\.?$"
    r"|^you deleted this message\.?$"
    r"|^<media omitted>$"
    r"|^(?:image|video|audio|sticker|gif|document|contact card) omitted$"
    r"|^missed (?:voice|video) call"
    r"|^waiting for this message"
    r"|^(?:.{1,80} )?joined using (?:this group's invite link|a group link)\.?$",
    re.IGNORECASE,
)
EDITED = re.compile(r"\s*<This message was edited>$", re.IGNORECASE)
DIRECTION_MARKS = "\u200e\u200f\u202a\u202b\u202c"


def parse(raw: str, source: str) -> list[Message]:
    text = _normalise(raw)
    if source == "sms":
        body = text.strip()
        return [Message(None, body)] if body else []
    if source == "plain":
        return [Message(None, line.strip()) for line in text.splitlines() if line.strip()]
    return parse_whatsapp(text)


def parse_whatsapp(text: str) -> list[Message]:
    messages: list[Message] = []
    found_header = False
    in_system = False  # continuation lines of a system line are dropped too
    for line in text.splitlines():
        line = line.strip().lstrip(DIRECTION_MARKS)
        if not line:
            continue
        m = _match_header(line)
        if m is None:
            if messages and not in_system:
                messages[-1].text += "\n" + line  # next line of a multi-line message
            continue  # text before the first header, or part of a system line

        found_header = True
        msg = _message_from(m.group("rest"))
        in_system = msg is None
        if msg is not None:
            messages.append(msg)

    if not found_header:
        raise ParseError
    return [m for m in messages if m.text]


def _normalise(raw: str) -> str:
    # Newer exports put a narrow no-break space before AM/PM
    return (
        raw.replace("\ufeff", "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u202f", " ")
        .replace("\u00a0", " ")
    )


def _match_header(line: str) -> Optional[re.Match]:
    m = ANDROID.match(line) or IOS.match(line)
    if m and _valid_stamp(m):
        return m
    return None


def _valid_stamp(m: re.Match) -> bool:
    d1, d2, y = int(m.group("d1")), int(m.group("d2")), m.group("y")
    year = int(y) if len(y) == 4 else 2000 + int(y)
    if not (_is_date(year, month=d2, day=d1) or _is_date(year, month=d1, day=d2)):
        return False
    h, mi = int(m.group("h")), int(m.group("mi"))
    if mi > 59 or (m.group("s") and int(m.group("s")) > 59):
        return False
    return 1 <= h <= 12 if m.group("ampm") else h <= 23


def _is_date(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
        return True
    except ValueError:
        return False


def _message_from(rest: str) -> Optional[Message]:
    """Return the message in a header line, or None for a system line."""
    if GROUP_EVENT.match(rest):
        return None
    m = SENDER.match(rest)
    if m is None:
        return None  # no "Name:" part, e.g. the Android encryption notice or "X joined"
    raw_text = m.group("text") or ""
    if raw_text.startswith("\u200e"):
        return None  # iPhone marks system text and media placeholders this way
    text = EDITED.sub("", raw_text.strip(DIRECTION_MARKS + " "))
    if SYSTEM_TEXT.search(text):
        return None
    return Message(m.group("sender").strip(), text)
