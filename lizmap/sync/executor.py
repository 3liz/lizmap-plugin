"""Execution of the synchronisation plan.

Safety rules:

* a local file modified, created or deleted since the comparison is never touched, the operation
  is reported as a conflict,
* a file modified on the server since the comparison is never overwritten nor deleted, thanks to
  the ETag preconditions of the backend,
* a local file replaced by a download or deleted is first kept in a local trash,
  ``.~lizmap-trash/<date>/`` in the local directory, never synchronised,
* deletions are run at the end, after all transfers.

Once the operations are run, the manifest is fetched again, to verify the operations on the server
(transfers with the checksums, deletions, created directories) and to record the new state of the
synchronised files. Directories are never deleted, except those emptied by the deletions of the
synchronisation itself: an empty directory existing before is kept.
"""

from __future__ import annotations

import os
import shutil
import time

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from qgis.core import QgsFeedback
from qgis.PyQt.QtCore import Qt

from lizmap.sync.backends.base import BackendCanceled, BackendError
from lizmap.sync.filters import INTERNAL_PREFIX
from lizmap.sync.model import FileStatus
from lizmap.sync.paths import parent_directories
from lizmap.sync.plan import OperationKind
from lizmap.sync.scanner import stat_local

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from lizmap.sync.backends.base import RemoteBackend
    from lizmap.sync.diff import Comparison
    from lizmap.sync.manifest import RemoteManifest
    from lizmap.sync.model import FileDiff, LocalEntry
    from lizmap.sync.plan import SyncOperation
    from lizmap.sync.state import SyncState

TRASH_DIRECTORY = INTERNAL_PREFIX + "trash"

# Weight of an operation in the progress, in addition to its size, so small files count too
OPERATION_WEIGHT = 64 * 1024


class LocalConflict(Exception):
    """The local file changed since the comparison."""


