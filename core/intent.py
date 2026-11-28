"""Recognize explicit requests to save a user's name."""

import re
import unicodedata


_NAME_PREFIX = re.compile(r"(?:my\s+name\s+is|call\s+me|naa\s+peru)\s+", re.IGNORECASE)

# ponytail: This blocklist is a heuristic and can be extended.
_NON_NAMES = {"back", "later", "tomorrow", "now", "soon", "not", "never", "anytime"}


def _is_name_word(word: str) -> bool:
    letters = word.replace("'", "").replace("-", "")
    return bool(letters) and letters[0].isalpha() and all(
        char.isalpha() or unicodedata.category(char).startswith("M") for char in letters[1:]
    )


def extract_name(text: str) -> str | None:
    text = text.strip()
    prefix = _NAME_PREFIX.match(text)
    if prefix is None:
        return None

    name = text[prefix.end():].rstrip(" \t\r\n.,!?;:…–—\"'”’)]}").rstrip()
    words = name.split()
    if not words or len(name) > 60 or len(words) > 4:
        return None
    if words[0].casefold() in _NON_NAMES:
        return None
    if not all(_is_name_word(word) for word in words):
        return None
    return name
