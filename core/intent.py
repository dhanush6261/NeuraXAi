"""Recognize explicit requests to save a user's name."""

import enum
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


class Intent(str, enum.Enum):
    GREETING = "greeting"
    THANKS = "thanks"
    FAREWELL = "farewell"
    IDENTITY = "identity"
    ASK_NAME = "ask_name"


# ponytail: Exact phrases keep "hi neuraxai" and "thanks, that helped" on the LLM path.
# Extend the table if real traffic shows misses.
_PHRASES = {
    phrase: intent
    for intent, phrases in (
        (Intent.GREETING, (
            "hi", "hii", "hello", "hey", "hi there", "hello there", "hey there",
            "good morning", "good afternoon", "good evening", "namaste", "namaskaram",
            "హాయ్", "హలో", "నమస్తే", "నమస్కారం",
        )),
        (Intent.THANKS, (
            "thanks", "thank you", "thanks a lot", "thank you so much", "thx",
            "dhanyavadalu", "ధన్యవాదాలు",
        )),
        (Intent.FAREWELL, (
            "bye", "bye bye", "goodbye", "good bye", "see you", "see you later",
            "good night", "ok bye", "బై", "శుభ రాత్రి",
        )),
        (Intent.IDENTITY, (
            "who are you", "what is your name", "what's your name", "whats your name",
            "nuvvu evaru", "meeru evaru", "nee peru enti", "mee peru enti",
            "నువ్వు ఎవరు", "మీరు ఎవరు", "నీ పేరు ఏమిటి", "మీ పేరు ఏమిటి",
        )),
        (Intent.ASK_NAME, (
            "what is my name", "what's my name", "whats my name", "do you know my name",
            "naa peru enti", "నా పేరు ఏమిటి", "నా పేరు ఏంటి",
        )),
    )
    for phrase in phrases
}

_REPLIES = {
    Intent.GREETING: ("Hello! How can I help you?", "హలో! నేను మీకు ఎలా సహాయం చేయగలను?"),
    Intent.THANKS: ("You're welcome!", "సంతోషం!"),
    Intent.FAREWELL: ("Bye! Talk to you soon.", "సరే, మళ్ళీ కలుద్దాం!"),
    Intent.IDENTITY: (
        "I'm NeuraXAi, a local AI assistant running on your computer.",
        "నేను NeuraXAi, మీ కంప్యూటర్ లో నడిచే లోకల్ AI అసిస్టెంట్.",
    ),
    Intent.ASK_NAME: ("I don't know.", "నాకు తెలియదు."),
}


def classify(text: str) -> Intent | None:
    normalized = " ".join(text.replace("’", "'").casefold().split()).strip(" .,!?;:…'\"-~")
    return _PHRASES.get(normalized)


def shortcut_reply(intent: Intent, language: str, user_name: str | None = None) -> str:
    if intent is Intent.ASK_NAME and user_name:
        return user_name
    english, telugu = _REPLIES[intent]
    return telugu if language == "telugu" else english
