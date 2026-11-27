"""Test the interface of the synchronisation, with a backend in memory."""

import shutil
import sqlite3
import time

from collections.abc import Callable
from pathlib import Path

import pytest

from qgis.core import QgsFeature, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QAbstractItemModel, QCoreApplication, QModelIndex, Qt
from qgis.PyQt.QtTest import QAbstractItemModelTester
from qgis.PyQt.QtWidgets import QComboBox, QStyleOptionViewItem, QWidget

from lizmap.sync.backends.base import BackendError
from lizmap.sync.filters import ExcludeRules
from lizmap.sync.gui.action_delegate import ActionDelegate
from lizmap.sync.gui.filter_proxy import FilterMode, SyncFilterProxy
from lizmap.sync.gui.project_checks import checkpoint_sqlite, layers_with_pending_edits, project_files
from lizmap.sync.gui.sync_panel import SyncContext, SyncPanel, SyncUnavailable
from lizmap.sync.gui.tree_model import DIFF_ROLE, Column, SyncTreeModel
from lizmap.sync.model import FileStatus, Preference, SyncAction
from lizmap.sync.state import SyncState

from .test_sync_executor import FakeBackend, compare_now, write


def wait_for(condition: Callable[[], bool], timeout: float = 20):
    """Process the events until a condition is true.

    :param condition: The condition.
    :param timeout: Maximum duration in seconds.
    """
    end = time.time() + timeout
    while not condition() and time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert condition(), "Timeout"


Sample = tuple[FakeBackend, Path, SyncState]


@pytest.fixture
def sample(tmp_path: Path) -> Sample:
    """A local directory and a server with some differences.

    :return: The backend, the local directory and an empty state.
    """
    backend = FakeBackend()
    backend.put("media/logo.png", b"logo")
    backend.put("project.qgs.cfg", b"{}")
    write(tmp_path / "project.qgs", b"<qgis/>")
    write(tmp_path / "project.qgs.cfg", b"{}")
    write(tmp_path / "data" / "zones.gpkg", b"gpkg")
    write(tmp_path / "project.qgs~", b"backup")
    return backend, tmp_path, SyncState("s", "r", str(tmp_path))


def model_rows(model: QAbstractItemModel, parent: QModelIndex = QModelIndex(), depth: int = 0) -> list[str]:
    """List the names of the rows of a model, indented by depth.

    :param model: The model or the proxy.
    :param parent: The parent index.
    :param depth: The depth of the parent.
    :return: The names.
    """
    rows = []
    for row in range(model.rowCount(parent)):
        index = model.index(row, 0, parent)
        rows.append("  " * depth + index.data())
        rows.extend(model_rows(model, index, depth + 1))
    return rows


def test_tree_model(sample: Sample):
    """Test the structure, the data and the edition of the tree model."""
    backend, root, state = sample
    model = SyncTreeModel()
    QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Fatal, model)
    model.set_comparison(compare_now(backend, root, state).comparison)

    # Directories first
    assert model_rows(model) == [
        "data",
        "  zones.gpkg",
        "media",
        "  logo.png",
        "project.qgs",
        "project.qgs.cfg",
        "project.qgs~",
    ]

    data = model.index(0, 0)
    zones = model.index(0, 0, data)
    assert model.index(0, Column.Status, data).data() == "Missing on the server"
    assert model.index(0, Column.Action, data).data(Qt.ItemDataRole.EditRole) == SyncAction.Upload
    assert model.index(0, Column.Status).data() == "1 action(s)"
    assert zones.data(DIFF_ROLE).path == "data/zones.gpkg"
    assert model.index(0, Column.Remote, data).data() == "-"

    # Only files with several possible actions are editable
    excluded = model.index(4, Column.Action)
    assert excluded.data(DIFF_ROLE).status == FileStatus.Excluded
    assert not (model.flags(excluded) & Qt.ItemFlag.ItemIsEditable)
    action = model.index(0, Column.Action, data)
    assert model.flags(action) & Qt.ItemFlag.ItemIsEditable

    # Edition of an action, the summary of the directory changes
    assert model.setData(action, SyncAction.Nothing)
    assert model.index(0, Column.Status).data() == ""
    assert not model.setData(action, SyncAction.Download)

    # Bulk changes on a directory, then on all files
    model.apply_preference(Preference.Remote, data)
    assert action.data(Qt.ItemDataRole.EditRole) == SyncAction.DeleteLocal
    model.reset_actions()
    assert action.data(Qt.ItemDataRole.EditRole) == SyncAction.Upload

    model.set_comparison(None)
    assert model.rowCount() == 0


