"""How the Ukrainian voice reads Latin words: Dota names from
data/promo/pronounce.json first, then simple English-to-Ukrainian rules.
Words read by the rules are returned so the quality report can list them."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "promo" / "pronounce.json"

# Longest first; applied left to right on a lower-case word.
RULES = (
    ("tch", "ч"),
    ("sch", "ск"),
    ("igh", "ай"),
    ("ough", "оу"),
    ("sh", "ш"),
    ("ch", "ч"),
    ("th", "т"),
    ("ph", "ф"),
    ("ck", "к"),
    ("qu", "кв"),
    ("ee", "і"),
    ("ea", "і"),
    ("oo", "у"),
    ("ou", "ау"),
    ("ow", "оу"),
    ("ay", "ей"),
    ("ai", "ей"),
    ("ey", "ей"),
    ("oa", "оу"),
    ("er", "ер"),
    ("wh", "в"),
    ("kn", "н"),
    ("a", "а"),
    ("b", "б"),
    ("c", "к"),
    ("d", "д"),
    ("e", "е"),
    ("f", "ф"),
    ("g", "г"),
    ("h", "х"),
    ("i", "і"),
    ("j", "дж"),
    ("k", "к"),
    ("l", "л"),
    ("m", "м"),
    ("n", "н"),
    ("o", "о"),
    ("p", "п"),
    ("q", "к"),
    ("r", "р"),
    ("s", "с"),
    ("t", "т"),
    ("u", "у"),
    ("v", "в"),
    ("w", "в"),
    ("x", "кс"),
    ("y", "і"),
    ("z", "з"),
)
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'’]*")


@lru_cache(maxsize=1)
def names() -> dict[str, str]:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    return dict(data["names"])


def transliterate(word: str) -> str:
    text = word.lower().replace("’", "'").replace("'", "")
    if len(text) > 3 and text.endswith("e") and text[-2] not in "aeiouy":
        text = text[
            :-1
        ]  # a silent final e: "blade" -> "блейд" needs the dictionary, "spike" -> "спайк" too
    out = []
    i = 0
    while i < len(text):
        for latin, cyrillic in RULES:
            if text.startswith(latin, i):
                # c before e, i, y sounds like s
                if latin == "c" and text[i + 1 : i + 2] in ("e", "i", "y"):
                    cyrillic = "с"
                out.append(cyrillic)
                i += len(latin)
                break
        else:
            i += 1
    result = "".join(out)
    return result[:1].upper() + result[1:] if word[:1].isupper() else result


def percent_word(number: int) -> str:
    """«відсоток / відсотки / відсотків» for a whole number."""
    if number % 10 == 1 and number % 100 != 11:
        return "відсоток"
    if number % 10 in (2, 3, 4) and number % 100 not in (12, 13, 14):
        return "відсотки"
    return "відсотків"


def _percent(match: re.Match[str]) -> str:
    whole, fraction = match.group(1), match.group(2)
    if fraction:  # a fraction always takes «відсотка»
        return f"{whole},{fraction} відсотка"
    return f"{whole} {percent_word(int(whole))}"


def for_voice(text: str) -> tuple[str, list[str]]:
    """(the text with every Latin word in Cyrillic, the words read by the rules)."""
    table = names()
    # Whole names first, longest first, as words (not inside other words).
    for name in sorted(table, key=len, reverse=True):
        pattern = r"(?<![\w'])" + re.escape(name) + r"(?![\w'])"
        text = re.sub(pattern, table[name], text)
    guessed: list[str] = []

    def rule(match: re.Match[str]) -> str:
        word = match.group(0)
        if word not in guessed:
            guessed.append(word)
        return transliterate(word)

    text = LATIN_WORD.sub(rule, text)
    # «53 %» is said «53 відсотки»: the word agrees with the number.
    text = re.sub(r"(\d+)(?:[,.](\d+))?[\s\u00a0]?%", _percent, text)
    return text, guessed
