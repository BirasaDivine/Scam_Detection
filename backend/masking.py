import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
LINK = re.compile(
    r"(?:https?://|www\.)\S+"
    r"|\b[\w-]+\.(?:com|net|org|co|io|ly|me|rw|ke|ug|tz|ng|gh|za)(?:/\S*)?\b",
    re.IGNORECASE,
)
CURRENCY = r"(?:rwf|frw|kes|ksh|ugx|tzs|ngn|ghs|zar|usd|shillings?|francs?|naira|cedis?|rand|dollars?|birr)"
AMOUNT = re.compile(
    rf"\b{CURRENCY}\.?\s?\d[\d,.]*|[$€£]\s?\d[\d,.]*|\d[\d,.]*\s?{CURRENCY}\b",
    re.IGNORECASE,
)
NUMBER = re.compile(r"\+?\d[\d\s\-()]{5,}\d")

# Greeting or title, then a capitalised word: "Hi Chidi", "Hello Dr. Habimana"
LEAD = r"(?i:hi|hello|hey|dear|thanks|thank you|mr|mrs|ms|miss|dr|prof|sir|madam)"
GREETED_NAME = re.compile(rf"\b(?:{LEAD}\.?,?\s+)+([A-Z][a-z'\-]+)")
# Words that follow a greeting but are not names. "Dear Customer" is a classic scam signal, so keep it.
NOT_NAMES = {"customer", "client", "user", "friend", "winner", "beneficiary",
             "sir", "madam", "everyone", "all", "team", "there"}

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _mask_people(text):
    doc = _get_nlp()(text)
    for ent in reversed(doc.ents):  # from the end, so the character positions stay valid
        if ent.label_ == "PERSON":
            text = text[:ent.start_char] + "<NAME>" + text[ent.end_char:]
    return text


def names_from_senders(senders):
    names = set()
    for s in senders:
        if not s or s.strip().lower() in {"you", "me"}:
            continue
        s = s.strip()
        names.add(s)
        for part in s.split():
            if len(part) >= 3:
                names.add(part)
    return sorted(names, key=len, reverse=True)  # longest first


def _mask_known(text, names):
    for n in names:
        text = re.sub(rf"(?<!\w){re.escape(n)}(?!\w)", "<NAME>", text, flags=re.IGNORECASE)
    return text


def _mask_greeted(text):
    def repl(m):
        if m.group(1).lower() in NOT_NAMES:
            return m.group(0)
        return m.group(0)[: m.start(1) - m.start(0)] + "<NAME>"
    return GREETED_NAME.sub(repl, text)


def mask(text: str, known_names=()) -> str:
    text = _mask_people(text)
    text = _mask_known(text, known_names)
    text = _mask_greeted(text)
    # The order matters: amounts must go before long numbers.
    text = EMAIL.sub("<EMAIL>", text)
    text = LINK.sub("<LINK>", text)
    text = AMOUNT.sub("<AMOUNT>", text)
    text = NUMBER.sub("<NUMBER>", text)
    return text