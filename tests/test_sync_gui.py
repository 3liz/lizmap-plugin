"""Test the interface of the synchronisation, with a backend in memory."""

import shutil
import sqlite3
import time

from collections.abc import Callable
from pathlib import Path

import pytest

from qgis.core import QgsFeature, QgsFeedback, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QAbstractItemModel, QCoreApplication, QModelIndex, Qt
from qgis.PyQt.QtTest import QAbstractItemModelTester
from qgis.PyQt.QtWidgets import QComboBox, QStyleOptionViewItem, QWidget

from lizmap.sync.backends.base import BackendError
from lizmap.sync.diff import Comparison
from lizmap.sync.filters import DEFAULT_EXCLUDE_PATTERNS, parse_rules
from lizmap.sync.gui.action_delegate import ActionDelegate
from lizmap.sync.gui.filter_proxy import FilterMode, SyncFilterProxy
from lizmap.sync.gui.options_dialog import (
    MEGABYTE,
    SyncOptionsDialog,
    default_rules_text,
    load_options,
    save_options,
)
from lizmap.sync.gui.project_checks import checkpoint_sqlite, layers_with_pending_edits, project_files
from lizmap.sync.gui.sync_panel import SyncContext, SyncPanel, SyncUnavailable
from lizmap.sync.gui.tree_model import DIFF_ROLE, SECTION_ROLE, Column, SyncTreeModel, TreeSection
from lizmap.sync.manifest import RemoteManifest
from lizmap.sync.model import Direction, FileStatus, Preference, SyncAction
from lizmap.sync.options import SyncOptions
from lizmap.sync.pair import PairKind, PairSettings
from lizmap.sync.state import SyncState

from .test_sync_executor import FakeBackend, compare_now, make_pair, write


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


def load(model: SyncTreeModel, *comparisons: Comparison):
    """Display comparisons in the model, one section each.

    :param model: The model.
    :param comparisons: The comparisons.
    """
    model.set_sections([TreeSection(index, f"Section {index}", c) for index, c in enumerate(comparisons)])


def test_tree_model(sample: Sample):
    """Test the structure, the data and the edition of the tree model."""
    backend, root, state = sample
    model = SyncTreeModel()
    QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Fatal, model)
    comparison = compare_now(backend, root, state).comparison
    model.set_sections([TreeSection("repository", "Repository", comparison, "a note", "a tooltip")])

    # A root by section, then directories first
    assert model_rows(model) == [
        "Repository",
        "  data",
        "    zones.gpkg",
        "  media",
        "    logo.png",
        "  project.qgs",
        "  project.qgs.cfg",
        "  project.qgs~",
    ]

    section = model.index(0, 0)
    assert section.data(SECTION_ROLE) == "repository"
    assert model.index(0, Column.Status).data() == "3 action(s) - a note"
    assert section.data(Qt.ItemDataRole.ToolTipRole) == "a tooltip"
    assert model.section_index("repository") == section
    assert not model.section_index("other").isValid()

    data = model.index(0, 0, section)
    zones = model.index(0, 0, data)
    assert model.index(0, Column.Status, data).data() == "Missing on the server"
    assert model.index(0, Column.Action, data).data(Qt.ItemDataRole.EditRole) == SyncAction.Upload
    assert model.index(0, Column.Status, section).data() == "1 action(s)"
    assert zones.data(DIFF_ROLE).path == "data/zones.gpkg"
    assert zones.data(SECTION_ROLE) is None
    assert model.index(0, Column.Remote, data).data() == "-"

    # Only files with several possible actions are editable
    excluded = model.index(4, Column.Action, section)
    assert excluded.data(DIFF_ROLE).status == FileStatus.Excluded
    assert not (model.flags(excluded) & Qt.ItemFlag.ItemIsEditable)
    action = model.index(0, Column.Action, data)
    assert model.flags(action) & Qt.ItemFlag.ItemIsEditable

    # Edition of an action, the summary of the directory changes
    assert model.setData(action, SyncAction.Nothing)
    assert model.index(0, Column.Status, section).data() == ""
    assert not model.setData(action, SyncAction.Download)

    # Bulk changes on a directory, then on all files
    model.apply_preference(Preference.Remote, data)
    assert action.data(Qt.ItemDataRole.EditRole) == SyncAction.DeleteLocal
    model.reset_actions()
    assert action.data(Qt.ItemDataRole.EditRole) == SyncAction.Upload

    model.set_sections([])
    assert model.rowCount() == 0


def test_tree_model_sections(sample: Sample, tmp_path: Path):
    """Test several sections, the bulk changes apply to all of them."""
    backend, root, state = sample
    media = FakeBackend()
    media.put("upload/photo.jpg", b"jpg")
    media_root = tmp_path.parent / f"{tmp_path.name}-media"
    model = SyncTreeModel()
    QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Fatal, model)
    load(
        model,
        compare_now(backend, root, state).comparison,
        compare_now(media, media_root, SyncState("s", "m", str(media_root))).comparison,
    )

    assert [model.index(row, 0).data() for row in range(model.rowCount())] == ["Section 0", "Section 1"]
    assert model_rows(model, model.index(1, 0)) == ["upload", "  photo.jpg"]
    model.apply_preference(Preference.Nothing)
    assert all(
        diff.action == SyncAction.Nothing for section in model.sections for diff in section.comparison.diffs
    )


