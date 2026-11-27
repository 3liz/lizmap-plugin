"""Test the comparison engine of the synchronisation."""

import pytest

from lizmap.sync.diff import (
    DEFAULT_PREFERENCES,
    allowed_actions,
    classify,
    compare,
    resolve_action,
)
from lizmap.sync.filters import ExcludeRules, match_glob
from lizmap.sync.model import (
    BaseEntry,
    Direction,
    FileDiff,
    FileStatus,
    LocalEntry,
    Preference,
    RemoteEntry,
    SyncAction,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64

PATH = "project.qgs"


def local(size: int = 10, mtime_ns: int = 1_000_000_000_000, checksum: str | None = SHA_A) -> LocalEntry:
    """Build a local entry.

    :param size: Size in bytes.
    :param mtime_ns: Modification time in nanoseconds.
    :param checksum: Checksum.
    :return: The local entry.
    """
    return LocalEntry(PATH, size, mtime_ns, checksum)


def remote(
    size: int = 10, mtime: int = 1000, etag: str = '"e1"', checksum: str | None = SHA_A
) -> RemoteEntry:
    """Build a remote entry.

    :param size: Size in bytes.
    :param mtime: Modification time in seconds.
    :param etag: ETag.
    :param checksum: Checksum.
    :return: The remote entry.
    """
    return RemoteEntry(PATH, size, mtime, etag, checksum)


def base(
    local_entry: LocalEntry | None = None,
    remote_entry: RemoteEntry | None = None,
) -> BaseEntry:
    """Build a base entry from a local and a remote entry, as recorded after a synchronisation.

    :param local_entry: Local side, the default local entry if None.
    :param remote_entry: Remote side, the default remote entry if None.
    :return: The base entry.
    """
    local_entry = local_entry or local()
    remote_entry = remote_entry or remote()
    return BaseEntry(
        local_size=local_entry.size,
        local_mtime_ns=local_entry.mtime_ns,
        local_checksum=local_entry.checksum,
        remote_size=remote_entry.size,
        remote_mtime=remote_entry.mtime,
        remote_etag=remote_entry.etag,
        remote_checksum=remote_entry.checksum,
        synced_at=1000,
    )


@pytest.mark.parametrize(
    ("local_entry", "remote_entry", "base_entry", "expected"),
    [
        # Never synchronised
        pytest.param(local(), None, None, FileStatus.NewLocal, id="new-local"),
        pytest.param(None, remote(), None, FileStatus.NewRemote, id="new-remote"),
        pytest.param(local(), remote(), None, FileStatus.Identical, id="identical-checksum"),
        pytest.param(local(), remote(checksum=SHA_B), None, FileStatus.Different, id="different-checksum"),
        pytest.param(local(), remote(size=11), None, FileStatus.Different, id="different-size"),
        pytest.param(
            local(checksum=None),
            remote(checksum=None),
            None,
            FileStatus.Unverified,
            id="unverified-same-size",
        ),
        pytest.param(local(), remote(checksum=None), None, FileStatus.Unverified, id="unverified-big-remote"),
        # Already synchronised, nothing changed, even if the remote ETag changed with the same checksum
        pytest.param(local(), remote(), base(), FileStatus.Identical, id="unchanged"),
        pytest.param(
            local(mtime_ns=5), remote(etag='"e2"'), base(), FileStatus.Identical, id="touched-both-sides"
        ),
        # Already synchronised, one side changed
        pytest.param(
            local(checksum=SHA_B), remote(), base(), FileStatus.LocalModified, id="local-modified-checksum"
        ),
        pytest.param(
            local(size=12, checksum=SHA_B),
            remote(),
            base(),
            FileStatus.LocalModified,
            id="local-modified-size",
        ),
        pytest.param(
            local(),
            remote(etag='"e2"', checksum=SHA_B),
            base(),
            FileStatus.RemoteModified,
            id="remote-modified-checksum",
        ),
        # Both changed differently
        pytest.param(
            local(checksum=SHA_B), remote(checksum=SHA_C), base(), FileStatus.Conflict, id="conflict"
        ),
        # Both changed the same way
        pytest.param(
            local(checksum=SHA_B), remote(checksum=SHA_B), base(), FileStatus.Identical, id="same-change"
        ),
        # Deletions
        pytest.param(local(), None, base(), FileStatus.DeletedRemote, id="deleted-remote"),
        pytest.param(None, remote(), base(), FileStatus.DeletedLocal, id="deleted-local"),
        pytest.param(
            local(checksum=SHA_B), None, base(), FileStatus.Conflict, id="modified-local-deleted-remote"
        ),
        pytest.param(
            None, remote(checksum=SHA_B), base(), FileStatus.Conflict, id="modified-remote-deleted-local"
        ),
    ],
)
def test_classify_with_checksums(local_entry, remote_entry, base_entry, expected):
    """Test the status of a file, with checksums."""
    assert classify(local_entry, remote_entry, base_entry) == expected


@pytest.mark.parametrize(
    ("local_entry", "remote_entry", "expected"),
    [
        pytest.param(local(checksum=None), remote(checksum=None), FileStatus.Identical, id="unchanged"),
        pytest.param(
            local(mtime_ns=5, checksum=None),
            remote(checksum=None),
            FileStatus.LocalModified,
            id="local-mtime",
        ),
        pytest.param(
            local(checksum=None),
            remote(etag='"e2"', checksum=None),
            FileStatus.RemoteModified,
            id="remote-etag",
        ),
        pytest.param(
            local(mtime_ns=5, checksum=None),
            remote(etag='"e2"', checksum=None),
            FileStatus.Conflict,
            id="both",
        ),
    ],
)
def test_classify_without_checksums(local_entry, remote_entry, expected):
    """Test the status of a file, without checksums, using the modification time and the ETag."""
    base_entry = base(local(checksum=None), remote(checksum=None))
    assert classify(local_entry, remote_entry, base_entry) == expected


def test_classify_inconsistent_base():
    """Test a file unchanged on both sides since the last synchronisation, but with different checksums."""
    base_entry = base(local(), remote(checksum=SHA_B))
    assert classify(local(), remote(checksum=SHA_B), base_entry) == FileStatus.Different


def test_classify_missing_both_sides():
    """Test a file which doesn't exist anywhere."""
    with pytest.raises(ValueError):
        classify(None, None, base())


def test_allowed_actions():
    """Test the allowed actions according to the presence of the file."""
    assert allowed_actions(FileStatus.Identical, local(), remote()) == (SyncAction.Nothing,)
    assert allowed_actions(FileStatus.Excluded, local(), None) == (SyncAction.Nothing,)
    assert allowed_actions(FileStatus.Different, local(), remote()) == (
        SyncAction.Nothing,
        SyncAction.Upload,
        SyncAction.Download,
    )
    assert allowed_actions(FileStatus.NewLocal, local(), None) == (
        SyncAction.Nothing,
        SyncAction.Upload,
        SyncAction.DeleteLocal,
    )
    assert allowed_actions(FileStatus.NewRemote, None, remote()) == (
        SyncAction.Nothing,
        SyncAction.Download,
        SyncAction.DeleteRemote,
    )


def diff_for(
    local_entry: LocalEntry | None,
    remote_entry: RemoteEntry | None,
    status: FileStatus = FileStatus.Different,
) -> FileDiff:
    """Build a diff for the tests of the preferences.

    :param local_entry: The local entry.
    :param remote_entry: The remote entry.
    :param status: The status.
    :return: The diff.
    """
    return FileDiff(
        path=PATH,
        status=status,
        local=local_entry,
        remote=remote_entry,
        base=None,
        allowed_actions=allowed_actions(status, local_entry, remote_entry),
    )


@pytest.mark.parametrize(
    ("local_entry", "remote_entry", "preference", "expected"),
    [
        (local(), remote(), Preference.Local, SyncAction.Upload),
        (local(), remote(), Preference.Remote, SyncAction.Download),
        (local(), remote(), Preference.Nothing, SyncAction.Nothing),
        (local(), None, Preference.Local, SyncAction.Upload),
        (local(), None, Preference.Remote, SyncAction.DeleteLocal),
        (None, remote(), Preference.Local, SyncAction.DeleteRemote),
        (None, remote(), Preference.Remote, SyncAction.Download),
        # Newest, the remote file is at 1000 s
        (local(mtime_ns=2_000_000_000_000), remote(), Preference.Newest, SyncAction.Upload),
        (local(mtime_ns=500_000_000_000), remote(), Preference.Newest, SyncAction.Download),
        (local(mtime_ns=1_000_000_000_000), remote(), Preference.Newest, SyncAction.Nothing),
        (local(), None, Preference.Newest, SyncAction.Nothing),
    ],
)
def test_resolve_action(local_entry, remote_entry, preference, expected):
    """Test the translation of a preference into an action."""
    assert resolve_action(diff_for(local_entry, remote_entry), preference) == expected


def test_resolve_action_frozen_status():
    """Test a preference on an identical file."""
    assert (
        resolve_action(diff_for(local(), remote(), FileStatus.Identical), Preference.Local)
        == SyncAction.Nothing
    )


def test_choose_not_allowed():
    """Test choosing an action not allowed for a file."""
    diff = diff_for(local(), None, FileStatus.NewLocal)
    with pytest.raises(ValueError):
        diff.choose(SyncAction.Download)


def entries(*items) -> dict:
    """Index entries by path.

    :param items: Entries.
    :return: The entries by path.
    """
    return {item.path: item for item in items}


def test_compare_default_actions():
    """Test a full comparison with the default preferences."""
    local_files = entries(
        LocalEntry("new_local.gpkg", 100, 1, SHA_A),
        LocalEntry("modified.qgs", 20, 2, SHA_B),
        LocalEntry("same.qgs.cfg", 5, 3, SHA_C),
        LocalEntry("deleted_remote.csv", 7, 4, SHA_A),
    )
    remote_files = entries(
        RemoteEntry("new_remote.png", 50, 10, '"r1"', SHA_A),
        RemoteEntry("modified.qgs", 10, 11, '"r2"', SHA_A),
        RemoteEntry("same.qgs.cfg", 5, 12, '"r3"', SHA_C),
    )
    base_entries = {
        "modified.qgs": BaseEntry(10, 1, SHA_A, 10, 11, '"r2"', SHA_A, 0),
        "deleted_remote.csv": BaseEntry(7, 4, SHA_A, 7, 9, '"r4"', SHA_A, 0),
        "deleted_both.txt": BaseEntry(1, 1, SHA_A, 1, 1, '"r5"', SHA_A, 0),
    }

    comparison = compare(local_files, remote_files, base_entries)

    result = {diff.path: (diff.status, diff.action) for diff in comparison.diffs}
    assert result == {
        "deleted_remote.csv": (FileStatus.DeletedRemote, SyncAction.Nothing),
        "modified.qgs": (FileStatus.LocalModified, SyncAction.Upload),
        "new_local.gpkg": (FileStatus.NewLocal, SyncAction.Upload),
        "new_remote.png": (FileStatus.NewRemote, SyncAction.Download),
        "same.qgs.cfg": (FileStatus.Identical, SyncAction.Nothing),
    }
    # Sorted by path
    assert [diff.path for diff in comparison.diffs] == sorted(result)
    assert comparison.stale_paths == ["deleted_both.txt"]

    # Summary of the transfers
    assert comparison.summary() == {
        SyncAction.Upload: (2, 120),
        SyncAction.Download: (1, 50),
    }

    # Bulk button, then back to the defaults
    comparison.apply_preference(Preference.Local)
    result = {diff.path: diff.action for diff in comparison.diffs}
    assert result["new_remote.png"] == SyncAction.DeleteRemote
    assert result["deleted_remote.csv"] == SyncAction.Upload
    assert result["same.qgs.cfg"] == SyncAction.Nothing

    comparison.reset()
    assert comparison.diffs[0].action == SyncAction.Nothing
    assert len(comparison.to_run()) == 3


def test_compare_custom_preferences():
    """Test overriding a default preference."""
    local_files = entries(LocalEntry("a.qgs", 1, 2_000_000_000_000, SHA_A))
    remote_files = entries(RemoteEntry("a.qgs", 2, 1000, '"r"', SHA_B))

    comparison = compare(local_files, remote_files, {})
    assert comparison.diffs[0].status == FileStatus.Different
    assert comparison.diffs[0].action == SyncAction.Nothing

    comparison = compare(local_files, remote_files, {}, preferences={FileStatus.Different: Preference.Newest})
    assert comparison.diffs[0].action == SyncAction.Upload
    assert comparison.diffs[0].default_action == SyncAction.Upload


def test_compare_excluded_and_case_conflict():
    """Test the filters and the paths differing only by the case."""
    local_files = entries(
        LocalEntry("project.qgs~", 1, 1, None),
        LocalEntry("big.tif", 1000, 1, None),
        LocalEntry("Data.csv", 1, 1, SHA_A),
    )
    remote_files = entries(RemoteEntry("data.csv", 1, 1, '"r"', SHA_B))
    rules = ExcludeRules(max_size=500)

    comparison = compare(local_files, remote_files, {}, rules=rules)

    result = {diff.path: (diff.status, diff.action, diff.exclusion) for diff in comparison.diffs}
    assert result == {
        "Data.csv": (FileStatus.CaseConflict, SyncAction.Nothing, None),
        "big.tif": (FileStatus.Excluded, SyncAction.Nothing, "size > 500"),
        "data.csv": (FileStatus.CaseConflict, SyncAction.Nothing, None),
        "project.qgs~": (FileStatus.Excluded, SyncAction.Nothing, "pattern : *.qgs~"),
    }


def test_default_preferences_never_delete():
    """Test that no default preference can delete a file."""
    for status, preference in DEFAULT_PREFERENCES.items():
        if status in (FileStatus.DeletedLocal, FileStatus.DeletedRemote, FileStatus.Conflict):
            assert preference == Preference.Nothing


@pytest.mark.parametrize(
    ("direction", "local_entry", "remote_entry", "expected"),
    [
        (Direction.PullOnly, local(), remote(), (SyncAction.Nothing, SyncAction.Download)),
        (Direction.PullOnly, local(), None, (SyncAction.Nothing, SyncAction.DeleteLocal)),
        (Direction.PullOnly, None, remote(), (SyncAction.Nothing, SyncAction.Download)),
        (Direction.PushOnly, local(), remote(), (SyncAction.Nothing, SyncAction.Upload)),
        (Direction.PushOnly, local(), None, (SyncAction.Nothing, SyncAction.Upload)),
        (Direction.PushOnly, None, remote(), (SyncAction.Nothing, SyncAction.DeleteRemote)),
    ],
)
def test_allowed_actions_direction(direction, local_entry, remote_entry, expected):
    """Test the actions allowed by a direction."""
    assert allowed_actions(FileStatus.Different, local_entry, remote_entry, direction) == expected


def test_compare_direction():
    """Test the default actions with a direction: a new local file is not sent in pull only mode."""
    local_files = entries(LocalEntry("a.png", 1, 1, SHA_A))
    remote_files = entries(RemoteEntry("b.png", 1, 1, '"r"', SHA_B))

    comparison = compare(local_files, remote_files, {}, direction=Direction.PullOnly)

    result = {diff.path: (diff.action, diff.allowed_actions) for diff in comparison.diffs}
    assert result == {
        "a.png": (SyncAction.Nothing, (SyncAction.Nothing, SyncAction.DeleteLocal)),
        "b.png": (SyncAction.Download, (SyncAction.Nothing, SyncAction.Download)),
    }


def test_compare_protected():
    """Test the files produced by the server, never deleted nor overwritten on the server by default."""
    local_files = entries(
        LocalEntry("media/upload/a.jpg", 1, 1, SHA_A),
        LocalEntry("media/upload/sub/new.jpg", 1, 1, SHA_A),
    )
    remote_files = entries(
        RemoteEntry("media/upload/a.jpg", 2, 1, '"r"', SHA_B),
        RemoteEntry("media/upload/b.jpg", 2, 1, '"r"', SHA_B),
    )
    base_entries = {
        "media/upload/a.jpg": BaseEntry(2, 1, SHA_B, 2, 1, '"r"', SHA_B, 0),
        "media/upload/b.jpg": BaseEntry(2, 1, SHA_B, 2, 1, '"r"', SHA_B, 0),
    }
    comparison = compare(local_files, remote_files, base_entries, protected_patterns=("media/upload/**",))
    result = {diff.path: (diff.status, diff.protected, diff.action) for diff in comparison.diffs}
    assert result == {
        # Modified locally: the upload would overwrite the file of the server
        "media/upload/a.jpg": (FileStatus.LocalModified, True, SyncAction.Nothing),
        # Deleted locally: never deleted on the server by the bulk choices
        "media/upload/b.jpg": (FileStatus.DeletedLocal, True, SyncAction.Nothing),
        # A new file is sent, nothing is overwritten
        "media/upload/sub/new.jpg": (FileStatus.NewLocal, True, SyncAction.Upload),
    }

    comparison.apply_preference(Preference.Local)
    assert [diff.action for diff in comparison.diffs] == [
        SyncAction.Nothing,
        SyncAction.Nothing,
        SyncAction.Upload,
    ]

    # An explicit choice, file by file, is still possible
    comparison.diffs[1].choose(SyncAction.DeleteRemote)
    assert comparison.diffs[1].action == SyncAction.DeleteRemote


def test_compare_download_threshold():
    """Test that big files missing locally are not downloaded by default."""
    remote_files = entries(
        RemoteEntry("small.jpg", 10, 1, '"r"', SHA_A),
        RemoteEntry("big.tif", 1000, 1, '"r"', None),
    )
    comparison = compare({}, remote_files, {}, download_threshold=100)
    assert {diff.path: diff.action for diff in comparison.diffs} == {
        "big.tif": SyncAction.Nothing,
        "small.jpg": SyncAction.Download,
    }

    # Still possible with the bulk choices
    comparison.apply_preference(Preference.Remote)
    assert comparison.diffs[0].action == SyncAction.Download


@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        ("media/upload/a.jpg", "media/upload/**", True),
        ("media/upload/x/y/a.jpg", "media/upload/**", True),
        ("MEDIA/Upload/a.jpg", "media/upload/**", True),
        ("other/media/upload/a.jpg", "media/upload/**", False),
        ("media/uploads/a.jpg", "media/upload/**", False),
        ("a/b/c.jpg", "**/*.jpg", True),
        ("c.jpg", "**/*.jpg", True),
        ("a/c.jpg", "*.jpg", False),
        ("media/js/a.js", "media/*/a.js", True),
    ],
)
def test_match_glob(path, pattern, expected):
    """Test the glob patterns with "**"."""
    assert match_glob(path, pattern) == expected
