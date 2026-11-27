"""Test the plan and the execution of the synchronisation, with a backend in memory."""

import hashlib
import os
import time

from pathlib import Path

from qgis.core import QgsFeedback

from lizmap.sync.backends.base import BackendError
from lizmap.sync.executor import TRASH_DIRECTORY, SyncExecutor, SyncResult, purge_trash
from lizmap.sync.filters import ExcludeRules
from lizmap.sync.manifest import RemoteManifest
from lizmap.sync.model import Direction, FileStatus, RemoteEntry, SyncAction
from lizmap.sync.pair import PairKind, PairSettings, SyncPair
from lizmap.sync.paths import parent_directories
from lizmap.sync.plan import OperationKind, build_plan
from lizmap.sync.state import SyncState
from lizmap.sync.tasks import CompareResult, compare_pair, recompare


class FakeBackend:
    """A directory on a server, in memory."""

    def __init__(self):
        """Empty directory."""
        self.files: dict[str, bytes] = {}
        self.etags: dict[str, str] = {}
        self.dirs: set[str] = set()
        self.calls: list[tuple[str, str]] = []
        self.counter = 0
        # Content stored instead of the sent one, to simulate a corrupted upload
        self.corrupt: bytes | None = None
        # Simulate a server reporting a success without doing anything, like Sabre before the fix
        self.silent_failures = False

    def put(self, path: str, content: bytes):
        """Store a file directly, as if another user sent it.

        :param path: Relative path.
        :param content: Content.
        """
        self.counter += 1
        self.files[path] = content
        self.etags[path] = f'"{self.counter}"'
        self.dirs.update(parent_directories(path))

    def fetch_manifest(self, feedback: QgsFeedback | None = None) -> RemoteManifest:
        """Build the manifest.

        :param feedback: Not used.
        :return: The manifest.
        """
        files = {
            path: RemoteEntry(path, len(content), 1000, self.etags[path], hashlib.sha256(content).hexdigest())
            for path, content in self.files.items()
        }
        return RemoteManifest("1.0", "", 0, "sha256", None, frozenset(self.dirs), files)

    def make_directory(self, path: str, feedback: QgsFeedback | None = None):
        """Create a directory.

        :param path: Relative path.
        :param feedback: Not used.
        """
        self.calls.append(("mkdir", path))
        if not self.silent_failures:
            self.dirs.add(path)

    def upload(
        self, local_file: Path, path: str, etag: str | None, feedback: QgsFeedback | None = None
    ) -> str:
        """Store a file, with the ETag preconditions.

        :param local_file: Local file.
        :param path: Relative path.
        :param etag: Expected ETag, None for a new file.
        :param feedback: Not used.
        :return: The new ETag.
        """
        self.calls.append(("upload", path))
        if etag != self.etags.get(path):
            raise BackendError("Precondition failed", 412)
        if "/" in path and path.rsplit("/", 1)[0] not in self.dirs:
            raise BackendError("Missing parent", 409)
        self.put(path, self.corrupt if self.corrupt is not None else local_file.read_bytes())
        return self.etags[path]

    def download(self, path: str, local_file: Path, feedback: QgsFeedback | None = None) -> str:
        """Write a file locally, by renaming a temporary file like the real backend.

        :param path: Relative path.
        :param local_file: Local file.
        :param feedback: Not used.
        :return: The ETag.
        """
        self.calls.append(("download", path))
        local_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = local_file.parent / ".~lizmap-download-test"
        temporary.write_bytes(self.files[path])
        os.replace(temporary, local_file)
        return self.etags[path]

    def delete(self, path: str, etag: str | None, feedback: QgsFeedback | None = None):
        """Delete a file, with the ETag precondition.

        :param path: Relative path.
        :param etag: Expected ETag.
        :param feedback: Not used.
        """
        self.calls.append(("delete", path))
        if etag and self.etags.get(path) not in (None, etag):
            raise BackendError("Precondition failed", 412)
        if not self.silent_failures:
            self.files.pop(path, None)
            self.etags.pop(path, None)

    def delete_empty_directory(self, path: str, feedback: QgsFeedback | None = None):
        """Delete a directory, only if it's empty.

        :param path: Relative path.
        :param feedback: Not used.
        """
        self.calls.append(("rmdir", path))
        prefix = path + "/"
        if any(p.startswith(prefix) for p in self.files) or any(d.startswith(prefix) for d in self.dirs):
            raise BackendError("The directory is not empty.", 409)
        self.dirs.discard(path)


