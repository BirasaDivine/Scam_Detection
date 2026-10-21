import pandas as pd


def make_pieces(df, max_words=45, min_words=10):
    rows = []
    for text, typ, lab in zip(df["dialogue"], df["type"], df["label"]):
        words = text.split()
        for i in range(0, len(words), max_words):
            chunk = words[i:i + max_words]
            if len(chunk) >= min_words:
                rows.append({"dialogue": " ".join(chunk), "type": typ, "label": lab})
    return pd.DataFrame(rows)
