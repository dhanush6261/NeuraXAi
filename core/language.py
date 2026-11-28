"""Language detection for NeuraXAi (English, Telugu script, and Roman Telugu).

Returns ``"telugu"`` or ``"english"``:
1. Any Telugu-script character (U+0C00–U+0C7F) returns ``"telugu"``.
2. Otherwise, whole ASCII words (``[a-z]+``, case-insensitive) are checked
   against Roman Telugu keyword sets:
   - Unambiguous keywords (``UNAMBIGUOUS_ROMAN_TELUGU_WORDS``):
     ``avunu``, ``baagundi``, ``baagunnanu``, ``baagunnara``, ``bagundi``,
     ``bagunnanu``, ``bagunnara``, ``chaala``, ``cheppandi``, ``cheppu``,
     ``chesthunnaru``, ``chesthunnav``, ``chestundi``, ``chestunnaru``,
     ``chestunnav``, ``cheyali``, ``cheyyali``, ``cheyyi``, ``chudu``,
     ``chupinchu``, ``ekkada``, ``elaaga``, ``emiti``, ``enduku``, ``enti``,
     ``eppudu``, ``evaru``, ``kaadu``, ``kaavali``, ``kavali``, ``ledu``,
     ``manam``, ``manamu``, ``meeru``, ``miru``, ``naaku``, ``naku``,
     ``namaskaram``, ``nenu``, ``raayali``, ``rayali``, ``telugulo``,
     ``undi``, ``unna``, ``unnaru``, ``unnav``, ``unnavu``, ``vaddu``.
   - Ambiguous keywords (also valid English words, names, or abbreviations;
     ``AMBIGUOUS_ROMAN_TELUGU_WORDS``):
     ``adi``, ``ani``, ``ante``, ``chala``, ``ela``, ``em``, ``emi``,
     ``ga``, ``idi``, ``lo``, ``mari``, ``mee``, ``naa``, ``oka``, ``peru``.

Threshold rule:
- At least 1 distinct unambiguous Roman Telugu keyword, OR at least 2 distinct
  keywords from the combined set (unambiguous + ambiguous) -> ``"telugu"``.
- A single ambiguous word on its own (e.g. ``"Peru"``, ``"Tell me about Peru"``,
  ``"Up the ante"``) does NOT flip the language and returns ``"english"``.
- Empty, whitespace, numeric, or unknown input returns ``"english"``.
"""
import re

TELUGU_REGEX = re.compile(r"[\u0C00-\u0C7F]")
WORD_REGEX = re.compile(r"\b[a-z]+\b")

UNAMBIGUOUS_ROMAN_TELUGU_WORDS = frozenset({
    "avunu",
    "baagundi",
    "baagunnanu",
    "baagunnara",
    "bagundi",
    "bagunnanu",
    "bagunnara",
    "chaala",
    "cheppandi",
    "cheppu",
    "chesthunnaru",
    "chesthunnav",
    "chestundi",
    "chestunnaru",
    "chestunnav",
    "cheyali",
    "cheyyali",
    "cheyyi",
    "chudu",
    "chupinchu",
    "ekkada",
    "elaaga",
    "emiti",
    "enduku",
    "enti",
    "eppudu",
    "evaru",
    "kaadu",
    "kaavali",
    "kavali",
    "ledu",
    "manam",
    "manamu",
    "meeru",
    "miru",
    "naaku",
    "naku",
    "namaskaram",
    "nenu",
    "raayali",
    "rayali",
    "telugulo",
    "undi",
    "unna",
    "unnaru",
    "unnav",
    "unnavu",
    "vaddu",
})

AMBIGUOUS_ROMAN_TELUGU_WORDS = frozenset({
    "adi",
    "ani",
    "ante",
    "chala",
    "ela",
    "em",
    "emi",
    "ga",
    "idi",
    "lo",
    "mari",
    "mee",
    "naa",
    "oka",
    "peru",
})

ALL_ROMAN_TELUGU_WORDS = UNAMBIGUOUS_ROMAN_TELUGU_WORDS | AMBIGUOUS_ROMAN_TELUGU_WORDS


def detect_language(text: str) -> str:
    """Detect whether *text* is English or Telugu (script or Roman Telugu)."""
    if not text or not isinstance(text, str):
        return "english"

    if TELUGU_REGEX.search(text):
        return "telugu"

    words = set(WORD_REGEX.findall(text.lower()))
    if not words:
        return "english"

    if words & UNAMBIGUOUS_ROMAN_TELUGU_WORDS:
        return "telugu"

    if len(words & ALL_ROMAN_TELUGU_WORDS) >= 2:
        return "telugu"

    return "english"
