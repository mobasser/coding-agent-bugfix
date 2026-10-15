from textutils.truncate import truncate


def test_truncate_adds_ellipsis_when_cut():
    assert truncate("hello world", 8) == "hello..."


def test_truncate_keeps_text_that_fits_exactly():
    assert truncate("hello", 5) == "hello"


def test_truncate_keeps_short_text():
    assert truncate("hi", 10) == "hi"
