"""Shared file validation helpers."""
from collections.abc import Iterable


def is_allowed_file(filename: str, allowed_extensions: Iterable[str]) -> bool:
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in {ext.lower() for ext in allowed_extensions}
