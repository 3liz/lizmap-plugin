"""Options of the synchronisation, chosen by the user.

The exclusion rules of a synchronised directory are kept in a file at its root, shared with
the other users. The other options are personal settings.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from lizmap.sync.filters import DEFAULT_EXCLUDE_PATTERNS, IGNORE_FILE, ExcludeRules, parse_rules
from lizmap.sync.pair import DEFAULT_DOWNLOAD_THRESHOLD, DEFAULT_SETTINGS, PairKind

if TYPE_CHECKING:
    from pathlib import Path

    from lizmap.sync.model import Direction
    from lizmap.sync.pair import PairSettings


@dataclass(frozen=True)
class SyncOptions:
    """Personal options of the synchronisation.

    :param exclude_hidden: Exclude files and directories starting with a ".".
    :param max_size: Files bigger than this size, in bytes, are never synchronised. None for no limit.
    :param download_threshold: Files missing locally and bigger than this size, in bytes,
        are not downloaded by default. None for no limit.
    :param protected_repository: Rules of the files produced by the server, in the repository.
    :param protected_shared_media: Rules of the files produced by the server, in the shared media.
    """

    exclude_hidden: bool = True
    max_size: int | None = None
    download_threshold: int | None = DEFAULT_DOWNLOAD_THRESHOLD
    protected_repository: tuple[str, ...] = DEFAULT_SETTINGS[PairKind.Repository].protected_patterns
    protected_shared_media: tuple[str, ...] = DEFAULT_SETTINGS[PairKind.SharedMedia].protected_patterns

    def protected(self, kind: PairKind) -> tuple[str, ...]:
        """Rules of the files produced by the server, for a kind of pair.

        :param kind: The kind of pair.
        :return: The rules.
        """
        return self.protected_repository if kind == PairKind.Repository else self.protected_shared_media

    def exclude_rules(self, patterns: tuple[str, ...]) -> ExcludeRules:
        """Build the exclusion rules of a directory.

        :param patterns: The rules of the directory, from its rules file.
        :return: The exclusion rules, with the personal options.
        """
        return ExcludeRules(patterns=patterns, exclude_hidden=self.exclude_hidden, max_size=self.max_size)

    def pair_settings(self, kind: PairKind, direction: Direction | None = None) -> PairSettings:
        """Build the settings of a pair.

        :param kind: The kind of pair.
        :param direction: The direction chosen by the user, the default one if None.
        :return: The settings.
        """
        settings = replace(
            DEFAULT_SETTINGS[kind],
            protected_patterns=self.protected(kind),
            download_threshold=self.download_threshold,
        )
        return replace(settings, direction=direction) if direction else settings


def read_rules_text(root: Path) -> str | None:
    """Read the rules file of a directory.

    :param root: The synchronised directory.
    :return: The content, None if the file doesn't exist.
    """
    file_path = root.joinpath(IGNORE_FILE)
    if not file_path.is_file():
        return None
    return file_path.read_text(encoding="utf-8", errors="replace")


def read_rules(root: Path) -> tuple[tuple[str, ...], list[str]]:
    """Read the exclusion rules of a directory.

    :param root: The synchronised directory.
    :return: The rules, the default ones if there isn't any rules file, and the unsupported lines.
    """
    content = read_rules_text(root)
    if content is None:
        return DEFAULT_EXCLUDE_PATTERNS, []
    return parse_rules(content)


def write_rules(root: Path, content: str):
    """Write the rules file of a directory, created if needed.

    :param root: The synchronised directory.
    :param content: The rules, with comments.
    """
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath(IGNORE_FILE).write_text(content.rstrip("\n") + "\n", encoding="utf-8")
