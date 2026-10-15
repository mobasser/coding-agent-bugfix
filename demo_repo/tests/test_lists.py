from textutils.lists import join_with_and


def test_join_with_and_single_item():
    assert join_with_and(["cats"]) == "cats"


def test_join_with_and_two_items():
    assert join_with_and(["cats", "dogs"]) == "cats and dogs"


def test_join_with_and_three_items():
    assert join_with_and(["a", "b", "c"]) == "a, b, and c"
