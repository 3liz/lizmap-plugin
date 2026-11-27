"""Exclusion rules of the synchronisation.

The rules are written one per line, matched without taking care of the case:

* "*" matches any characters except "/", "?" a single character, "**" any number of directories,
* a rule without "/" matches a file or a directory name at any depth, for instance "*.bak" or "drafts",
* a rule ending with "/" matches only directories, for instance "drafts/",
* a rule starting with "/" or containing a "/" is anchored at the root of the synchronised
  directory, for instance "/exports/" or "data/raw/*.csv",
* empty lines and lines starting with "#" are ignored.

The rules of a directory are kept in the file ``IGNORE_FILE`` at its root. This file is
synchronised like the other files, so the rules are shared with the other users.
"""

from __future__ import annotations

import re

from dataclasses import dataclass
from enum import Enum
from functools import cache

# Prefix of the files and directories of the synchronisation itself: downloads in progress,
# local trash, uploads in progress on the server. They are always excluded, whatever the rules.
INTERNAL_PREFIX = ".~lizmap-"

# File keeping the exclusion rules, at the root of a synchronised directory. Never excluded.
IGNORE_FILE = ".lizmapignore"

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
    :param detail: The matching rule, the hidden name or the size limit in bytes.
    """

    reason: ExclusionReason
    detail: str


@cache
def _glob_regex(pattern: str) -> re.Pattern:
    """Translate a glob pattern into a regular expression.

    :param pattern: The pattern: "*" and "?" don't match "/", "**" matches any number of directories.
    :return: The compiled expression, case insensitive.
    """
    regex = ""
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            regex += "(?:.*/)?"
            index += 3
        elif pattern.startswith("**", index):
            regex += ".*"
            index += 2
        elif pattern[index] == "*":
            regex += "[^/]*"
            index += 1
        elif pattern[index] == "?":
            regex += "[^/]"
            index += 1
        else:
            regex += re.escape(pattern[index])
            index += 1
    return re.compile(regex + r"\Z", re.IGNORECASE)


def match_glob(path: str, pattern: str) -> bool:
    """Match a relative path with a glob pattern supporting "**", such as "media/upload/**".

    :param path: Normalised relative path.
    :param pattern: The pattern, anchored at the root of the synchronised directory.
    :return: True if the path matches.
    """
    return _glob_regex(pattern).match(path) is not None


@dataclass(frozen=True)
class _Rule:
    """A parsed exclusion rule.

    :param text: The rule as written by the user.
    :param glob: The glob pattern, without the leading and trailing "/".
    :param directory_only: The rule matches only directories.
    :param anchored: The rule matches the whole path from the root, not a name at any depth.
    """

    text: str
    glob: str
    directory_only: bool
    anchored: bool

    def matches(self, path: str, is_directory: bool) -> bool:
        """Match a file or a directory.

        :param path: Normalised relative path.
        :param is_directory: True for a directory.
        :return: True if the rule matches.
        """
        if self.directory_only and not is_directory:
            return False
        value = path if self.anchored else path.rsplit("/", 1)[-1]
        return match_glob(value, self.glob)


@cache
def _parse_rule(text: str) -> _Rule:
    """Parse a rule.

    :param text: The rule, already stripped and valid.
    :return: The parsed rule.
    """
    directory_only = text.endswith("/")
    glob = text.strip("/")
    anchored = text.startswith("/") or "/" in glob
    return _Rule(text, glob, directory_only, anchored)


def match_rule(path: str, rule: str, is_directory: bool = False) -> bool:
    """Match a file or a directory with a single rule, see the module documentation.

    :param path: Normalised relative path.
    :param rule: The rule.
    :param is_directory: True for a directory.
    :return: True if the rule matches.
    """
    return _parse_rule(rule).matches(path, is_directory)


def parse_rules(content: str) -> tuple[tuple[str, ...], list[str]]:
    """Read the rules written by the user, one per line.

    :param content: The text, with comments.
    :return: The valid rules, and the lines which are not supported.
    """
    rules = []
    invalid = []
    for line in content.splitlines():
        rule = line.strip()
        if not rule or rule.startswith("#"):
            continue
        # Exceptions and backslashes are not supported
        if rule.startswith("!") or "\\" in rule or rule.strip("/") == "":
            invalid.append(rule)
            continue
        rules.append(rule)
    return tuple(rules), invalid


@dataclass(frozen=True)
class ExcludeRules:
    """Rules telling which files are not synchronised.

    :param patterns: The rules, see the module documentation.
    :param exclude_hidden: Exclude files and directories starting with a ".".
    :param max_size: Files bigger than this size, in bytes, are excluded. None for no limit.
    """

    patterns: tuple[str, ...] = DEFAULT_EXCLUDE_PATTERNS
    exclude_hidden: bool = True
    max_size: int | None = None

    def _exclusion(self, path: str, is_directory: bool) -> Exclusion | None:
        """Check a single file or directory, without its parents.

        :param path: Normalised relative path.
        :param is_directory: True for a directory.
        :return: The exclusion, or None.
        """
        name = path.rsplit("/", 1)[-1]
        if name.startswith(INTERNAL_PREFIX):
            return Exclusion(ExclusionReason.Internal, name)
        if self.exclude_hidden and name.startswith("."):
            return Exclusion(ExclusionReason.Hidden, name)
        for pattern in self.patterns:
            if _parse_rule(pattern).matches(path, is_directory):
                return Exclusion(ExclusionReason.Pattern, pattern)
        return None

    def directory_exclusion(self, path: str) -> Exclusion | None:
        """Check if a directory or one of its parents is excluded, to skip it while scanning.

        :param path: Normalised relative path of the directory.
        :return: The exclusion, or None if the directory is synchronised.
        """
        segments = path.split("/")
        for index in range(len(segments)):
            exclusion = self._exclusion("/".join(segments[: index + 1]), True)
            if exclusion:
                return exclusion
        return None

    def file_exclusion(self, path: str, size: int | None = None) -> Exclusion | None:
        """Check if a file is excluded.

        :param path: Normalised relative path of the file.
        :param size: Size in bytes, if known.
        :return: The exclusion, or None if the file is synchronised.
        """
        # The rules themselves are always synchronised
        if path == IGNORE_FILE:
            return None

        # A parent directory is excluded
        parent = path.rsplit("/", 1)[0] if "/" in path else ""
        if parent:
            exclusion = self.directory_exclusion(parent)
            if exclusion:
                return exclusion

        exclusion = self._exclusion(path, False)
        if exclusion:
            return exclusion

        if self.max_size is not None and size is not None and size > self.max_size:
            return Exclusion(ExclusionReason.Size, str(self.max_size))

        return None
