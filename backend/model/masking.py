# ===== masking_model =====
import re, spacy

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
LINK = re.compile(r"(?:https?://|www\.)\S+|\b[\w-]+\.(?:com|net|org|co|io|ly|me|rw|ke|ug|tz|ng|gh|za)(?:/\S*)?\b", re.IGNORECASE)
CURRENCY = r"(?:rwf|frw|kes|ksh|ugx|tzs|ngn|ghs|zar|usd|shillings?|francs?|naira|cedis?|rand|dollars?|birr)"
AMOUNT = re.compile(rf"\b{CURRENCY}\.?\s?\d[\d,.]*|[$€£]\s?\d[\d,.]*|\d[\d,.]*\s?{CURRENCY}\b", re.IGNORECASE)
NUMBER = re.compile(r"\+?\d[\d\s\-()]{5,}\d")

GREETING = r"(?i:hi|hello|hey|dear|thanks|thank you)"
TITLE = r"(?i:mr|mrs|ms|miss|dr|prof)"
# A space only (no comma or full stop) between the greeting and the name: "Hi Chidi", "Dear Dr. Habimana"
AFTER_GREETING = re.compile(rf"\b{GREETING}\s+(?:{TITLE}\.?\s+)*([A-Z][a-z\-]{{2,}})")
AFTER_TITLE = re.compile(rf"\b{TITLE}\.?\s+([A-Z][a-z\-]{{2,}})")
NOT_NAMES = {"customer", "client", "user", "friend", "winner", "beneficiary", "sir", "madam",
             "everyone", "all", "team", "there", "what", "when", "where", "who", "why", "how",
             "this", "that", "please", "just", "yes", "well", "now", "today", "and", "but",
             "so", "the", "you", "your", "our", "for", "from", "with", "hmm"}

# Filters for spaCy's PERSON tags
INTERJECTIONS = {"hmm", "hm", "ya", "yeah", "yep", "wat", "ok", "okay", "lol", "haha", "oh", "ah",
                 "wow", "hey", "hi", "hello", "thanks", "pls", "plz", "sorry", "yes", "no"}
LEADING = {"this", "the", "a", "an", "my", "your", "our", "his", "her", "their", "dear", "hello",
           "hi", "hey", "thanks", "mr", "mrs", "ms", "miss", "dr", "prof"}
BAD_WORDS = {"st", "street", "rd", "road", "ave", "avenue", "usa", "uk", "ltd", "inc", "limited", "delivery", "bank"}

TOK = dict(name="nametoken", email="emailtoken", link="linktoken", amount="amounttoken", number="numtoken")
DISPLAY = {v: f"<{k.upper()}>" for k, v in TOK.items()}

_nlp = None
def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

def _person_span(ent):
    toks = list(ent)
    while toks and toks[0].lower_.rstrip(".") in LEADING:   # "this John Smith" -> "John Smith"
        toks = toks[1:]
    if not toks or len(toks) > 3:
        return None
    for t in toks:
        w = t.text
        if not w.replace("-", "").replace("'", "").isalpha() or not w[0].isupper() or len(w) < 2 or w.isupper():
            return None
        if w.lower() in INTERJECTIONS or w.lower() in BAD_WORDS:
            return None
    return toks[0].idx, toks[-1].idx + len(toks[-1])

def _greeted(m):
    if m.group(1).lower() in NOT_NAMES:
        return m.group(0)
    return m.group(0)[: m.start(1) - m.start(0)] + TOK["name"]

def _rest(text, known_names):
    for n in known_names:
        text = re.sub(rf"(?<!\w){re.escape(n)}(?!\w)", TOK["name"], text, flags=re.IGNORECASE)
    for pattern in (AFTER_GREETING, AFTER_TITLE):
        text = pattern.sub(_greeted, text)
    text = EMAIL.sub(TOK["email"], text)
    text = LINK.sub(TOK["link"], text)
    text = AMOUNT.sub(TOK["amount"], text)   # amounts before long numbers
    text = NUMBER.sub(TOK["number"], text)
    return text

def mask_texts(texts, known_names=()):
    texts = [str(t) for t in texts]
    out = []
    for doc, text in zip(_get_nlp().pipe(texts, batch_size=64), texts):
        spans = [s for s in (_person_span(e) for e in doc.ents if e.label_ == "PERSON") if s]
        for start, end in reversed(spans):
            text = text[:start] + TOK["name"] + text[end:]
        out.append(_rest(text, known_names))
    return out

def to_display(text):
    for tok, shown in DISPLAY.items():
        text = text.replace(tok, shown)
    return text
