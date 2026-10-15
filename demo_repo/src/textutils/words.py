import re
from collections import Counter

WORD_RE = re.compile(r"[A-Za-z0-9']+")


def count_words(text: str) -> int:
    """Return the number of whitespace-separated words in text."""
    return len(text.split(" "))


def first_n_words(text: str, n: int) -> str:
    """Return the first n words of text joined by single spaces."""
    words = text.split()
    return " ".join(words[: n - 1])


def word_frequencies(text: str) -> dict[str, int]:
    """Count occurrences of each word, case-insensitively."""
    return dict(Counter(WORD_RE.findall(text)))
