"""
A caller asks, in Hindi, to hear their order again in Telugu ("मेरा ऑर्डर तेलुगु में दोबारा बताओ").

The speech service writes Hindi speech in Devanagari, so the language name arrives as "तेलुगु", not "Telugu". Before this
was handled, only the Latin spellings were recognised and the order was read back in the call's own language.

    python -m pytest tests/test_language_request.py
"""

import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="module")
def app():
    try:
        import dukaan_dost.app as m
    except Exception as e:
        pytest.skip(f"main module not importable here: {e}")
    return m


# ---- which language was asked for ----------------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "मेरा ऑर्डर तेलुगु में दोबारा बताओ",             # Devanagari, the demo sentence
    "मेरा ऑर्डर तेलुगु में फिर से सुनाओ",
    "मेरा आर्डर तेलुगू में बोलो",
    "मेरा ऑर्डर तेलगु में दोहराओ",
    "నా ఆర్డర్ తెలుగులో మళ్ళీ చెప్పండి",              # Telugu script
    "repeat my order in Telugu",
    "mera order Telugu mein dobara bolo",
    "mera order telegu mein batao",
    "TELUGU MEIN BATAO",
])
def test_telugu_is_recognised_in_every_script(app, text):
    assert app._extract_requested_language(text) == "te-in"


@pytest.mark.parametrize("text", ["Hindi mein bolo", "मेरा ऑर्डर हिंदी में बताओ", "मेरा ऑर्डर हिन्दी में सुनाओ", "హిందీలో చెప్పండి"])
def test_hindi_is_recognised(app, text):
    assert app._extract_requested_language(text) == "hi-in"


@pytest.mark.parametrize("text", ["repeat in English", "मेरा ऑर्डर अंग्रेज़ी में बताओ", "मेरा ऑर्डर अंग्रेजी में बताओ", "इंग्लिश में बोलो", "ఇంగ్లీష్ లో చెప్పండి"])
def test_english_is_recognised(app, text):
    assert app._extract_requested_language(text) == "en-in"


@pytest.mark.parametrize("text", ["", "repeat my order", "मेरा ऑर्डर दोबारा बताओ", "cash", "ek kilo sugar"])
def test_no_language_named_gives_none(app, text):
    assert app._extract_requested_language(text) is None


def test_the_language_named_last_is_the_one_asked_for(app):
    assert app._extract_requested_language("Hindi mein poocha, Telugu mein batao") == "te-in"
    assert app._extract_requested_language("हिंदी में पूछा, अब तेलुगु में बताओ") == "te-in"
    assert app._extract_requested_language("Telugu mein nahi, Hindi mein batao") == "hi-in"


def test_a_dotted_letter_matches_in_either_form(app):
    one = "अंग्रेज़ी"                                      # ज़ as one character (U+095B)
    two = "अंग्रेज़ी"                                # ज + the dot (U+091C U+093C)
    assert one != two and unicodedata.normalize("NFD", one) == two
    assert app._extract_requested_language(f"ऑर्डर {one} में") == "en-in"
    assert app._extract_requested_language(f"ऑर्डर {two} में") == "en-in"


# ---- is it a request to read the order back ------------------------------------------------------------------------

@pytest.mark.parametrize("text", [
    "मेरा ऑर्डर तेलुगु में दोबारा बताओ",
    "मेरा ऑर्डर तेलुगु में फिर से सुनाओ",
    "मेरा ऑर्डर तेलुगु में बताइए",
    "मेरा ऑर्डर दोहराओ",
    "ऑर्डर रिपीट करो",
    "mera order Telugu mein dobara bolo",
    "mera order Telugu mein batao",
    "repeat my order in Telugu",
    "read my order",
    "నా ఆర్డర్ మళ్ళీ చెప్పండి",
])
def test_a_request_to_hear_the_order_again_is_recognised(app, text):
    assert app._is_order_readback_request(text)


@pytest.mark.parametrize("text", ["cash", "ek kilo sugar", "दो किलो चीनी", "उधार पर रमेश", "Telugu mein batao", "बताओ", "my name is Ramesh"])
def test_other_sentences_are_not_a_readback_request(app, text):
    assert not app._is_order_readback_request(text)


def test_an_item_sentence_with_a_repeat_word_is_an_order_turn_not_a_readback(app):
    text = "ऑर्डर में दो किलो चीनी दोबारा"
    assert app._carries_order_words(text)                    # the caller guards with this before treating it as a readback
