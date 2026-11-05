"""
Test phrases for product retrieval: what a caller might say (or what Prisma wrote down), and the SKUs that
phrase asks for. Used by evaluation/retrieval_benchmark.py to compare ways of finding products. Synthetic.

"heard" cases are real Prisma output from the 2026-11-03 clean evaluation run (evaluation/results/orders_clean_baseline_retrieval.*).
"variant" cases are written by hand to cover spellings and scripts the run did not happen to meet.
"""

HEARD = [
    ("2 किलो छेनी और 1 लीटर sunflower oil से है।", ["SUGAR-1KG", "OIL-1L"]),
    ("एक packet Maggi और दो packet Parle-G देना।", ["MAGGI-70", "PARLEG-100"]),
    ("आधा किलो प्याज और एक किलो आलू चाहिए।", ["ONION-1KG", "POTATO-1KG"]),
    ("3 किलो चावल और 1 किलो तोर dal देना।", ["RICE-1KG", "DAL-TOOR-1KG"]),
    ("चावल 1 किलो कम कर दो।", ["RICE-1KG"]),
    ("एक ghee और 2 packet नमक देना।", ["GHEE-500", "SALT-1KG"]),
    ("Paneer aur ek packet bread dena.", ["PANEER-200", "BREAD-400"]),
    ("1.5 किलो छीनी चाहिए।", ["SUGAR-1KG"]),
    ("2 किलो आटा और 8 लीटर तेल चाहिए।", ["ATTA-5KG", "OIL-1L"]),
    ("मुझे 3 पैकेट चाय पत्ती और 1 किलो चीनी दीजिए।", ["TEA-250", "SUGAR-1KG"]),
    ("1 किलो basmati चावल और 0.5 किलो tomato चाहिए।", ["BASMATI-1KG", "TOMATO-1KG"]),
    ("टमाटर 1 किलो कर दीजिए।", ["TOMATO-1KG"]),
    ("2 కిలోల బియ్యం మరియు 1 లీటర్ నూనె కావాలి.", ["RICE-1KG", "OIL-1L"]),
    ("అర కిలో ఉల్లిపాయలు మరియు ఒక కిలో బంగాళాదుంపలు కావాలి.", ["ONION-1KG", "POTATO-1KG"]),
    ("3 కిలోల చక్కెర మరియు ఒక ప్యాకెట్ tea powder కావాలి.", ["SUGAR-1KG", "TEA-250"]),
    ("చక్కెర 2 కిలోలు చేయండి.", ["SUGAR-1KG"]),
    ("ఒక కిలో కందిపప్పు మరియు 2 సబ్బులు కావాలి.", ["DAL-TOOR-1KG", "SOAP-100"]),
    ("Paneer మరియు ఒక packet పెరుగు కావాలి.", ["PANEER-200", "CURD-400"]),
    ("I want 2 kilos of rice and 1 litre of sunflower oil.", ["RICE-1KG", "OIL-1L"]),
    ("1 packet of Maggi, 2 packets of Parle-G, and a dragon fruit.", ["MAGGI-70", "PARLEG-100"]),
    ("Give me 0.5 kilo of onions and a loaf of bread.", ["ONION-1KG", "BREAD-400"]),
    ("Make it 1 kilo of onions.", ["ONION-1KG"]),
    ("1 ghee and a paneer, please.", ["GHEE-500", "PANEER-200"]),
    ("Add 3 trays of eggs.", ["EGGS-6"]),
]