@dataclass
class SyncResult:
    """Result of the synchronisation.

    :param done: Operations run successfully.
    :param conflicts: Files skipped because they changed since the comparison, with the reason.
    :param errors: Files in error, with the message.
    :param canceled: True if the user canceled before the end.
    :param trash: Directory where replaced or deleted local files have been kept, if any.
    :param removed_local_directories: Local directories emptied by the synchronisation, then removed.
    :param removed_remote_directories: Directories on the server emptied by the synchronisation, then removed.
    """

    done: list[SyncOperation] = field(default_factory=list)
    conflicts: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    canceled: bool = False
    trash: Path | None = None
    removed_local_directories: list[str] = field(default_factory=list)
    removed_remote_directories: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Tell if everything has been run.

        :return: True if there isn't any conflict, error nor cancellation.
        """
        return not (self.conflicts or self.errors or self.canceled)


def purge_trash(root: Path, keep_days: int = 30, now: float | None = None):
    """Remove the trash directories older than a number of days.

    :param root: The local directory.
    :param keep_days: Number of days to keep.
    :param now: Current time in seconds, for the tests.
    """
    trash = root.joinpath(TRASH_DIRECTORY)
    if not trash.is_dir():
        return

    limit = (time.time() if now is None else now) - keep_days * 86400
    for session in trash.iterdir():
        if session.is_dir() and session.stat().st_mtime < limit:
            shutil.rmtree(session, ignore_errors=True)


def child_feedback(parent: QgsFeedback | None, start: float, width: float) -> QgsFeedback | None:
    """Build a feedback for a part of a task, linked to the global feedback.

    The caller must disconnect ``parent.canceled`` from ``child.cancel`` once the part is done.

    :param parent: The global feedback.
    :param start: Global progress at the beginning of the part, in percent.
    :param width: Size of the part in the global progress, in percent.
    :return: The feedback of the part, None if there isn't any global feedback.
    """
    if parent is None:
        return None

    child = QgsFeedback()
    child.progressChanged.connect(lambda progress: parent.setProgress(start + progress * width / 100))
    # Direct connection, the cancellation must be immediate even if the parent is in another thread
    parent.canceled.connect(child.cancel, type=Qt.ConnectionType.DirectConnection)
    if parent.isCanceled():
        child.cancel()
    return child


class SyncExecutor:
    """Run the operations of a synchronisation plan.

    :param backend: The directory on the server.
    :param root: The local directory.
    :param state: State of the last synchronisation, updated at the end.
    :param checksum_max_size: Files bigger than this size don't get a checksum, None for no limit.
    :param log: Function receiving a message for each operation.
    """

    def __init__(
        self,
        backend: RemoteBackend,
        root: Path,
        state: SyncState,
        checksum_max_size: int | None = None,
        log: Callable[[str], None] | None = None,
    ):
        self.backend = backend
        self.root = root
        self.state = state
        self.checksum_max_size = checksum_max_size
        self.log = log or (lambda _message: None)
        self.trash = root.joinpath(TRASH_DIRECTORY, time.strftime("%Y-%m-%d_%H-%M-%S"))
        self._trash_used = False

    def run(
        self, comparison: Comparison, plan: list[SyncOperation], feedback: QgsFeedback | None = None
    ) -> SyncResult:
        """Run the plan, then update the state.

        Each operation is independent: a conflict or an error is reported and the next operation is run.

        :param comparison: The comparison used to build the plan.
        :param plan: The operations, from ``build_plan``.
        :param feedback: To cancel and follow the progress.
        :return: The result.
        """
        result = SyncResult()
        weights = [op.size + OPERATION_WEIGHT for op in plan]
        total = sum(weights) or 1
        done_weight = 0

        for operation, weight in zip(plan, weights, strict=True):
            if feedback and feedback.isCanceled():
                result.canceled = True
                break

            # A feedback for the operation, reporting its progress as a part of the global progress
            child = child_feedback(feedback, 100.0 * done_weight / total, 100.0 * weight / total)
            try:
                self._run_operation(operation, child)
                result.done.append(operation)
                self.log(f"{operation.kind.value} : {operation.path}")
            except LocalConflict as e:
                result.conflicts[operation.path] = str(e)
                self.log(f"Conflict {operation.path} : {e}")
            except BackendCanceled:
                result.canceled = True
                break
            except BackendError as e:
                if e.is_conflict:
                    result.conflicts[operation.path] = "Modified on the server since the comparison"
                else:
                    result.errors[operation.path] = str(e)
                self.log(f"Error {operation.path} : {e}")
            except OSError as e:
                result.errors[operation.path] = str(e)
                self.log(f"Error {operation.path} : {e}")
            finally:
                if feedback and child:
                    feedback.canceled.disconnect(child.cancel)

            done_weight += weight
            if feedback:
                feedback.setProgress(100.0 * done_weight / total)

        self._finish(comparison, result)
        if self._trash_used:
            result.trash = self.trash
        return result

    def _run_operation(self, operation: SyncOperation, feedback: QgsFeedback | None):
        """Run a single operation.

        :param operation: The operation.
        :param feedback: To cancel and follow the progress.
        :raises LocalConflict: If the local file changed since the comparison.
        :raises BackendError: If a request failed.
        :raises OSError: If a local file can't be read or written.
        """
        path = operation.path
        if operation.kind == OperationKind.MakeRemoteDirectory:
            self.backend.make_directory(path, feedback)
            return

        diff = operation.diff
        if diff is None:
            raise ValueError(f"The operation on '{path}' doesn't have any comparison result.")
        self._check_local_unchanged(diff)
        local_file = self.root.joinpath(path)
        remote_etag = diff.remote.etag if diff.remote else None

        if operation.kind == OperationKind.Upload:
            self.backend.upload(local_file, path, remote_etag, feedback)
        elif operation.kind == OperationKind.Download:
            if diff.local:
                self._keep_in_trash(path, move=False)
            checksum = diff.remote.checksum if diff.remote else None
            self.backend.download(path, local_file, remote_etag, checksum, feedback)
        elif operation.kind == OperationKind.DeleteRemote:
            self.backend.delete(path, remote_etag, feedback)
        elif operation.kind == OperationKind.DeleteLocal:
            self._keep_in_trash(path, move=True)

    def _check_local_unchanged(self, diff: FileDiff):
        """Check that the local file didn't change since the comparison.

        :param diff: The comparison result of the file.
        :raises LocalConflict: If the file has been created, modified or deleted since the comparison.
        """
        try:
            stat = self.root.joinpath(diff.path).stat()
        except FileNotFoundError:
            stat = None

        if diff.local is None:
            if stat is not None:
                raise LocalConflict("Created locally since the comparison")
            return

        if stat is None:
            raise LocalConflict("Deleted locally since the comparison")
        if stat.st_size != diff.local.size or stat.st_mtime_ns != diff.local.mtime_ns:
            raise LocalConflict("Modified locally since the comparison")

    def _keep_in_trash(self, path: str, move: bool):
        """Keep a local file in the trash before replacing or deleting it.

        :param path: Normalised relative path of the file.
        :param move: Move the file, for a deletion. Otherwise, the file is linked or copied,
            because the download replaces it only once complete.
        """
        source = self.root.joinpath(path)
        target = self.trash.joinpath(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._trash_used = True

        if move:
            os.replace(source, target)
            return

        # A hard link is instant and doesn't use any space, a copy is needed on some file systems
        try:
            os.link(source, target)
        except OSError:
            shutil.copy2(source, target)

    def _finish(self, comparison: Comparison, result: SyncResult):
        """Verify the operations, record the new state and remove the emptied directories.

        :param comparison: The comparison used to build the plan.
        :param result: The result, completed with the errors found while verifying the operations.
        """
        # Files deleted on both sides
        self.state.prune(comparison.stale_paths)

        # Identical files, recorded so the next comparison knows they are synchronised
        for diff in comparison.diffs:
            if diff.status == FileStatus.Identical and diff.local and diff.remote:
                self.state.record(diff.local, diff.remote)

        # Local deletions, done on the disk
        deleted_local = [op.path for op in result.done if op.kind == OperationKind.DeleteLocal]
        for path in deleted_local:
            self.state.forget(path)
        self._remove_local_directories(deleted_local, result)

        remote_operations = [op for op in result.done if op.kind != OperationKind.DeleteLocal]
        if not remote_operations:
            return

        # The manifest tells what really happened on the server
        try:
            manifest = self.backend.fetch_manifest()
        except BackendError as e:
            self.log(f"The operations on the server can't be verified : {e}")
            for operation in remote_operations:
                if operation.kind == OperationKind.DeleteRemote:
                    self.state.forget(operation.path)
            return

        failed = []
        for operation in remote_operations:
            error = self._verify(operation, manifest)
            if error:
                result.errors[operation.path] = error
                failed.append(operation)
        result.done = [op for op in result.done if op not in failed]

        deleted_remote = [op.path for op in result.done if op.kind == OperationKind.DeleteRemote]
        self._remove_remote_directories(deleted_remote, manifest, result)

    def _verify(self, operation: SyncOperation, manifest: RemoteManifest) -> str | None:
        """Verify an operation on the server with the final manifest, and record the new state.

        :param operation: An operation done on the server.
        :param manifest: The manifest fetched after all operations.
        :return: An error message, None if the operation is verified.
        """
        path = operation.path
        if operation.kind == OperationKind.MakeRemoteDirectory:
            # The root directory itself is not listed, the manifest exists if it has been created
            return None if path == "" or path in manifest.dirs else "Directory not created on the server"

        if operation.kind == OperationKind.DeleteRemote:
            if path in manifest.files:
                return "Still on the server after the deletion"
            self.state.forget(path)
            return None

        # Transfers
        remote = manifest.files.get(path)
        previous: LocalEntry | None = operation.diff.local if operation.diff else None
        local = stat_local(self.root, path, self.checksum_max_size, previous)
        if remote is None or local is None:
            return "Missing after the transfer"

        # Verify the content when both checksums are known
        if local.checksum and remote.checksum and local.checksum != remote.checksum:
            return "Different content after the transfer"

        self.state.record(local, remote)
        return None

    @staticmethod
    def _emptied_candidates(deleted: list[str]) -> list[str]:
        """List the parent directories of deleted files, the deepest first.

        :param deleted: Relative paths of the deleted files.
        :return: The directories which may have been emptied.
        """
        directories = {directory for path in deleted for directory in parent_directories(path)}
        return sorted(directories, key=lambda directory: (-directory.count("/"), directory))

    def _remove_local_directories(self, deleted: list[str], result: SyncResult):
        """Remove the local directories emptied by the deletions of the synchronisation.

        :param deleted: Relative paths of the deleted local files.
        :param result: The result, completed with the removed directories.
        """
        for directory in self._emptied_candidates(deleted):
            try:
                # Fails if the directory is not empty, nothing else to check
                self.root.joinpath(directory).rmdir()
            except OSError:
                continue
            result.removed_local_directories.append(directory)
            self.log(f"Local directory removed : {directory}")

    def _remove_remote_directories(self, deleted: list[str], manifest: RemoteManifest, result: SyncResult):
        """Remove the directories on the server emptied by the deletions of the synchronisation.

        The server refuses to delete a directory which is not empty anymore, for instance if someone
        added a file in the meantime.

        :param deleted: Relative paths of the files deleted on the server.
        :param manifest: The manifest fetched after all operations.
        :param result: The result, completed with the removed directories.
        """
        files = set(manifest.files)
        directories = set(manifest.dirs)
        for directory in self._emptied_candidates(deleted):
            prefix = directory + "/"
            if directory not in directories:
                continue
            if any(f.startswith(prefix) for f in files) or any(d.startswith(prefix) for d in directories):
                continue
            try:
                self.backend.delete_empty_directory(directory)
            except BackendError as e:
                self.log(f"Directory {directory} kept on the server : {e}")
                continue
            directories.discard(directory)
            result.removed_remote_directories.append(directory)
            self.log(f"Directory removed on the server : {directory}")
