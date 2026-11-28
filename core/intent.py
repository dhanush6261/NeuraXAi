"""Recognize explicit requests to save a user's name."""

import re


_NAME_PREFIX = re.compile(r"(?:my\s+name\s+is|call\s+me|naa\s+peru)\s+", re.IGNORECASE)

# ponytail: This blocklist is a heuristic and can be extended.
_NON_NAMES = {"back", "later", "tomorrow", "now", "soon", "not", "never", "anytime"}


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
    if not all(word.replace("'", "").replace("-", "").isalpha() for word in words):
        return None
    return name