def test_filter_proxy(sample: Sample):
    """Test the filter modes and the search."""
    backend, root, state = sample
    model = SyncTreeModel()
    model.set_comparison(compare_now(backend, root, state).comparison)
    proxy = SyncFilterProxy()
    proxy.setSourceModel(model)
    QAbstractItemModelTester(proxy, QAbstractItemModelTester.FailureReportingMode.Fatal, proxy)

    # Identical and excluded files are hidden by default
    assert model_rows(proxy) == ["data", "  zones.gpkg", "media", "  logo.png", "project.qgs"]

    proxy.set_mode(FilterMode.All)
    assert len(model_rows(proxy)) == 7

    proxy.set_text("LOGO")
    assert model_rows(proxy) == ["media", "  logo.png"]

    proxy.set_text("")
    proxy.set_mode(FilterMode.Problems)
    assert model_rows(proxy) == []

    # A file without action disappears from the files to synchronise
    proxy.set_mode(FilterMode.Actions)
    assert len(model_rows(proxy)) == 5
    model.setData(model.index(0, Column.Action, model.index(0, 0)), SyncAction.Nothing)
    assert model_rows(proxy) == ["media", "  logo.png", "project.qgs"]


def test_action_delegate(sample: Sample):
    """Test the combobox editing the action of a file."""
    backend, root, state = sample
    model = SyncTreeModel()
    model.set_comparison(compare_now(backend, root, state).comparison)
    index = model.index(0, Column.Action, model.index(1, 0))
    delegate = ActionDelegate()
    parent = QWidget()

    editor = delegate.createEditor(parent, QStyleOptionViewItem(), index)
    assert [editor.itemText(i) for i in range(editor.count())] == [
        "No action",
        "Download",
        "Delete on the server",
    ]
    delegate.setEditorData(editor, index)
    assert editor.currentText() == "Download"

    editor.setCurrentIndex(2)
    delegate.setModelData(editor, model, index)
    assert index.data(Qt.ItemDataRole.EditRole) == SyncAction.DeleteRemote

    # No editor for a directory
    assert delegate.createEditor(parent, QStyleOptionViewItem(), model.index(1, Column.Action)) is None


def panel_for(backend: FakeBackend, root: Path, state: SyncState, tmp_path: Path, **kwargs) -> SyncPanel:
    """Build a panel with a context in memory, accepting all questions.

    :param backend: The backend.
    :param root: The local directory.
    :param state: The state.
    :param tmp_path: Temporary directory of the test, the state file is written next to it,
        outside the synchronised directory.
    :param kwargs: Extra parameters of the context.
    :return: The panel.
    """
    state_file = tmp_path.parent / f"{tmp_path.name}-state.json"

    def provider() -> SyncContext:
        """Context of the tests.

        :return: The context.
        """
        return SyncContext(
            backend=backend,
            root=root,
            state=state,
            state_file=state_file,
            rules=ExcludeRules(),
            remote_label="memory",
            **kwargs,
        )

    panel = SyncPanel(None, provider)
    panel.questions = []
    panel.confirm = lambda title, text: panel.questions.append(text) or True
    return panel


def test_panel_compare_and_synchronise(sample: Sample, tmp_path: Path):
    """Test a comparison, then a synchronisation, then the automatic comparison after it."""
    backend, root, state = sample
    panel = panel_for(backend, root, state, tmp_path, project_path="project.qgs")
    assert not panel.sync_button.isEnabled()

    panel.compare()
    wait_for(lambda: not panel.busy)
    assert panel.sync_button.isEnabled()
    assert "Upload : 2" in panel.summary.text()
    assert "Download : 1" in panel.summary.text()

    synchronised = []
    panel.synchronised.connect(synchronised.append)
    panel.synchronise()
    assert panel.busy
    # The synchronisation, then the new comparison
    wait_for(lambda: synchronised and not panel.busy)

    assert synchronised == [False]
    assert "Synchronisation done." in panel.message.text()
    assert backend.files["data/zones.gpkg"] == b"gpkg"
    assert (root / "media" / "logo.png").read_bytes() == b"logo"
    assert (tmp_path.parent / f"{tmp_path.name}-state.json").exists()
    assert panel.summary.text() == "Nothing to synchronise."
    assert not panel.sync_button.isEnabled()