def write(path: Path, content: bytes):
    """Write a local file and its parents.

    :param path: The file.
    :param content: The content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


# Settings of the tests: two-way, without protected files nor download threshold
TEST_SETTINGS = PairSettings(download_threshold=None)


def make_pair(
    backend: FakeBackend,
    root: Path,
    state: SyncState,
    settings: PairSettings = TEST_SETTINGS,
    kind: PairKind = PairKind.Repository,
    state_file: Path | None = None,
) -> SyncPair:
    """Build a pair of directories for the tests.

    :param backend: The backend.
    :param root: The local directory.
    :param state: The state.
    :param settings: The settings of the pair.
    :param kind: The kind of pair.
    :param state_file: Where to save the state, next to the local directory if None.
    :return: The pair.
    """
    return SyncPair(
        kind=kind,
        label=kind.value,
        backend=backend,
        root=root,
        state=state,
        state_file=state_file or root.parent / f"{root.name}-{kind.value}-state.json",
        rules=ExcludeRules(),
        settings=settings,
        remote_label="memory",
    )


def compare_now(
    backend: FakeBackend, root: Path, state: SyncState, settings: PairSettings = TEST_SETTINGS
) -> CompareResult:
    """Compare with the default rules and preferences.

    :param backend: The backend.
    :param root: The local directory.
    :param state: The state.
    :param settings: The settings of the pair.
    :return: The comparison.
    """
    return compare_pair(make_pair(backend, root, state, settings))


def sync_now(
    backend: FakeBackend,
    root: Path,
    state: SyncState,
    result: CompareResult,
    feedback: QgsFeedback | None = None,
) -> SyncResult:
    """Run the synchronisation of a comparison.

    :param backend: The backend.
    :param root: The local directory.
    :param state: The state.
    :param result: The comparison.
    :param feedback: Optional feedback.
    :return: The synchronisation result.
    """
    plan = build_plan(result.comparison, result.manifest.dirs)
    return SyncExecutor(backend, root, state).run(result.comparison, plan, feedback)


def statuses(result: CompareResult) -> dict:
    """Statuses of the files.

    :param result: The comparison.
    :return: Status by path.
    """
    return {diff.path: diff.status for diff in result.comparison.diffs}


def test_build_plan(tmp_path: Path):
    """Test the order of the operations and the creation of the remote directories."""
    backend = FakeBackend()
    backend.put("a/remote.txt", b"r")
    backend.put("old.txt", b"o")
    write(tmp_path / "a" / "b" / "c.txt", b"c")
    write(tmp_path / "a" / "d.txt", b"d")
    state = SyncState("s", "r", str(tmp_path))
    result = compare_now(backend, tmp_path, state)
    # Deletion chosen by the user
    next(diff for diff in result.comparison.diffs if diff.path == "old.txt").choose(SyncAction.DeleteRemote)

    plan = build_plan(result.comparison, result.manifest.dirs)
    assert [(op.kind, op.path) for op in plan] == [
        (OperationKind.MakeRemoteDirectory, "a/b"),
        (OperationKind.Upload, "a/b/c.txt"),
        (OperationKind.Upload, "a/d.txt"),
        (OperationKind.Download, "a/remote.txt"),
        (OperationKind.DeleteRemote, "old.txt"),
    ]


def test_full_sync(tmp_path: Path):
    """Test a first synchronisation, then a second comparison with everything synchronised."""
    backend = FakeBackend()
    backend.put("media/logo.png", b"logo")
    backend.put("project.qgs.cfg", b"{}")
    write(tmp_path / "project.qgs", b"<qgis/>")
    write(tmp_path / "project.qgs.cfg", b"{}")
    write(tmp_path / "data" / "zones.gpkg", b"gpkg")
    state = SyncState("s", "r", str(tmp_path))

    result = compare_now(backend, tmp_path, state)
    sync = sync_now(backend, tmp_path, state, result)

    assert sync.success, (sync.conflicts, sync.errors)
    assert sync.trash is None
    assert ("mkdir", "data") in backend.calls
    assert backend.files["data/zones.gpkg"] == b"gpkg"
    assert (tmp_path / "media" / "logo.png").read_bytes() == b"logo"
    assert sorted(state.entries) == ["data/zones.gpkg", "media/logo.png", "project.qgs", "project.qgs.cfg"]

    # Everything is synchronised, nothing to do
    result = compare_now(backend, tmp_path, state)
    assert set(statuses(result).values()) == {FileStatus.Identical}
    assert result.comparison.to_run() == []


def test_download_keeps_previous_version(tmp_path: Path):
    """Test that a file replaced by a download is kept in the trash."""
    backend = FakeBackend()
    backend.put("a.txt", b"v1")
    state = SyncState("s", "r", str(tmp_path))
    sync_now(backend, tmp_path, state, compare_now(backend, tmp_path, state))

    # Modified on the server
    backend.put("a.txt", b"version 2")
    result = compare_now(backend, tmp_path, state)
    assert statuses(result) == {"a.txt": FileStatus.RemoteModified}
    sync = sync_now(backend, tmp_path, state, result)

    assert sync.success
    assert (tmp_path / "a.txt").read_bytes() == b"version 2"
    assert sync.trash.joinpath("a.txt").read_bytes() == b"v1"
    # The trash is never synchronised
    assert set(statuses(compare_now(backend, tmp_path, state)).values()) == {FileStatus.Identical}


def test_delete_both_sides(tmp_path: Path):
    """Test deletions chosen by the user: the local file goes to the trash, the state forgets them."""
    backend = FakeBackend()
    backend.put("remote.txt", b"r")
    write(tmp_path / "local.txt", b"l")
    state = SyncState("s", "r", str(tmp_path))
    sync_now(backend, tmp_path, state, compare_now(backend, tmp_path, state))

    # Each file deleted on one side
    (tmp_path / "remote.txt").unlink()
    backend.delete("local.txt", None)
    result = compare_now(backend, tmp_path, state)
    assert statuses(result) == {"local.txt": FileStatus.DeletedRemote, "remote.txt": FileStatus.DeletedLocal}
    for diff in result.comparison.diffs:
        diff.choose(SyncAction.DeleteLocal if diff.local else SyncAction.DeleteRemote)

    sync = sync_now(backend, tmp_path, state, result)
    assert sync.success
    assert not (tmp_path / "local.txt").exists()
    assert sync.trash.joinpath("local.txt").read_bytes() == b"l"
    assert backend.files == {}
    assert state.entries == {}


def test_local_change_after_comparison(tmp_path: Path):
    """Test that a local file modified after the comparison is not sent."""
    backend = FakeBackend()
    write(tmp_path / "a.txt", b"first")
    state = SyncState("s", "r", str(tmp_path))
    result = compare_now(backend, tmp_path, state)

    write(tmp_path / "a.txt", b"modified meanwhile")
    sync = sync_now(backend, tmp_path, state, result)

    assert sync.conflicts == {"a.txt": "Modified locally since the comparison"}
    assert backend.files == {}
    assert state.entries == {}


def test_remote_change_after_comparison(tmp_path: Path):
    """Test that a file modified on the server after the comparison is not overwritten."""
    backend = FakeBackend()
    backend.put("a.txt", b"v1")
    state = SyncState("s", "r", str(tmp_path))
    sync_now(backend, tmp_path, state, compare_now(backend, tmp_path, state))

    write(tmp_path / "a.txt", b"local v2")
    result = compare_now(backend, tmp_path, state)
    backend.put("a.txt", b"remote v2")
    sync = sync_now(backend, tmp_path, state, result)

    assert sync.conflicts == {"a.txt": "Modified on the server since the comparison"}
    assert backend.files["a.txt"] == b"remote v2"


def test_corrupted_upload(tmp_path: Path):
    """Test the verification of an upload with the checksums of the manifest."""
    backend = FakeBackend()
    backend.corrupt = b"corrupted"
    write(tmp_path / "a.txt", b"content")
    state = SyncState("s", "r", str(tmp_path))
    sync = sync_now(backend, tmp_path, state, compare_now(backend, tmp_path, state))

    assert sync.errors == {"a.txt": "Different content after the transfer"}
    assert state.entries == {}


def test_canceled(tmp_path: Path):
    """Test a synchronisation canceled before the first operation."""
    backend = FakeBackend()
    write(tmp_path / "a.txt", b"a")
    state = SyncState("s", "r", str(tmp_path))
    result = compare_now(backend, tmp_path, state)

    feedback = QgsFeedback()
    feedback.cancel()
    sync = sync_now(backend, tmp_path, state, result, feedback)

    assert sync.canceled
    assert backend.calls == []


def test_progress(tmp_path: Path):
    """Test the progress of the synchronisation."""
    backend = FakeBackend()
    write(tmp_path / "a.txt", b"a" * 1000)
    write(tmp_path / "b.txt", b"b")
    state = SyncState("s", "r", str(tmp_path))
    result = compare_now(backend, tmp_path, state)

    feedback = QgsFeedback()
    values = []
    feedback.progressChanged.connect(values.append)
    sync_now(backend, tmp_path, state, result, feedback)

    assert values == sorted(values)
    assert values[-1] == 100


def test_purge_trash(tmp_path: Path):
    """Test the removal of old trash directories."""
    old = tmp_path / TRASH_DIRECTORY / "2020-01-01_00-00-00"
    recent = tmp_path / TRASH_DIRECTORY / "2026-11-27_10-00-00"
    write(old / "a.txt", b"a")
    write(recent / "a.txt", b"a")
    os.utime(old, (0, 0))

    purge_trash(tmp_path, keep_days=30, now=time.time())

    assert not old.exists()
    assert recent.exists()


def test_remove_emptied_directories(tmp_path: Path):
    """Test the removal of the directories emptied by the deletions, on both sides."""
    backend = FakeBackend()
    backend.put("a/b/c.txt", b"c")
    backend.put("a/kept.txt", b"k")
    backend.put("x/y/z.txt", b"z")
    backend.dirs.add("empty_before")
    state = SyncState("s", "r", str(tmp_path))
    sync_now(backend, tmp_path, state, compare_now(backend, tmp_path, state))
    (tmp_path / "empty_local_before").mkdir()

    # Deleted locally, the deletion is propagated to the server
    (tmp_path / "a" / "b" / "c.txt").unlink()
    # Deleted on the server, the deletion is propagated locally
    backend.delete("x/y/z.txt", None)
    result = compare_now(backend, tmp_path, state)
    for diff in result.comparison.diffs:
        if diff.status == FileStatus.DeletedLocal:
            diff.choose(SyncAction.DeleteRemote)
        elif diff.status == FileStatus.DeletedRemote:
            diff.choose(SyncAction.DeleteLocal)
    sync = sync_now(backend, tmp_path, state, result)

    assert sync.success, sync.errors
    # "a" still contains a file, empty directories existing before are kept
    assert sync.removed_remote_directories == ["a/b"]
    assert backend.dirs == {"a", "x", "x/y", "empty_before"}
    assert sync.removed_local_directories == ["x/y", "x"]
    assert not (tmp_path / "x").exists()
    assert (tmp_path / "a" / "b").is_dir()
    assert (tmp_path / "empty_local_before").is_dir()


def test_directory_not_empty_anymore(tmp_path: Path):
    """Test a directory not removed because the server refuses, a file has been added meanwhile."""
    backend = FakeBackend()
    backend.put("a/c.txt", b"c")
    state = SyncState("s", "r", str(tmp_path))
    sync_now(backend, tmp_path, state, compare_now(backend, tmp_path, state))

    (tmp_path / "a" / "c.txt").unlink()
    result = compare_now(backend, tmp_path, state)
    result.comparison.diffs[0].choose(SyncAction.DeleteRemote)

    # A file added by someone else, between the final manifest and the removal of the directory
    original = backend.delete_empty_directory

    def add_then_delete(path: str, feedback: QgsFeedback | None = None):
        """Add a file in the directory, then try to delete it.

        :param path: Relative path.
        :param feedback: Not used.
        """
        backend.put("a/new.txt", b"n")
        original(path, feedback)

    backend.delete_empty_directory = add_then_delete
    sync = sync_now(backend, tmp_path, state, result)

    assert sync.success
    assert sync.removed_remote_directories == []
    assert "a/new.txt" in backend.files


def test_silent_failures_detected(tmp_path: Path):
    """Test a server reporting a success for a deletion or a directory not done."""
    backend = FakeBackend()
    backend.put("old.txt", b"o")
    state = SyncState("s", "r", str(tmp_path))
    sync_now(backend, tmp_path, state, compare_now(backend, tmp_path, state))

    (tmp_path / "old.txt").unlink()
    write(tmp_path / "new" / "file.txt", b"n")
    result = compare_now(backend, tmp_path, state)
    next(d for d in result.comparison.diffs if d.path == "old.txt").choose(SyncAction.DeleteRemote)
    backend.silent_failures = True
    sync = sync_now(backend, tmp_path, state, result)

    assert sync.errors == {
        "new": "Directory not created on the server",
        "new/file.txt": "Missing parent",
        "old.txt": "Still on the server after the deletion",
    }
    # The deleted file is still known, the next comparison is right
    assert "old.txt" in state.entries
    assert [op.path for op in sync.done] == []


def test_build_plan_create_root(tmp_path: Path):
    """Test the creation of the root directory, missing on the server, before the first upload."""
    backend = FakeBackend()
    write(tmp_path / "a.txt", b"a")
    write(tmp_path / "d" / "b.txt", b"b")
    state = SyncState("s", "r", str(tmp_path))
    result = compare_now(backend, tmp_path, state)

    plan = build_plan(result.comparison, result.manifest.dirs, create_root=True)
    assert [(op.kind, op.path) for op in plan] == [
        (OperationKind.MakeRemoteDirectory, ""),
        (OperationKind.MakeRemoteDirectory, "d"),
        (OperationKind.Upload, "a.txt"),
        (OperationKind.Upload, "d/b.txt"),
    ]

    # The root directory is verified by the manifest itself
    sync = SyncExecutor(backend, tmp_path, state).run(result.comparison, plan)
    assert sync.success, sync.errors


def test_recompare_direction(tmp_path: Path):
    """Test a new comparison with another direction, without any request."""
    backend = FakeBackend()
    backend.put("remote.txt", b"r")
    write(tmp_path / "local.txt", b"l")
    state = SyncState("s", "r", str(tmp_path))
    result = compare_now(backend, tmp_path, state)
    calls = len(backend.calls)

    pulled = recompare(result, PairSettings(Direction.PullOnly, (), None))

    assert {diff.path: diff.action for diff in pulled.comparison.diffs} == {
        "local.txt": SyncAction.Nothing,
        "remote.txt": SyncAction.Download,
    }
    assert pulled.pair.settings.direction == Direction.PullOnly
    assert len(backend.calls) == calls


def test_missing_local_directory(tmp_path: Path):
    """Test a pair whose local directory doesn't exist yet, such as the shared media."""
    backend = FakeBackend()
    backend.put("upload/photo.jpg", b"jpg")
    root = tmp_path / "media"
    state = SyncState("s", "media", str(root))

    result = compare_now(backend, root, state, PairSettings(Direction.PullOnly, ("upload/**",), None))
    assert statuses(result) == {"upload/photo.jpg": FileStatus.NewRemote}

    sync = sync_now(backend, root, state, result)
    assert sync.success
    assert (root / "upload" / "photo.jpg").read_bytes() == b"jpg"
