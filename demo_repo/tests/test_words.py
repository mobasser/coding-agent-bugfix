from textutils.words import count_words, first_n_words, word_frequencies


def test_count_words_ignores_extra_whitespace():
    assert count_words("one\ntwo") == 2
    assert count_words("  a  b  ") == 2


def test_first_n_words_returns_requested_count():
    assert first_n_words("a b c d", 2) == "a b"


def test_first_n_words_returns_all_when_n_is_large():
    assert first_n_words("a b", 5) == "a b"


def test_word_frequencies_is_case_insensitive():
    assert word_frequencies("The cat and the hat") == {"the": 2, "cat": 1, "and": 1, "hat": 1}
