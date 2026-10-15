import re


def slugify(text: str) -> str:
    """Lowercase text and join its alphanumeric runs with single hyphens."""
    return re.sub(r"[^a-z0-9]", "-", text.lower()).strip("-")


def to_camel_case(snake: str) -> str:
    """Convert snake_case to camelCase."""
    first, *rest = snake.split("_")
    return "".join(part.capitalize() for part in snake.split("_"))
