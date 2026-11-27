"""Test the exclusion rules, the local scan and the synchronisation state."""

import hashlib
import json
import os

from pathlib import Path

import pytest

from lizmap.sync.filters import ExcludeRules, ExclusionReason
from lizmap.sync.model import BaseEntry, LocalEntry, RemoteEntry
from lizmap.sync.scanner import ScanCanceled, scan_local
from lizmap.sync.state import StateError, SyncState, state_file_name


@pytest.mark.parametrize(
    ("path", "size", "reason"),
    [
        ("project.qgs", 10, None),
        ("project.qgs.cfg", 10, None),
        ("project.qgd", 10, None),
        ("media/js/project/script.js", 10, None),
        ("project.qgs~", 10, ExclusionReason.Pattern),
        ("PROJECT.BAK", 10, ExclusionReason.Pattern),
        ("data/zones.gpkg-wal", 10, ExclusionReason.Pattern),
        ("data/__pycache__/a.pyc", 10, ExclusionReason.Pattern),
        (".git/config", 10, ExclusionReason.Hidden),
        ("data/.hidden.csv", 10, ExclusionReason.Hidden),
        ("data/~$report.xlsx", 10, ExclusionReason.Pattern),
        ("big.tif", 2000, ExclusionReason.Size),
    ],
)
def test_file_exclusion(path, size, reason):
    """Test the default exclusion rules."""
    exclusion = ExcludeRules(max_size=1000).file_exclusion(path, size)
    assert (exclusion.reason if exclusion else None) == reason


def test_custom_patterns():
    """Test anchored patterns, directory patterns and hidden files allowed."""
    rules = ExcludeRules(patterns=("data/raw/*.csv", "tmp/", "cache/tiles/"), exclude_hidden=False)
    assert rules.file_exclusion("data/raw/a.csv")
    assert rules.file_exclusion("other/data/raw/a.csv") is None
    assert rules.file_exclusion("a/tmp/b.txt")
    assert rules.file_exclusion("cache/tiles/1/2.png")
    assert rules.file_exclusion("other/cache/tiles/1.png") is None
    assert rules.file_exclusion(".lizmapignore") is None
    assert rules.directory_exclusion("a/tmp")
    assert rules.directory_exclusion("a/data") is None


def write(path: Path, content: bytes):
    """Write a file and its parents.

    :param path: The file.
    :param content: The content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_scan_local(tmp_path):
    """Test the scan of a local directory."""
    write(tmp_path / "project.qgs", b"<qgis/>")
    write(tmp_path / "media" / "js" / "project" / "a.js", b"// js")
    write(tmp_path / "data" / "big.tif", b"x" * 100)
    write(tmp_path / "project.qgs~", b"backup")
    write(tmp_path / ".git" / "config", b"[core]")
    (tmp_path / "empty").mkdir()

    scan = scan_local(tmp_path, ExcludeRules(), checksum_max_size=50)

    assert sorted(scan.files) == ["data/big.tif", "media/js/project/a.js", "project.qgs", "project.qgs~"]
    # Excluded directories are not visited, empty directories are listed
    assert scan.dirs == {"data", "empty", "media", "media/js", "media/js/project"}
    assert scan.errors == {}

    assert scan.files["project.qgs"].checksum == hashlib.sha256(b"<qgis/>").hexdigest()
    assert scan.files["project.qgs"].size == 7
    # Too big or excluded files don't have any checksum
    assert scan.files["data/big.tif"].checksum is None
    assert scan.files["project.qgs~"].checksum is None


def test_scan_reuse_checksum(tmp_path):
    """Test that the checksum of an unchanged file is taken from the last synchronisation."""
    write(tmp_path / "a.csv", b"1;2")
    stat = (tmp_path / "a.csv").stat()
    fake = "f" * 64
    base = {"a.csv": BaseEntry(stat.st_size, stat.st_mtime_ns, fake, 3, 1, '"e"', fake, 1)}

    assert scan_local(tmp_path, ExcludeRules(), base).files["a.csv"].checksum == fake

    # Once modified, the checksum is computed again
    os.utime(tmp_path / "a.csv", ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
    assert (
        scan_local(tmp_path, ExcludeRules(), base).files["a.csv"].checksum
        == hashlib.sha256(b"1;2").hexdigest()
    )


def test_scan_canceled(tmp_path):
    """Test the cancellation of the scan."""

    class Feedback:
        """Feedback always canceled."""

        def isCanceled(self) -> bool:
            """Canceled.

            :return: Always True.
            """
            return True

    write(tmp_path / "a.csv", b"1")
    with pytest.raises(ScanCanceled):
        scan_local(tmp_path, ExcludeRules(), feedback=Feedback())


def test_state_record_save_load(tmp_path):
    """Test recording, saving and loading the state."""
    state = SyncState("https://demo.lizmap.com/", "urbanism", "/home/user/urbanism")
    state.record(LocalEntry("a.qgs", 3, 5, "a" * 64), RemoteEntry("a.qgs", 3, 6, '"e"', "a" * 64), now=42)
    state.record(LocalEntry("b.csv", 1, 1), RemoteEntry("b.csv", 1, 1, '"f"'), now=43)
    state.prune(["b.csv", "unknown"])

    file_path = tmp_path / "sync" / state_file_name(state.server, state.repository, state.local_dir)
    state.save(file_path)
    # No temporary file left
    assert [p.name for p in file_path.parent.iterdir()] == [file_path.name]

    loaded = SyncState.load(file_path, state.server, state.repository, state.local_dir)
    assert loaded == state
    assert loaded.entries["a.qgs"] == BaseEntry(3, 5, "a" * 64, 3, 6, '"e"', "a" * 64, 42)
    assert loaded.updated_at == 43


def test_state_load_errors(tmp_path):
    """Test loading a missing, corrupted or foreign state."""
    file_path = tmp_path / "state.json"
    empty = SyncState.load(file_path, "s", "r", "/d")
    assert empty.entries == {}

    SyncState("s", "r", "/d").save(file_path)
    with pytest.raises(StateError):
        SyncState.load(file_path, "s", "other", "/d")

    file_path.write_text("{not json", encoding="utf8")
    with pytest.raises(StateError):
        SyncState.load(file_path, "s", "r", "/d")

    file_path.write_text(json.dumps({"version": 1, "entries": {"a": {"foo": 1}}}), encoding="utf8")
    with pytest.raises(StateError):
        SyncState.load(file_path, "s", "r", "/d")


def test_state_record_different_paths():
    """Test recording two entries with different paths."""
    with pytest.raises(ValueError):
        SyncState("s", "r", "/d").record(LocalEntry("a", 1, 1), RemoteEntry("b", 1, 1, '"e"'))
