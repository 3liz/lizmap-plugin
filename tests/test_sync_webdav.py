"""Test the WebDAV transport of the synchronisation.

Tests using a server are skipped unless these environment variables are set, for instance with
the test stack of the Lizmap WebDAV module (``make run`` in its ``tests`` directory):

* ``LIZMAP_SYNC_DAV_URL``: URL of a writable directory, ``http://127.0.0.1:9023/dav.php/tests/``,
* ``LIZMAP_SYNC_USER`` and ``LIZMAP_SYNC_PASSWORD``: a user with the WebDAV access.
"""

import hashlib
import os
import time

from pathlib import Path

import pytest

from qgis.core import QgsApplication, QgsTask
from qgis.PyQt.QtCore import QCoreApplication

from lizmap.sync.backends.base import BackendError
from lizmap.sync.backends.webdav import (
    DOWNLOAD_PREFIX,
    WebDavBackend,
    WebDavServer,
    _error_message,
    encode_path,
)
from lizmap.sync.filters import ExcludeRules
from lizmap.sync.model import FileStatus
from lizmap.sync.state import SyncState
from lizmap.sync.tasks import CompareTask, SyncTask
from lizmap.toolbelt.strings import random_string

DAV_URL = os.getenv("LIZMAP_SYNC_DAV_URL", "")
USER = os.getenv("LIZMAP_SYNC_USER", "")
PASSWORD = os.getenv("LIZMAP_SYNC_PASSWORD", "")

METADATA = {
    "webdav": {
        "version": "1.3.0",
        "url": "https://demo.lizmap.com/dav.php",
        "cog_path": "",
        "projects_path": "qgis-projects/",
        "features": ["manifest", "sha256", "atomic-put", "fs-errors", "delete-empty-only"],
        "manifest_version": "1.0",
        "checksum_max_size": 1000,
    }
}


def test_server_from_metadata():
    """Test the WebDAV capabilities read from the metadata."""
    server = WebDavServer.from_metadata(METADATA)
    assert server.url == "https://demo.lizmap.com/dav.php/"
    assert server.supports_sync
    assert server.checksum_max_size == 1000
    assert (
        server.repository_url("urba nisme/") == "https://demo.lizmap.com/dav.php/qgis-projects/urba%20nisme/"
    )

    # Without projects path
    server = WebDavServer.from_metadata(
        {"webdav": {"url": "https://demo.lizmap.com/dav.php/", "projects_path": ""}}
    )
    assert server.repository_url("tests/") == "https://demo.lizmap.com/dav.php/tests/"

    # An old module without the manifest
    assert not server.supports_sync

    # Repository outside of the root directory of the repositories
    for path in ("/srv/other/", "../other/", ""):
        with pytest.raises(ValueError):
            server.repository_url(path)

    # No WebDAV for this user
    assert WebDavServer.from_metadata({"info": {}}) is None
    assert WebDavServer.from_metadata(None) is None


def test_encode_path():
    """Test the encoding of paths in URLs."""
    assert encode_path("données/été test#1.gpkg") == "donn%C3%A9es/%C3%A9t%C3%A9%20test%231.gpkg"


def test_error_message():
    """Test the message extracted from a Sabre error."""
    body = (
        b'<?xml version="1.0" encoding="utf-8"?>\n<d:error xmlns:d="DAV:" xmlns:s="http://sabredav.org/ns">'
        b"<s:exception>Sabre\\DAV\\Exception\\Forbidden</s:exception>"
        b"<s:message>This file name is reserved.</s:message></d:error>"
    )
    assert _error_message(body, "default") == "This file name is reserved."
    assert _error_message(b"<html>502</html>", "default") == "default"


def test_temporary_download_excluded():
    """Test that the temporary files of a download are never synchronised."""
    rules = ExcludeRules(exclude_hidden=False)
    assert rules.file_exclusion(f"data/{DOWNLOAD_PREFIX}zones.gpkg") is not None


@pytest.fixture
def backend() -> WebDavBackend:
    """A backend on a new directory on the test server, removed at the end.

    :return: The backend.
    """
    if not DAV_URL:
        pytest.skip("LIZMAP_SYNC_DAV_URL is not set")

    parent = WebDavBackend(DAV_URL, credentials=(USER, PASSWORD))
    name = f"sync-{random_string(8)}"
    parent.make_directory(name)
    yield WebDavBackend(parent.root_url + name, credentials=(USER, PASSWORD))
    parent._send("DELETE", parent.url(name, directory=True))