def test_filter_proxy(sample: Sample):
    """Test the filter modes and the search."""
    backend, root, state = sample
    model = SyncTreeModel()
    load(model, compare_now(backend, root, state).comparison)
    proxy = SyncFilterProxy()
    proxy.setSourceModel(model)
    QAbstractItemModelTester(proxy, QAbstractItemModelTester.FailureReportingMode.Fatal, proxy)

    # Identical and excluded files are hidden by default
    assert model_rows(proxy) == [
        "Section 0",
        "  data",
        "    zones.gpkg",
        "  media",
        "    logo.png",
        "  project.qgs",
    ]

    proxy.set_mode(FilterMode.All)
    assert len(model_rows(proxy)) == 8

    proxy.set_text("LOGO")
    assert model_rows(proxy) == ["Section 0", "  media", "    logo.png"]

    # The root of a section stays visible
    proxy.set_text("")
    proxy.set_mode(FilterMode.Problems)
    assert model_rows(proxy) == ["Section 0"]

    # A file without action disappears from the files to synchronise
    proxy.set_mode(FilterMode.Actions)
    assert len(model_rows(proxy)) == 6
    section = model.index(0, 0)
    model.setData(model.index(0, Column.Action, model.index(0, 0, section)), SyncAction.Nothing)
    assert model_rows(proxy) == ["Section 0", "  media", "    logo.png", "  project.qgs"]


def test_action_delegate(sample: Sample):
    """Test the combobox editing the action of a file."""
    backend, root, state = sample
    model = SyncTreeModel()
    load(model, compare_now(backend, root, state).comparison)
    section = model.index(0, 0)
    index = model.index(0, Column.Action, model.index(1, 0, section))
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

    # No editor for a directory nor a section
    assert (
        delegate.createEditor(parent, QStyleOptionViewItem(), model.index(1, Column.Action, section)) is None
    )
    assert delegate.createEditor(parent, QStyleOptionViewItem(), model.index(0, Column.Action)) is None


def panel_for(
    backend: FakeBackend,
    root: Path,
    state: SyncState,
    tmp_path: Path,
    media: FakeBackend | None = None,
    **kwargs,
) -> SyncPanel:
    """Build a panel with a context in memory, accepting all questions.

    :param backend: The backend of the repository.
    :param root: The local directory of the repository.
    :param state: The state of the repository.
    :param tmp_path: Temporary directory of the test, the state files and the shared media are
        written next to it, outside the synchronised directory.
    :param media: The backend of the shared media, no shared media if None.
    :param kwargs: Extra parameters of the context.
    :return: The panel.
    """
    pairs = [make_pair(backend, root, state)]
    if media:
        media_root = tmp_path.parent / f"{tmp_path.name}-media"
        media_state = SyncState("s", "media", str(media_root))
        settings = PairSettings(Direction.PullOnly, ("upload/**",), None)
        pairs.append(make_pair(media, media_root, media_state, settings, PairKind.SharedMedia))

    def provider() -> SyncContext:
        """Context of the tests.

        :return: The context.
        """
        return SyncContext(pairs=pairs, **kwargs)

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
    # Only the repository, the row of the shared media is hidden
    assert panel.direction_repository.isVisibleTo(panel)
    assert not panel.direction_shared_media.isVisibleTo(panel)
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
    assert (tmp_path.parent / f"{tmp_path.name}-repository-state.json").exists()
    assert panel.summary.text() == "Nothing to synchronise."
    assert not panel.sync_button.isEnabled()


def test_panel_shared_media(sample: Sample, tmp_path: Path):
    """Test the shared media, in download only mode, with a protected file, then a change of direction."""
    backend, root, state = sample
    media = FakeBackend()
    media.put("upload/photo.jpg", b"jpg")
    media_root = tmp_path.parent / f"{tmp_path.name}-media"
    write(media_root / "logo.png", b"local logo")
    panel = panel_for(backend, root, state, tmp_path, media=media)
    directions = []
    panel.directionChanged.connect(lambda kind, direction: directions.append((kind, direction)))

    panel.compare()
    wait_for(lambda: not panel.busy)
    assert panel.model.rowCount() == 2
    media_section = panel.model.section_index(PairKind.SharedMedia)
    assert media_section.data() == "shared_media"
    actions = {d.path: d.action for d in panel.model.sections[1].comparison.diffs}
    # Download only: the local logo is not sent
    assert actions == {"logo.png": SyncAction.Nothing, "upload/photo.jpg": SyncAction.Download}

    # Two-way, compared again without any request: the logo is sent
    calls = len(media.calls)
    combos = [panel.direction_repository, panel.direction_shared_media]
    assert panel.direction_shared_media.isVisibleTo(panel)
    assert [combo.currentData() for combo in combos] == ["two_way", "pull_only"]
    combos[1].setCurrentIndex(combos[1].findData("two_way"))
    assert directions == [(PairKind.SharedMedia, Direction.TwoWay)]
    actions = {d.path: d.action for d in panel.model.sections[1].comparison.diffs}
    assert actions == {"logo.png": SyncAction.Upload, "upload/photo.jpg": SyncAction.Download}
    assert len(media.calls) == calls

    synchronised = []
    panel.synchronised.connect(synchronised.append)
    panel.synchronise()
    wait_for(lambda: synchronised and not panel.busy)
    assert "Synchronisation done." in panel.message.text()
    assert (media_root / "upload" / "photo.jpg").read_bytes() == b"jpg"
    assert media.files["logo.png"] == b"local logo"


