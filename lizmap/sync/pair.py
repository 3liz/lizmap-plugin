"""Pair of directories synchronised together: a local directory and a directory on the server.

A synchronisation can handle several pairs, displayed as several roots in the same tree:
the Lizmap repository of the project, and the shared "media" directory at the root of the repositories.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from lizmap.sync.model import Direction

if TYPE_CHECKING:
    from pathlib import Path

    from lizmap.sync.backends.base import RemoteBackend
    from lizmap.sync.filters import ExcludeRules
    from lizmap.sync.state import SyncState

# Files missing locally and bigger than this size are not downloaded by default: 50 MiB
DEFAULT_DOWNLOAD_THRESHOLD = 50 * 1024 * 1024


class PairKind(Enum):
    """Kind of pair."""

    # The Lizmap repository, the local directory of the project
    Repository = "repository"
    # The "media" directory at the root of the repositories, "../media" locally
    SharedMedia = "shared_media"


@dataclass(frozen=True)
class PairSettings:
    """Settings of a pair.

    :param direction: Allowed direction of the transfers.
    :param protected_patterns: Glob patterns of the files produced by the server, such as the files
        sent with the web forms: the default and bulk choices never delete nor overwrite them on the server.
    :param download_threshold: Files missing locally and bigger than this size, in bytes,
        are not downloaded by default. None for no limit.
    """

    direction: Direction = Direction.TwoWay
    protected_patterns: tuple[str, ...] = ()
    download_threshold: int | None = DEFAULT_DOWNLOAD_THRESHOLD


DEFAULT_SETTINGS = {
    PairKind.Repository: PairSettings(Direction.TwoWay, ("media/upload/**",)),
    # The shared media mostly receives files from the web forms, the server is the reference
    PairKind.SharedMedia: PairSettings(Direction.PullOnly, ("upload/**",)),
}


@dataclass
class SyncPair:
    """A local directory and a directory on the server, synchronised together.

    :param kind: Kind of pair.
    :param label: Name displayed as the root of the tree.
    :param backend: The directory on the server.
    :param root: The local directory, it may not exist yet.
    :param state: State of the last synchronisation of this pair.
    :param state_file: Where to save the state.
    :param rules: The exclusion rules.
    :param settings: Direction, protected files and download threshold.
    :param remote_label: URL of the directory on the server, displayed to the user.
    """

    kind: PairKind
    label: str
    backend: RemoteBackend
    root: Path
    state: SyncState
    state_file: Path
    rules: ExcludeRules
    settings: PairSettings
    remote_label: str = ""
