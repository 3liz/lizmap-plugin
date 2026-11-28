"""Background tasks of the synchronisation, run by the QGIS task manager.

A task handles all the pairs of directories of the synchronisation, one after the other.
The tasks don't touch the interface: the dialog reads ``results`` and ``errors`` once the task
is completed (``taskCompleted`` signal) or terminated (``taskTerminated`` signal).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qgis.core import QgsFeedback, QgsTask

from lizmap.sync.backends.base import BackendCanceled, BackendError
from lizmap.sync.diff import compare
from lizmap.sync.executor import OPERATION_WEIGHT, SyncExecutor, child_feedback, purge_trash
from lizmap.sync.manifest import RemoteManifest
from lizmap.sync.plan import build_plan
from lizmap.sync.scanner import LocalScan, ScanCanceled, scan_local

if TYPE_CHECKING:
    from collections.abc import Mapping

    from lizmap.sync.diff import Comparison
    from lizmap.sync.executor import SyncResult
    from lizmap.sync.model import FileStatus, Preference
    from lizmap.sync.pair import PairKind, PairSettings, SyncPair

HTTP_NOT_FOUND = 404


@dataclass
class CompareResult:
    """Result of the comparison of a pair, with what is needed to run the synchronisation.

    :param pair: The pair of directories.
    :param comparison: The comparison, one result per file.
    :param manifest: The manifest of the server, empty if the directory doesn't exist on the server.
    :param local: The scan of the local directory, empty if it doesn't exist.
    :param remote_exists: False if the directory doesn't exist yet on the server.
    """

    pair: SyncPair
    comparison: Comparison
    manifest: RemoteManifest
    local: LocalScan
    remote_exists: bool = True


def _compare(
    pair: SyncPair,
    manifest: RemoteManifest,
    local: LocalScan,
    preferences: Mapping[FileStatus, Preference] | None,
) -> Comparison:
    """Compare a pair with its settings.

    :param pair: The pair.
    :param manifest: The manifest of the server.
    :param local: The scan of the local directory.
    :param preferences: Default preference by status.
    :return: The comparison.
    """
    return compare(
        local.files,
        manifest.files,
        pair.state.entries,
        pair.rules,
        preferences,
        direction=pair.settings.direction,
        protected_patterns=pair.settings.protected_patterns,
        download_threshold=pair.settings.download_threshold,
    )


def compare_pair(
    pair: SyncPair,
    preferences: Mapping[FileStatus, Preference] | None = None,
    feedback: QgsFeedback | None = None,
) -> CompareResult:
    """Compare the local directory with the directory on the server.

    A directory missing on the server or locally is considered as empty: it will be created
    by the first upload or download.

    :param pair: The pair.
    :param preferences: Default preference by status.
    :param feedback: To cancel.
    :return: The comparison.
    :raises BackendError: If the manifest can't be fetched.
    :raises ScanCanceled: If the user canceled.
    """
    # The manifest first, it gives the maximum size of the checksums
    remote_exists = True
    try:
        manifest = pair.backend.fetch_manifest(feedback)
    except BackendError as e:
        if e.http_status != HTTP_NOT_FOUND:
            raise
        remote_exists = False
        manifest = RemoteManifest("1.0", "", 0, "sha256", None, frozenset(), {})

    local = LocalScan()
    if pair.root.is_dir():
        local = scan_local(pair.root, pair.rules, pair.state.entries, manifest.checksum_max_size, feedback)

    comparison = _compare(pair, manifest, local, preferences)
    return CompareResult(pair, comparison, manifest, local, remote_exists)


def recompare(
    result: CompareResult,
    settings: PairSettings,
    preferences: Mapping[FileStatus, Preference] | None = None,
) -> CompareResult:
    """Compare a pair again with other settings, without any request nor scan.

    :param result: The previous comparison of the pair.
    :param settings: The new settings, also stored in the pair.
    :param preferences: Default preference by status.
    :return: The new comparison.
    """
    result.pair.settings = settings
    comparison = _compare(result.pair, result.manifest, result.local, preferences)
    return CompareResult(result.pair, comparison, result.manifest, result.local, result.remote_exists)


class CompareTask(QgsTask):
    """Compare all pairs in the background.

    :param pairs: The pairs of directories.
    :param preferences: Default preference by status.
    """

    def __init__(self, pairs: list[SyncPair], preferences: Mapping[FileStatus, Preference] | None = None):
        super().__init__("Lizmap - Compare", QgsTask.Flag.CanCancel)
        self.pairs = pairs
        self.preferences = preferences
        self.feedback = QgsFeedback()
        self.results: list[CompareResult] = []
        # Error by pair, the other pairs are still compared
        self.errors: dict[PairKind, str] = {}

    def run(self) -> bool:
        """Run the comparisons, in a worker thread.

        :return: True if at least one pair has been compared, without cancellation.
        """
        for pair in self.pairs:
            try:
                self.results.append(compare_pair(pair, self.preferences, self.feedback))
            except (ScanCanceled, BackendCanceled):
                return False
            except (BackendError, OSError) as e:
                self.errors[pair.kind] = str(e)
        return bool(self.results)

    def cancel(self):
        """Cancel the task, including the request in progress."""
        self.feedback.cancel()
        super().cancel()


class SyncTask(QgsTask):
    """Run the synchronisation of all pairs in the background, then save their states.

    :param results: The comparisons, with the actions chosen by the user.
    """

    def __init__(self, results: list[CompareResult]):
        super().__init__("Lizmap - Synchronise", QgsTask.Flag.CanCancel)
        self.compare_results = results
        self.feedback = QgsFeedback()
        self.feedback.progressChanged.connect(self.setProgress)
        self.messages: list[str] = []
        self.results: dict[PairKind, SyncResult] = {}
        self.errors: dict[PairKind, str] = {}

    def run(self) -> bool:
        """Run the synchronisation, in a worker thread.

        Each pair is run even without any operation, to record the identical files in its state.

        :return: True if all operations of all pairs succeeded.
        """
        plans = [
            build_plan(result.comparison, result.manifest.dirs, create_root=not result.remote_exists)
            for result in self.compare_results
        ]
        # Part of the progress of each pair
        weights = [sum(op.size + OPERATION_WEIGHT for op in plan) + 1 for plan in plans]
        total = sum(weights)
        start = 0.0

        for compare_result, plan, weight in zip(self.compare_results, plans, weights, strict=True):
            pair = compare_result.pair
            width = 100.0 * weight / total
            feedback = child_feedback(self.feedback, start, width)
            start += width

            def log(message: str, label: str = pair.label):
                """Keep a message, prefixed by the pair.

                :param message: The message.
                :param label: Name of the pair.
                """
                self.messages.append(f"{label} : {message}")

            executor = SyncExecutor(
                pair.backend, pair.root, pair.state, compare_result.manifest.checksum_max_size, log=log
            )
            try:
                purge_trash(pair.root)
                result = executor.run(compare_result.comparison, plan, feedback)
                # The state is saved even after a cancellation, for the operations already run
                pair.state.save(pair.state_file)
            except OSError as e:
                self.errors[pair.kind] = str(e)
                continue
            finally:
                if feedback:
                    self.feedback.canceled.disconnect(feedback.cancel)

            self.results[pair.kind] = result
            if result.canceled:
                break

        return not self.errors and all(result.success for result in self.results.values())

    def cancel(self):
        """Cancel the task, including the transfer in progress."""
        self.feedback.cancel()
        super().cancel()
