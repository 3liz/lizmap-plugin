"""Relative paths used by the synchronisation.

All paths handled by the synchronisation are relative to the synchronised root directory,
use "/" as separator and are normalised in the Unicode NFC form, so that paths coming from
macOS (NFD), Windows or the server can be compared.
"""

from __future__ import annotations

import unicodedata


class InvalidPathError(ValueError):
    """The path cannot be used by the synchronisation."""


def normalize_relative_path(path: str) -> str:
    """Normalise and validate a relative path.

    A trailing "/" is accepted, for directories, and removed.

    :param path: Relative path, with "/" as separator.
    :return: The path in the Unicode NFC form, without trailing "/".
    :raises InvalidPathError: If the path is empty, absolute, contains a backslash,
        a NUL character, a drive letter or a "", "." or ".." segment.
    """
    if not isinstance(path, str) or not path:
        raise InvalidPathError("The path must be a non-empty string.")

    # Characters which are never allowed
    if "\\" in path or "\x00" in path:
        raise InvalidPathError(f"Invalid character in the path '{path}'.")

    if path.startswith("/"):
        raise InvalidPathError(f"The path '{path}' must be relative.")

    # Each segment must be a real name, which prevents any path traversal
    segments = path.rstrip("/").split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise InvalidPathError(f"Invalid segment in the path '{path}'.")

    # A Windows drive letter, like "C:"
    first = segments[0]
    if len(first) == 2 and first[1] == ":" and first[0].isalpha():
        raise InvalidPathError(f"The path '{path}' must be relative.")

    return unicodedata.normalize("NFC", "/".join(segments))


def parent_directories(path: str) -> list[str]:
    """List the parent directories of a relative path, from the top-level one.

    For instance, "a/b/c.txt" gives ["a", "a/b"].

    :param path: Normalised relative path.
    :return: The parent directories, the root directory is not included.
    """
    segments = path.split("/")[:-1]
    return ["/".join(segments[: i + 1]) for i in range(len(segments))]
