"""Background tasks of the synchronisation, run by the QGIS task manager.

The tasks don't touch the interface: the dialog reads ``result`` or ``error`` once the task
is completed (``taskCompleted`` signal) or terminated (``taskTerminated`` signal).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qgis.core import QgsFeedback, QgsTask

from lizmap.sync.backends.base import BackendError
from lizmap.sync.diff import compare
from lizmap.sync.executor import SyncExecutor, purge_trash
from lizmap.sync.plan import build_plan
from lizmap.sync.scanner import ScanCanceled, scan_local

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from lizmap.sync.backends.base import RemoteBackend
    from lizmap.sync.diff import Comparison
    from lizmap.sync.executor import SyncResult
    from lizmap.sync.filters import ExcludeRules
    from lizmap.sync.manifest import RemoteManifest
    from lizmap.sync.model import FileStatus, Preference
    from lizmap.sync.scanner import LocalScan
    from lizmap.sync.state import SyncState


@dataclass
class CompareResult:
    """Result of a comparison, with what is needed to run the synchronisation.

    :param comparison: The comparison, one result per file.
    :param manifest: The manifest of the server.
    :param local: The scan of the local directory.
    """

    comparison: Comparison
    manifest: RemoteManifest
    local: LocalScan


def compare_directories(
    backend: RemoteBackend,
    root: Path,
    rules: ExcludeRules,
    state: SyncState,
    preferences: Mapping[FileStatus, Preference] | None = None,
    feedback: QgsFeedback | None = None,
) -> CompareResult:
    """Compare the local directory with the directory on the server.

    :param backend: The directory on the server.
    :param root: The local directory.
    :param rules: The exclusion rules.
    :param state: State of the last synchronisation.
    :param preferences: Default preference by status.
    :param feedback: To cancel.
    :return: The comparison.
    :raises BackendError: If the manifest can't be fetched.
    :raises ScanCanceled: If the user canceled.
    """
    # The manifest first, it gives the maximum size of the checksums
    manifest = backend.fetch_manifest(feedback)
    local = scan_local(root, rules, state.entries, manifest.checksum_max_size, feedback)
    comparison = compare(local.files, manifest.files, state.entries, rules, preferences)
    return CompareResult(comparison=comparison, manifest=manifest, local=local)


class CompareTask(QgsTask):
    """Compare the local directory with the server, in the background.

    :param backend: The directory on the server.
    :param root: The local directory.
    :param rules: The exclusion rules.
    :param state: State of the last synchronisation.
    :param preferences: Default preference by status.
    """

    def __init__(
        self,
        backend: RemoteBackend,
        root: Path,
        rules: ExcludeRules,
        state: SyncState,
        preferences: Mapping[FileStatus, Preference] | None = None,
    ):
        super().__init__("Lizmap - Compare", QgsTask.Flag.CanCancel)
        self.backend = backend
        self.root = root
        self.rules = rules
        self.state = state
        self.preferences = preferences
        self.feedback = QgsFeedback()
        self.result: CompareResult | None = None
        self.error: str | None = None
        # HTTP status of the error, 404 if the directory doesn't exist on the server
        self.error_status: int | None = None

    def run(self) -> bool:
        """Run the comparison, in a worker thread.

        :return: True if the comparison is available in ``result``.
        """
        try:
            self.result = compare_directories(
                self.backend, self.root, self.rules, self.state, self.preferences, self.feedback
            )
        except ScanCanceled:
            return False
        except BackendError as e:
            self.error = str(e)
            self.error_status = e.http_status
            return False
        except OSError as e:
            self.error = str(e)
            return False
        return True

    def cancel(self):
        """Cancel the task, including the request in progress."""
        self.feedback.cancel()
        super().cancel()


class SyncTask(QgsTask):
    """Run the synchronisation in the background, then save the state.

    :param backend: The directory on the server.
    :param root: The local directory.
    :param compare_result: The comparison, with the actions chosen by the user.
    :param state: State of the last synchronisation, updated and saved at the end.
    :param state_file: Where to save the state.
    """

    def __init__(
        self,
        backend: RemoteBackend,
        root: Path,
        compare_result: CompareResult,
        state: SyncState,
        state_file: Path,
    ):
        super().__init__("Lizmap - Synchronise", QgsTask.Flag.CanCancel)
        self.backend = backend
        self.root = root
        self.compare_result = compare_result
        self.state = state
        self.state_file = state_file
        self.feedback = QgsFeedback()
        self.feedback.progressChanged.connect(self.setProgress)
        self.messages: list[str] = []
        self.result: SyncResult | None = None
        self.error: str | None = None

    def run(self) -> bool:
        """Run the synchronisation, in a worker thread.

        :return: True if all operations succeeded.
        """
        manifest = self.compare_result.manifest
        comparison = self.compare_result.comparison
        plan = build_plan(comparison, manifest.dirs)

        executor = SyncExecutor(
            self.backend, self.root, self.state, manifest.checksum_max_size, log=self.messages.append
        )
        try:
            purge_trash(self.root)
            self.result = executor.run(comparison, plan, self.feedback)
            # The state is saved even after a cancellation, for the operations already run
            self.state.save(self.state_file)
        except OSError as e:
            self.error = str(e)
            return False
        return self.result.success

    def cancel(self):
        """Cancel the task, including the transfer in progress."""
        self.feedback.cancel()
        super().cancel()