VARIANTS = [
    # Devanagari with and without the dot under the letter, and common respellings
    ("प्याज़ चाहिए", ["ONION-1KG"]),
    ("पनीर दे दो", ["PANEER-200"]),
    ("अरहर की दाल एक किलो", ["DAL-TOOR-1KG"]),
    ("मूंग दाल आधा किलो", ["DAL-MOONG-1KG"]),
    ("चना दाल और राजमा", ["DAL-CHANA-1KG", "RAJMA-500"]),
    ("लहसुन और अदरक", ["GARLIC-250", "GINGER-250"]),
    ("हल्दी और लाल मिर्च पाउडर", ["TURMERIC-100", "CHILLI-100"]),
    ("साबुन और टूथपेस्ट", ["SOAP-100", "TOOTHPASTE-100"]),
    ("सरसों का तेल एक लीटर", ["OIL-MUSTARD-1L"]),
    ("मूंगफली का तेल", ["OIL-GNUT-1L"]),
    ("दूध दो पैकेट", ["MILK-500"]),
    ("गुड़ चाहिए", ["JAGGERY-500"]),
    # Hinglish in Latin letters
    ("pyaz aur aloo", ["ONION-1KG", "POTATO-1KG"]),
    ("cheeni aur chai patti", ["SUGAR-1KG", "TEA-250"]),
    ("doodh aur dahi", ["MILK-500", "CURD-400"]),
    ("namak, haldi aur mirch powder", ["SALT-1KG", "TURMERIC-100", "CHILLI-100"]),
    ("gehu ka atta aur nariyal tel", ["ATTA-5KG", "OIL-COCONUT-500"]),
    ("amul butter aur ek makhan", ["BUTTER-100"]),
    ("good day biscuit aur rusk", ["GOODDAY-75", "RUSK-200"]),
    ("agarbatti aur machis", ["AGARBATTI-1", "MATCHBOX-1"]),
    # Telugu
    ("పాలు మరియు పెరుగు", ["MILK-500", "CURD-400"]),
    ("కారం పొడి మరియు పసుపు", ["CHILLI-100", "TURMERIC-100"]),
    ("నెయ్యి ఒక ప్యాకెట్", ["GHEE-500"]),
    ("గుడ్లు ఆరు", ["EGGS-6"]),
    ("టమాటాలు మరియు పచ్చిమిర్చి", ["TOMATO-1KG", "GREENCHILLI-100"]),
    ("కొబ్బరి నూనె", ["OIL-COCONUT-500"]),
    ("బెల్లం అర కిలో", ["JAGGERY-500"]),
    ("మినపప్పు మరియు పెసరపప్పు", ["DAL-URAD-1KG", "DAL-MOONG-1KG"]),
]


# Written AFTER the retriever was tuned on the cases above and not used to tune it: the fairer measure.
# Spellings and words a caller (or Prisma) might produce that appear nowhere in the stock list's aliases.
HOLDOUT = [
    ("shakkar aur chaval dena", ["SUGAR-1KG", "RICE-1KG"]),
    ("dal chahiye toor wali", ["DAL-TOOR-1KG"]),
    ("pyaaj tamatar aloo", ["ONION-1KG", "TOMATO-1KG", "POTATO-1KG"]),
    ("ek kilo atte ka packet", ["ATTA-5KG"]),
    ("thoda sa jeera aur sarson", ["CUMIN-100", "MUSTARD-100"]),
    ("brown bread aur anda", ["BREAD-400", "EGGS-6"]),
    ("surf aur vim bar", ["DETERGENT-1KG", "DISHWASH-BAR"]),
    ("imli aur kali mirch", ["TAMARIND-250", "PEPPER-50"]),
    ("kaju badam", []),
    ("कॉफी और चाय", ["COFFEE-100", "TEA-250"]),
    ("बेसन और मैदा और सूजी", ["BESAN-500", "MAIDA-500", "SUJI-500"]),
    ("नींबू और हरी मिर्च", ["LEMON-1", "GREENCHILLI-100"]),
    ("बिस्किट और नमकीन", ["PARLEG-100", "GOODDAY-75", "BHUJIA-200"]),
    ("मोमबत्ती और अगरबत्ती", ["CANDLE-6", "AGARBATTI-1"]),
    ("కందిపప్పు మరియు శనగపప్పు", ["DAL-TOOR-1KG", "DAL-CHANA-1KG"]),
    ("ఉప్పు చింతపండు", ["SALT-1KG", "TAMARIND-250"]),
    ("అల్లం వెల్లుల్లి", ["GINGER-250", "GARLIC-250"]),
    ("కాఫీ పొడి", ["COFFEE-100"]),
    ("సబ్బు మరియు టూత్ పేస్ట్", ["SOAP-100", "TOOTHPASTE-100"]),
    ("2 packets of good day and some bhujia", ["GOODDAY-75", "BHUJIA-200"]),
    ("a bottle of cold drink and water", ["COLD-750", "WATER-1L"]),
    ("coconut oil and groundnut oil", ["OIL-COCONUT-500", "OIL-GNUT-1L"]),
    ("curd, butter and ghee", ["CURD-400", "BUTTER-100", "GHEE-500"]),
    ("basmati rice and jaggery", ["BASMATI-1KG", "JAGGERY-500"]),
]

CASES = [{"source": "heard", "text": t, "expected": e} for t, e in HEARD] +         [{"source": "variant", "text": t, "expected": e} for t, e in VARIANTS] +         [{"source": "holdout", "text": t, "expected": e} for t, e in HOLDOUT]