def test_panel_protected_warning(sample: Sample, tmp_path: Path):
    """Test the warning when a file produced by the server is deleted by an explicit choice."""
    backend, root, state = sample
    backend.put("media/upload/photo.jpg", b"jpg")
    panel = panel_for(backend, root, state, tmp_path)
    panel._provider().pairs[0].settings = PairSettings(protected_patterns=("media/upload/**",))
    panel.compare()
    wait_for(lambda: not panel.busy)

    diff = next(d for d in panel.model.sections[0].comparison.diffs if d.path == "media/upload/photo.jpg")
    assert diff.protected
    diff.choose(SyncAction.DeleteRemote)
    panel.confirm = lambda title, text: panel.questions.append(text) and False
    panel.synchronise()
    assert "produced by the server" in panel.questions[0]
    assert "media/upload/photo.jpg" in panel.questions[0]


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
    """Test a directory missing on the server, created by the first upload."""
    _backend, root, state = sample

    class MissingDirectory(FakeBackend):
        """A server without the directory of the repository."""

        exists = False

        def fetch_manifest(self, feedback: QgsFeedback | None = None) -> RemoteManifest:
            """Fail until the directory is created.

            :param feedback: Not used.
            :return: The manifest.
            """
            if not self.exists:
                raise BackendError("Not found", 404)
            return super().fetch_manifest(feedback)

        def make_directory(self, path: str, feedback: QgsFeedback | None = None):
            """Create the directory of the repository.

            :param path: Relative path, empty for the directory itself.
            :param feedback: Not used.
            """
            if path == "":
                self.exists = True
            super().make_directory(path, feedback)

    backend = MissingDirectory()
    panel = panel_for(backend, root, state, tmp_path)
    panel.compare()
    wait_for(lambda: not panel.busy)
    assert "missing on the server" in panel.model.index(0, Column.Status).data()

    synchronised = []
    panel.synchronised.connect(synchronised.append)
    panel.synchronise()
    wait_for(lambda: synchronised and not panel.busy)
    assert ("mkdir", "") in backend.calls
    assert "data/zones.gpkg" in backend.files
    assert "Synchronisation done." in panel.message.text()


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


def test_options_dialog():
    """Test the options dialog: values, unsupported lines, changed rules, defaults."""
    options = SyncOptions(
        exclude_hidden=False,
        max_size=20 * MEGABYTE,
        download_threshold=None,
        protected_repository=("media/upload/**", "forms/**"),
    )
    rules = {PairKind.Repository: ("Repository", "*.tif\n"), PairKind.SharedMedia: ("Shared media", None)}
    dialog = SyncOptionsDialog(None, options, rules)

    assert dialog.options() == options
    assert dialog.rules_editors[PairKind.SharedMedia].toPlainText() == default_rules_text()
    assert dialog.changed_rules() == {}

    dialog.rules_editors[PairKind.Repository].setPlainText("*.tif\n!keep.tif\n")
    assert "!keep.tif" in dialog.invalid_label.text()
    assert dialog.changed_rules() == {PairKind.Repository: "*.tif\n!keep.tif\n"}

    dialog.restore_defaults()
    assert dialog.options() == SyncOptions()
    assert dialog.invalid_label.text() == ""
    assert dialog.changed_rules() == {PairKind.Repository: default_rules_text()}

    # The default text gives the default rules, the comments are ignored
    assert parse_rules(default_rules_text()) == (DEFAULT_EXCLUDE_PATTERNS, [])


def test_options_settings():
    """Test the personal options saved in the QGIS settings."""
    options = SyncOptions(
        exclude_hidden=False,
        max_size=3 * MEGABYTE,
        download_threshold=None,
        protected_shared_media=("upload/**", "photos/"),
    )
    save_options(options)
    assert load_options() == options
    save_options(SyncOptions())
    assert load_options() == SyncOptions()


def test_panel_options(sample: Sample, tmp_path: Path):
    """Test the options button: a new comparison after a change."""
    backend, root, state = sample
    panel = panel_for(backend, root, state, tmp_path)
    changes = []
    panel._open_options = lambda: changes.append(True) or True
    panel.options_button.setVisible(True)

    # No comparison yet, nothing to refresh
    panel.edit_options()
    assert not panel.busy

    panel.compare()
    wait_for(lambda: not panel.busy)
    panel.edit_options()
    assert panel.busy
    wait_for(lambda: not panel.busy)
    assert changes == [True, True]
