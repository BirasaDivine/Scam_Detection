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
NUMBER = re.compile(r"\+?\d[\d\s\-()]{5,}\d")  # phone, account and ID-like digit runs


def mask(text: str) -> str:
    # The order matters: amounts must go before long numbers,
    # or "1500000 RWF" would be swallowed as a phone number.
    text = EMAIL.sub("<EMAIL>", text)
    text = LINK.sub("<LINK>", text)
    text = AMOUNT.sub("<AMOUNT>", text)
    text = NUMBER.sub("<NUMBER>", text)
    return text
    