"""Exclusion rules of the synchronisation.

Patterns follow a simplified ".gitignore" syntax, matched without taking care of the case:

* a pattern ending with "/" matches a directory name at any depth, for instance ".git/",
* a pattern containing a "/" matches the whole relative path, for instance "data/raw/*.csv",
* any other pattern matches the file name at any depth, for instance "*.bak".
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatchcase

# Prefix of the files and directories of the synchronisation itself: downloads in progress,
# local trash, uploads in progress on the server. They are always excluded, whatever the rules.
INTERNAL_PREFIX = ".~lizmap-"

DEFAULT_EXCLUDE_PATTERNS: tuple[str, ...] = (
    # Version control and Python caches
    ".git/",
    ".svn/",
    "__pycache__/",
    # QGIS backups and project formats not usable by Lizmap Web Client
    "*.qgs~",
    "*.qgz",
    "*.qgz~",
    "*.bak",
    # SQLite and GeoPackage temporary files, they must never be sent alone
    "*.gpkg-wal",
    "*.gpkg-shm",
    "*.sqlite-wal",
    "*.sqlite-shm",
    "*-journal",
    # Operating systems and office software
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "~$*",
    ".~lock.*#",
    "*.tmp",
)


class ExclusionReason(Enum):
    """Why a path is excluded."""

    Pattern = "pattern"
    Hidden = "hidden"
    Size = "size"
    # File or directory of the synchronisation itself
    Internal = "internal"


@dataclass(frozen=True)
class Exclusion:
    """Exclusion of a path.

    :param reason: Why the path is excluded.
    :param detail: The matching pattern, the hidden segment or the size limit in bytes.
    """

    reason: ExclusionReason
    detail: str


def _match(value: str, pattern: str) -> bool:
    """Match a value with a pattern, case insensitive.

    :param value: A file or directory name, or a relative path.
    :param pattern: A glob pattern.
    :return: True if the value matches.
    """
    return fnmatchcase(value.lower(), pattern.lower())


@dataclass(frozen=True)
class ExcludeRules:
    """Rules telling which files are not synchronised.

    :param patterns: Glob patterns, see the module documentation.
    :param exclude_hidden: Exclude files and directories starting with a ".".
    :param max_size: Files bigger than this size, in bytes, are excluded. None for no limit.
    """

    patterns: tuple[str, ...] = DEFAULT_EXCLUDE_PATTERNS
    exclude_hidden: bool = True
    max_size: int | None = None

    def _directory_exclusion(self, segments: list[str]) -> Exclusion | None:
        """Check directory names against the hidden rule and the directory patterns.

        :param segments: Directory names, from the top-level one.
        :return: The exclusion, or None if no directory is excluded.
        """
        for index, segment in enumerate(segments):
            if segment.startswith(INTERNAL_PREFIX):
                return Exclusion(ExclusionReason.Internal, segment)

            if self.exclude_hidden and segment.startswith("."):
                return Exclusion(ExclusionReason.Hidden, segment)

            for pattern in self.patterns:
                if not pattern.endswith("/"):
                    continue
                directory_pattern = pattern[:-1]
                if "/" in directory_pattern:
                    # Anchored pattern, compare with the path of the directory
                    value = "/".join(segments[: index + 1])
                else:
                    value = segment
                if _match(value, directory_pattern):
                    return Exclusion(ExclusionReason.Pattern, pattern)
        return None

    def directory_exclusion(self, path: str) -> Exclusion | None:
        """Check if a directory is excluded, to skip it while scanning.

        :param path: Normalised relative path of the directory.
        :return: The exclusion, or None if the directory is synchronised.
        """
        return self._directory_exclusion(path.split("/"))

    def file_exclusion(self, path: str, size: int | None = None) -> Exclusion | None:
        """Check if a file is excluded.

        :param path: Normalised relative path of the file.
        :param size: Size in bytes, if known.
        :return: The exclusion, or None if the file is synchronised.
        """
        segments = path.split("/")
        name = segments[-1]

        # A parent directory is excluded
        exclusion = self._directory_exclusion(segments[:-1])
        if exclusion:
            return exclusion

        if name.startswith(INTERNAL_PREFIX):
            return Exclusion(ExclusionReason.Internal, name)

        if self.exclude_hidden and name.startswith("."):
            return Exclusion(ExclusionReason.Hidden, name)

        # File patterns, either on the name or on the whole path
        for pattern in self.patterns:
            if pattern.endswith("/"):
                continue
            value = path if "/" in pattern else name
            if _match(value, pattern):
                return Exclusion(ExclusionReason.Pattern, pattern)

        if self.max_size is not None and size is not None and size > self.max_size:
            return Exclusion(ExclusionReason.Size, str(self.max_size))

        return None
