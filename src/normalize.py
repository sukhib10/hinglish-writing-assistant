"""
Text normalization module for Hinglish Writing Assistant.

Provides pre-transliteration SMS spelling canonicalization and
post-transliteration Devanagari-to-ASCII digit conversion.
"""

import re

# Small, curated dictionary mapping common informal Roman/SMS spellings
# to their standard Hinglish forms.
# Applied to whole lowercase words only to avoid corrupting substrings
# (e.g. 'mai' inside 'email' or 'remain') or capitalized proper names (e.g. 'Rahul', 'Priya').
SMS_SPELLINGS = {
    # Common informal negation
    "nhi": "nahi",
    "nahin": "nahi",
    # Slang / phonetic shorthand for 'pata' (know) - prevents mistransliterating as 'PTA' / 'पीटीए'
    "pta": "pata",
    # 1st-person auxiliary / copula 'hoon' (am)
    "hu": "hoon",
    "hun": "hoon",
    # 1st-person pronoun 'main' (I) - prevents mistransliterating as calendar month 'मई'
    "mai": "main",
    # Adjective / adverb 'theek' (fine/okay) - prevents dental 'थिक' instead of retroflex 'ठीक'
    "thik": "theek",
    # Interrogative / question word 'kya' (what)
    "kyaa": "kya",
    # 1st-person dative pronoun 'mujhe' (to me / me)
    "mujhey": "mujhe",
    "muje": "mujhe",
    # Single-letter copula abbreviation 'h' -> 'hai' (is)
    "h": "hai",
}

# Mapping table for Devanagari numerals (०-९) to ASCII Arabic numerals (0-9)
_DEVANAGARI_DIGITS = "०१२३४५६७८९"
_ASCII_DIGITS = "0123456789"
_DEVA_TO_ASCII_TABLE = str.maketrans(_DEVANAGARI_DIGITS, _ASCII_DIGITS)


def normalize_sms(text: str) -> str:
    """
    Normalizes common informal SMS/chat Roman spellings to standard forms.

    Applies whole-word replacement for lowercase words matching SMS_SPELLINGS.
    Preserves punctuation, whitespace, and capitalization of words not in
    the dictionary (such as personal or city names like 'Rahul', 'Priya', 'Delhi').
    Ensures standalone words like 'mai' are only replaced when whole tokens,
    preventing corruption of legitimate words like 'email' or 'remain'.
    """
    if not text:
        return "" if text is None else text

    def _replace_word(match: re.Match) -> str:
        word = match.group(0)
        return SMS_SPELLINGS.get(word, word)

    # Match whole alphabetic words bounded by word boundaries
    return re.sub(r"\b[a-zA-Z]+\b", _replace_word, text)


def devanagari_to_ascii_digits(text: str) -> str:
    """
    Converts native Devanagari numerals (०-९) to standard ASCII Arabic digits (0-9).
    Preserves all other characters untouched.
    """
    if not text:
        return "" if text is None else text
    return text.translate(_DEVA_TO_ASCII_TABLE)
