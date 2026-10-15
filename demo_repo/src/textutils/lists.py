def join_with_and(items: list[str]) -> str:
    """Join items as a human-readable list: 'a', 'a and b', 'a, b, and c'."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"
