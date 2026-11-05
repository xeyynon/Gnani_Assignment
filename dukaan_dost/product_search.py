"""
product_search.py

Finds which products a caller's sentence is about, by sound-alike character overlap rather than whole-word
matching. It exists for two jobs:

  1. A shop with too many items to send the model a catalogue on every turn: send only the best few matches.
  2. A second opinion on small shops, to catch what the model might miss.

Why not the keyword search in knowledge_retriever.py: it needs a whole word to match exactly, so a Hindi
spelling with or without the dot under the letter (प्याज / प्याज़), a Telugu plural (సబ్బు / సబ్బులు), a
transliteration, or a mis-heard word (छेनी for cheeni) all missed. Here a word is cut into overlapping 2, 3 and
4 letter pieces, so near-spellings still share most pieces.

How it works:
  - Each item becomes one small document: its names in English, Hindi and Telugu and its spellings.
  - Text is cleaned first: lower case, no zero-width joiners, no nukta (the dot under a Devanagari letter),
    no punctuation, no digits, and none of the words that carry no product meaning (quantities, units, "give me").
  - A piece's weight is higher the fewer items it appears in (inverse document frequency).
  - The sentence is cut into every run of 1 to 3 words; each run is scored against every item (cosine
    similarity), and an item's score is its best run. A run covers one product, so a sentence naming three
    products does not dilute any of them.
Pure Python, no model and no network: a search takes well under a millisecond for 61 items.
"""

import math
import re
import unicodedata
from collections import Counter

NGRAMS = (2, 3, 4)
MAX_RUN = 3
MIN_SCORE = 0.30            # below this a match is not reported at all

# Words that say how much or how, not what: removed from the caller's sentence before searching.
_NOISE = frozenset("""
a an the and or of to in on for with please give me i want need get add make it one two three four five six seven eight
nine ten half kilo kilos kg kgs gram grams litre litres liter liters packet packets pack packs piece pieces bar bars
bottle bottles loaf bag bags tray trays dozen some more less remove take out cancel total price rate cost much how what
ek do teen char paanch aadha adha dedh dena dedo de do chahiye chahie aur bhi hai ka ki ke ko se mujhe aap bas
एक दो तीन चार पांच पाँच छह सात आठ नौ दस आधा डेढ़ किलो ग्राम लीटर पैकेट पैक बार बोतल दीजिए दीजिये देना दे दो चाहिए चाहिये
और भी है का की के को से मुझे आप बस कम कर
ఒక రెండు మూడు నాలుగు ఐదు అర కిలో కిలోల కిలోలు లీటర్ ప్యాకెట్ కావాలి కావాలను మరియు చేయండి ఇవ్వండి
""".split())

_STRIP = dict.fromkeys(map(ord, "‌‍़॒॑"), None)      # joiners, nukta, stress marks


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").lower().translate(_STRIP)
    text = text.replace("।", " ").replace("॥", " ")         # the Hindi full stops lie inside the script range
    text = re.sub(r"[\d.,]+", " ", text)                       # quantities
    text = re.sub(r"[^\wऀ-෿]+", " ", text)           # punctuation, danda, brackets
    return " ".join(text.split())


def _grams(word: str) -> Counter:
    padded = f" {word} "
    out = Counter()
    for n in NGRAMS:
        for i in range(len(padded) - n + 1):
            out[padded[i:i + n]] += 1
    return out


class ProductSearch:
    def __init__(self, items: list):
        self.items = items
        self.skus = [it["sku"] for it in items]
        # One small vector per name or spelling of an item, not one blended vector per item: a caller says ONE of
        # the names, and blending seven names into one vector made every single name look weak.
        self._variants = []                 # (sku index, grams)
        for idx, it in enumerate(items):
            n = it["name"]
            names = [n["en"], n["hi"], n["te"], *it.get("aliases", [])]
            seen = set()
            for name in names:
                norm = normalise(name)
                if norm and norm not in seen:
                    seen.add(norm)
                    self._variants.append((idx, self._doc_vector(norm)))
        df = Counter()
        for _, g in self._variants:
            df.update(g.keys())
        total = len(self._variants)
        self._idf = {g: math.log((1 + total) / (1 + c)) + 1.0 for g, c in df.items()}
        self._vecs = [(idx, self._weigh(g)) for idx, g in self._variants]

    @staticmethod
    def _doc_vector(doc: str) -> Counter:
        total = Counter()
        for w in doc.split():
            total.update(_grams(w))
        return total

    def _weigh(self, grams: Counter) -> dict:
        vec = {g: (1 + math.log(c)) * self._idf.get(g, 1.0) for g, c in grams.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {g: v / norm for g, v in vec.items()}

    def _runs(self, text: str) -> list:
        words = [w for w in normalise(text).split() if w not in _NOISE and len(w) > 1]
        runs = []
        for i in range(len(words)):
            for n in range(1, MAX_RUN + 1):
                if i + n <= len(words):
                    runs.append(" ".join(words[i:i + n]))
        return runs

    def search(self, text: str, limit: int = 8) -> list:
        """[(sku, score)] best first, at most `limit`, each with score >= MIN_SCORE."""
        best = {}                                    # item index -> (score, words in the run that matched)
        for run in self._runs(text):
            q = self._weigh(self._doc_vector(run))
            span = run.count(" ") + 1
            for idx, dv in self._vecs:
                s = sum(w * dv.get(g, 0.0) for g, w in q.items())
                cur_s, cur_span = best.get(idx, (0.0, 0))
                if s > cur_s + 1e-9 or (abs(s - cur_s) <= 1e-9 and span > cur_span):
                    best[idx] = (max(s, cur_s), span)
        # Equal scores: the item matched by the longer phrase is the more specific one ("basmati chawal" is
        # basmati rice, though "chawal" alone is plain rice).
        ranked = sorted(((self.skus[i], round(v[0], 3), v[1]) for i, v in best.items() if v[0] >= MIN_SCORE),
                        key=lambda r: (-r[1], -r[2]))
        return [(sku, score) for sku, score, _ in ranked[:limit]]