def test_panel_protected_files(sample: Sample, tmp_path: Path):
    """Test the warning about files of the open project replaced by the synchronisation."""
    backend, root, state = sample
    backend.put("project.qgs", b"<qgis version='server'/>")
    panel = panel_for(backend, root, state, tmp_path, project_path="project.qgs")
    panel.compare()
    wait_for(lambda: not panel.busy)

    panel.model.apply_preference(Preference.Remote)
    synchronised = []
    panel.synchronised.connect(synchronised.append)
    panel.synchronise()
    wait_for(lambda: synchronised and not panel.busy)

    assert "used by the open project" in panel.questions[0]
    assert "will be deleted" in panel.questions[0]
    assert synchronised == [True]
    assert "reload it" in panel.message.text()


def test_panel_unavailable(tmp_path: Path):
    """Test a context provider refusing the synchronisation."""

    def provider() -> SyncContext:
        """Refuse.

        :raises SyncUnavailable: Always.
        """
        raise SyncUnavailable("Save the project first.")

    panel = SyncPanel(None, provider)
    panel.compare()
    assert not panel.busy
    assert "Save the project first." in panel.message.text()


def test_panel_missing_directory(sample: Sample, tmp_path: Path):
    """Test the creation of the directory on the server when it doesn't exist yet."""
    _backend, root, state = sample

    class MissingDirectory(FakeBackend):
        """A server without the directory of the repository."""

        exists = False

        def fetch_manifest(self, feedback=None):
            """Fail until the directory is created.

            :param feedback: Not used.
            :return: The manifest.
            """
            if not self.exists:
                raise BackendError("Not found", 404)
            return super().fetch_manifest(feedback)

        def make_directory(self, path, feedback=None):
            """Create the directory of the repository.

            :param path: Relative path, empty for the directory itself.
            :param feedback: Not used.
            """
            if path == "":
                self.exists = True
            super().make_directory(path, feedback)

    panel = panel_for(MissingDirectory(), root, state, tmp_path)
    panel.compare()
    wait_for(lambda: panel.model.comparison is not None)
    assert "doesn't exist yet" in panel.questions[0]


def test_panel_repository_mirror():
    """Test the combobox of the repositories mirrored from the dialog."""
    source = QComboBox()
    source.addItems(["one", "two"])
    panel = SyncPanel(None, lambda: None, source)

    source.setCurrentIndex(1)
    assert panel.repository.currentText() == "two"
    panel.repository.setCurrentIndex(0)
    assert source.currentText() == "one"


def test_project_checks(tmp_path: Path):
    """Test the files used by the project, pending edits and the GeoPackage checkpoint."""
    data = Path(__file__).parent / "data"
    shutil.copy(data / "points_lines.gpkg", tmp_path / "points_lines.gpkg")
    project = QgsProject()
    layer = QgsVectorLayer(f"{tmp_path / 'points_lines.gpkg'}|layername=points", "points", "ogr")
    assert layer.isValid()
    memory = QgsVectorLayer("Point?crs=epsg:4326", "memory", "memory")
    project.addMapLayers([layer, memory])

    assert "points_lines.gpkg" in project_files(project, tmp_path)
    assert project_files(project, tmp_path / "other") == {}

    assert layers_with_pending_edits(project) == []
    memory.startEditing()
    memory.addFeature(QgsFeature(memory.fields()))
    assert layers_with_pending_edits(project) == ["memory"]
    memory.rollBack()


def test_checkpoint_sqlite(tmp_path: Path):
    """Test the checkpoint of a SQLite file in WAL mode, with a connection still open."""
    database = tmp_path / "data.sqlite"
    connection = sqlite3.connect(str(database))
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE t (v TEXT)")
    connection.execute("INSERT INTO t VALUES ('in the wal')")
    connection.commit()
    wal = Path(f"{database}-wal")
    assert wal.stat().st_size > 0

    assert checkpoint_sqlite([database, tmp_path / "other.csv"]) == {}
    assert wal.stat().st_size == 0
    connection.close()
