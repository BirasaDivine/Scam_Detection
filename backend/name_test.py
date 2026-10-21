import spacy

nlp = spacy.load("en_core_web_sm")

tests = [
    "Hi Chidi, are you free tomorrow?",
    "This is Uwase from the bank, please confirm your PIN.",
    "Kamau sent me your number.",
    "Wanjiru, I sent you money by mistake.",
    "My name is Amina Hassan and I work at Equity Bank.",
    "Please call Mr. Okafor on the number below.",
    "Mukamana told me about the scholarship.",
    "Thanks Emmanuel, see you at the market.",
    "Hello Dr. Habimana, your parcel is waiting.",
    "Send the fee to Jean Claude Niyonzima today.",
]

caught = 0
for t in tests:
    found = [(e.text, e.label_) for e in nlp(t).ents]
    print(t, "->", found)