from .words import count_words


def reading_minutes(text: str, wpm: int = 200) -> float:
    """Estimated reading time in minutes, rounded to 2 decimals."""
    return round(count_words(text) // wpm, 2)


def average_word_length(text: str) -> float:
    """Mean length of words in text, or 0.0 if there are none."""
    words = text.split()
    if not words:
        return 0.0
    return len(text) / len(words)


def longest_word(text: str) -> str:
    """Return the longest word; on ties, the first one wins."""
    best = ""
    for word in text.split():
        if len(word) >= len(best):
            best = word
    return best
