from textutils.stats import average_word_length, longest_word, reading_minutes


def test_reading_minutes_keeps_fraction():
    assert reading_minutes(" ".join(["word"] * 250)) == 1.25


def test_reading_minutes_whole_minutes():
    assert reading_minutes(" ".join(["word"] * 400)) == 2.0


def test_average_word_length_uses_word_lengths():
    assert average_word_length("ab cd") == 2.0


def test_average_word_length_empty_text():
    assert average_word_length("") == 0.0


def test_longest_word_returns_first_on_tie():
    assert longest_word("cat dog") == "cat"


def test_longest_word_picks_longest():
    assert longest_word("a abc ab") == "abc"
