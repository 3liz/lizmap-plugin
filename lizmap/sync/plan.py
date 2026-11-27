"""Plan of the synchronisation: the ordered list of operations to run."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from lizmap.sync.model import SyncAction
from lizmap.sync.paths import parent_directories

if TYPE_CHECKING:
    from collections.abc import Iterable

    from lizmap.sync.diff import Comparison
    from lizmap.sync.model import FileDiff


class OperationKind(Enum):
    """Kind of operation, in the order they are run."""

    MakeRemoteDirectory = "make_remote_directory"
    Upload = "upload"
    Download = "download"
    DeleteRemote = "delete_remote"
    DeleteLocal = "delete_local"


_KINDS = {
    SyncAction.Upload: OperationKind.Upload,
    SyncAction.Download: OperationKind.Download,
    SyncAction.DeleteRemote: OperationKind.DeleteRemote,
    SyncAction.DeleteLocal: OperationKind.DeleteLocal,
}

# Order of the operations: directories first, transfers, then deletions
_ORDER = {kind: index for index, kind in enumerate(OperationKind)}


@dataclass(frozen=True)
class SyncOperation:
    """An operation of the synchronisation.

    :param kind: Kind of operation.
    :param path: Normalised relative path of the file or of the directory.
    :param diff: The comparison result of the file, None for a directory.
    """

    kind: OperationKind
    path: str
    diff: FileDiff | None = None

    @property
    def size(self) -> int:
        """Number of bytes to transfer.

        :return: The size of the file for a transfer, 0 otherwise.
        """
        return self.diff.transfer_size if self.diff else 0


def build_plan(comparison: Comparison, remote_dirs: Iterable[str]) -> list[SyncOperation]:
    """Build the ordered list of operations from the chosen actions.

    Missing remote directories are created first, parents before children, then files are
    uploaded and downloaded, and deletions are run at the end, so a failed transfer never
    follows a deletion.

    :param comparison: The comparison, with the action chosen for each file.
    :param remote_dirs: Directories already existing on the server.
    :return: The operations, in the order they must be run.
    """
    existing = set(remote_dirs)
    operations = []

    for diff in comparison.to_run():
        kind = _KINDS[diff.action]
        operations.append(SyncOperation(kind, diff.path, diff))

        # Parent directories needed on the server for an upload
        if kind == OperationKind.Upload:
            for directory in parent_directories(diff.path):
                if directory not in existing:
                    existing.add(directory)
                    operations.append(SyncOperation(OperationKind.MakeRemoteDirectory, directory))

    # Parents are shorter than their children, so sorting by path keeps them first
    return sorted(operations, key=lambda op: (_ORDER[op.kind], op.path))
