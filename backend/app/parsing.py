import re
from dataclasses import dataclass
from typing import Optional

# Matches WhatsApp export lines, for example:
#   Android: 12/03/2025, 14:05 - Chidi: Hello
#   iPhone:  [12/03/2025, 14:05:09] Chidi: Hello
HEADER = re.compile(
    r"^\[?\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?\]?"
    r"\s*-?\s*(?P<sender>[^:]{1,60}):\s(?P<text>.*)$"
)
DATE_START = re.compile(r"^\[?\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}")


@dataclass
class Message:
    sender: Optional[str]
    text: str


def parse_chat(raw: str) -> list[Message]:
    # WhatsApp adds invisible direction marks at the start of some lines
    lines = [l.strip().lstrip("\u200e\u200f") for l in raw.splitlines()]
    lines = [l for l in lines if l]

    is_export = any(HEADER.match(l) for l in lines)
    if not is_export:
        # Plain pasted text: treat each line as one message
        return [Message(None, l) for l in lines]

    messages = []
    for l in lines:
        m = HEADER.match(l)
        if m:
            messages.append(Message(m.group("sender").strip(), m.group("text").strip()))
        elif DATE_START.match(l):
            continue  # a system line such as "Messages are end-to-end encrypted"
        elif messages:
            messages[-1].text += " " + l  # second line of a multi-line message
    return messages