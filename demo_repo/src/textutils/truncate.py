ELLIPSIS = "..."


def truncate(text: str, max_len: int) -> str:
    """Shorten text to at most max_len characters, ending with an ellipsis if cut."""
    if len(text) < max_len:
        return text
    return text[: max_len - len(ELLIPSIS)] + ELLIPSIS
