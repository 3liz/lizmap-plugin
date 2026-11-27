"""State of the last synchronisation.

For each synchronised file, the state stores what was on both sides just after the transfer.
It's the "base" of the three-way comparison: without it, a file only on one side can be either new
on this side or deleted on the other side, and a modified file can't be attributed to one side.

The state is saved as JSON, outside the project directory (in the QGIS profile), one file per
server, repository and local directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lizmap.sync.model import BaseEntry

if TYPE_CHECKING:
    from collections.abc import Iterable

    from lizmap.sync.model import LocalEntry, RemoteEntry

STATE_FORMAT_VERSION = 1


class StateError(ValueError):
    """The state file is not valid or doesn't belong to the given synchronisation."""


def state_file_name(server: str, repository: str, local_dir: str) -> str:
    """Name of the state file for a synchronisation.

    :param server: URL of the Lizmap Web Client server.
    :param repository: Identifier of the Lizmap repository.
    :param local_dir: Absolute path of the local directory.
    :return: A file name, based on a hash of the parameters.
    """
    key = "\n".join((server, repository, local_dir))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32] + ".json"


@dataclass
class SyncState:
    """State of the last synchronisation between a local directory and a repository.

    :param server: URL of the Lizmap Web Client server.
    :param repository: Identifier of the Lizmap repository.
    :param local_dir: Absolute path of the local directory.
    :param entries: Base entries, by normalised relative path.
    :param updated_at: Last update of the state, in seconds since the epoch.
    """

    server: str
    repository: str
    local_dir: str
    entries: dict[str, BaseEntry] = field(default_factory=dict)
    updated_at: int = 0

    def record(self, local: LocalEntry, remote: RemoteEntry, now: int | None = None):
        """Record a file as synchronised, after a transfer or when both sides are identical.

        :param local: The local entry, after the transfer.
        :param remote: The remote entry, after the transfer.
        :param now: Current time in seconds, for the tests.
        :raises ValueError: If both entries don't have the same path.
        """
        if local.path != remote.path:
            raise ValueError(f"Different paths '{local.path}' and '{remote.path}'.")

        now = int(time.time()) if now is None else now
        self.entries[local.path] = BaseEntry(
            local_size=local.size,
            local_mtime_ns=local.mtime_ns,
            local_checksum=local.checksum,
            remote_size=remote.size,
            remote_mtime=remote.mtime,
            remote_etag=remote.etag,
            remote_checksum=remote.checksum,
            synced_at=now,
        )
        self.updated_at = now

    def forget(self, path: str):
        """Remove a file from the state, after a deletion on both sides.

        :param path: Normalised relative path.
        """
        self.entries.pop(path, None)

    def prune(self, paths: Iterable[str]):
        """Remove several files from the state, such as files deleted on both sides.

        :param paths: Normalised relative paths.
        """
        for path in paths:
            self.forget(path)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the state.

        :return: A JSON compatible dictionary.
        """
        return {
            "version": STATE_FORMAT_VERSION,
            "server": self.server,
            "repository": self.repository,
            "local_dir": self.local_dir,
            "updated_at": self.updated_at,
            "entries": {path: asdict(entry) for path, entry in sorted(self.entries.items())},
        }

    @classmethod
    def from_dict(cls, data: Any) -> SyncState:
        """Deserialise a state.

        :param data: Dictionary built by ``to_dict``.
        :return: The state.
        :raises StateError: If the content is not valid.
        """
        if not isinstance(data, dict) or data.get("version") != STATE_FORMAT_VERSION:
            raise StateError("Unsupported version of the synchronisation state.")

        try:
            entries = {str(path): BaseEntry(**values) for path, values in data["entries"].items()}
            return cls(
                server=str(data["server"]),
                repository=str(data["repository"]),
                local_dir=str(data["local_dir"]),
                entries=entries,
                updated_at=int(data["updated_at"]),
            )
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            raise StateError(f"Invalid synchronisation state : {e}") from e

    def save(self, file_path: Path):
        """Save the state, atomically.

        The content is written in a temporary file in the same directory, then renamed, so a crash
        never leaves a truncated state.

        :param file_path: Destination of the state file.
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=file_path.parent, prefix=f".{file_path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=1)
            os.replace(temporary, file_path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, file_path: Path, server: str, repository: str, local_dir: str) -> SyncState:
        """Load the state of a synchronisation.

        :param file_path: The state file.
        :param server: URL of the Lizmap Web Client server.
        :param repository: Identifier of the Lizmap repository.
        :param local_dir: Absolute path of the local directory.
        :return: The saved state, or an empty state if the file doesn't exist yet.
        :raises StateError: If the file is not valid or belongs to another synchronisation.
        """
        if not file_path.exists():
            return cls(server=server, repository=repository, local_dir=local_dir)

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise StateError(f"The synchronisation state can't be read : {e}") from e

        state = cls.from_dict(data)

        # Protection against a hash collision or a file copied by hand
        if (state.server, state.repository, state.local_dir) != (server, repository, local_dir):
            raise StateError("The synchronisation state belongs to another directory or repository.")
        return state