def test_backend_scenario(backend: WebDavBackend, tmp_path: Path):
    """Test a full scenario on a server: directories, uploads with preconditions, manifest, download, delete."""
    local = tmp_path / "été.txt"
    local.write_bytes(b"first version")

    # Directories, an existing one is not an error
    backend.make_directory("données")
    backend.make_directory("données")

    # New file
    etag = backend.upload(local, "données/été.txt", None)
    assert etag

    # A new file can't overwrite an existing one
    with pytest.raises(BackendError) as error:
        backend.upload(local, "données/été.txt", None)
    assert error.value.is_conflict

    # Manifest
    manifest = backend.fetch_manifest()
    entry = manifest.files["données/été.txt"]
    assert entry.etag == etag
    assert entry.checksum == hashlib.sha256(b"first version").hexdigest()
    assert manifest.dirs == frozenset({"données"})

    # Replace with the right ETag, then with an outdated one
    local.write_bytes(b"second version")
    new_etag = backend.upload(local, "données/été.txt", etag)
    assert new_etag and new_etag != etag
    with pytest.raises(BackendError) as error:
        backend.upload(local, "données/été.txt", etag)
    assert error.value.is_conflict

    # Download, the temporary file is removed
    target = tmp_path / "download" / "été.txt"
    assert backend.download("données/été.txt", target) == new_etag
    assert target.read_bytes() == b"second version"
    assert sorted(p.name for p in target.parent.iterdir()) == ["été.txt"]

    # Download of a missing file, the local file is kept
    with pytest.raises(BackendError) as error:
        backend.download("données/missing.txt", target)
    assert error.value.http_status == 404
    assert target.read_bytes() == b"second version"

    # Delete with an outdated ETag, then with the right one, then again
    with pytest.raises(BackendError) as error:
        backend.delete("données/été.txt", etag)
    assert error.value.is_conflict
    backend.delete("données/été.txt", new_etag)
    backend.delete("données/été.txt", None)
    assert backend.fetch_manifest().files == {}

    # Directory removed only if empty
    backend.make_directory("données/sub")
    with pytest.raises(BackendError) as error:
        backend.delete_empty_directory("données")
    assert error.value.http_status == 409
    backend.delete_empty_directory("données/sub")
    backend.delete_empty_directory("données")
    backend.delete_empty_directory("données")
    assert backend.fetch_manifest().dirs == frozenset()


def test_backend_errors(backend: WebDavBackend, tmp_path: Path):
    """Test errors from the server."""
    local = tmp_path / "a.txt"
    local.write_bytes(b"a")

    # Reserved name, with the message from the server
    with pytest.raises(BackendError) as error:
        backend.upload(local, ".~lizmap-upload-test", None)
    assert error.value.http_status == 403
    assert "reserved" in str(error.value)

    # Parent directory missing
    with pytest.raises(BackendError) as error:
        backend.upload(local, "missing/a.txt", None)
    assert error.value.http_status == 409

    # Wrong password
    other = WebDavBackend(backend.root_url, credentials=(USER, "wrong"))
    with pytest.raises(BackendError) as error:
        other.fetch_manifest()
    assert error.value.http_status == 401


def run_task(task: QgsTask, timeout: float = 30) -> bool:
    """Run a task with the task manager, in a worker thread, and wait for its end.

    :param task: The task.
    :param timeout: Maximum duration in seconds.
    :return: True if the task completed successfully.
    """
    QgsApplication.taskManager().addTask(task)
    end = time.time() + timeout
    finished = (QgsTask.TaskStatus.Complete, QgsTask.TaskStatus.Terminated)
    while task.status() not in finished and time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    return task.status() == QgsTask.TaskStatus.Complete


def test_tasks_in_worker_thread(backend: WebDavBackend, tmp_path: Path):
    """Test the comparison and the synchronisation tasks with the server, in worker threads."""
    root = tmp_path / "project"
    root.joinpath("data").mkdir(parents=True)
    root.joinpath("project.qgs").write_bytes(b"<qgis/>")
    root.joinpath("data", "zones.gpkg").write_bytes(b"x" * 100_000)
    state = SyncState(backend.root_url, "tests", str(root))
    state_file = tmp_path / "state.json"

    # First comparison, everything is missing on the server
    compare_task = CompareTask(backend, root, ExcludeRules(), state)
    assert run_task(compare_task), compare_task.error
    statuses = {diff.path: diff.status for diff in compare_task.result.comparison.diffs}
    assert statuses == {"data/zones.gpkg": FileStatus.NewLocal, "project.qgs": FileStatus.NewLocal}

    # Synchronisation, the state is saved
    sync_task = SyncTask(backend, root, compare_task.result, state, state_file)
    assert run_task(sync_task), (sync_task.error, sync_task.result)
    assert sync_task.result.success
    assert state_file.exists()
    assert sorted(state.entries) == ["data/zones.gpkg", "project.qgs"]

    # Second comparison, with the saved state: everything is synchronised
    state = SyncState.load(state_file, backend.root_url, "tests", str(root))
    compare_task = CompareTask(backend, root, ExcludeRules(), state)
    assert run_task(compare_task), compare_task.error
    assert {diff.status for diff in compare_task.result.comparison.diffs} == {FileStatus.Identical}
