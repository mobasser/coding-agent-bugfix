from textutils.case import slugify, to_camel_case


def test_slugify_collapses_punctuation_and_spaces():
    assert slugify("Hello,   World!") == "hello-world"


def test_slugify_strips_edge_separators():
    assert slugify("  Python 3.12 ") == "python-3-12"


def test_to_camel_case_keeps_first_word_lowercase():
    assert to_camel_case("user_name") == "userName"
