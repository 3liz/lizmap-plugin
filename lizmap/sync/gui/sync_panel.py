"""Panel of the synchronisation between the local directories of the project and the server.

Several pairs of directories are synchronised together, each one is a root of the tree:
the Lizmap repository of the project, and the shared "media" directory.

The panel doesn't know the Lizmap dialog nor the QGIS project: everything needed is given by
a "context provider", called when the user clicks on "Compare".
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QModelIndex, QPersistentModelIndex, QPoint, Qt, QUrl, pyqtSignal, pyqtSlot
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QWidget,
)

from lizmap.sync.gui.action_delegate import ActionDelegate
from lizmap.sync.gui.filter_proxy import FilterMode, SyncFilterProxy
from lizmap.sync.gui.presentation import GREEN, RED, action_label, direction_label, file_size
from lizmap.sync.gui.tree_model import DIFF_ROLE, SECTION_ROLE, Column, SyncTreeModel, TreeSection
from lizmap.sync.model import Direction, Preference, SyncAction
from lizmap.sync.pair import PairKind
from lizmap.sync.plan import OperationKind
from lizmap.sync.tasks import CompareTask, SyncTask, recompare
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from lizmap.sync.model import FileStatus
    from lizmap.sync.pair import SyncPair
    from lizmap.sync.tasks import CompareResult

FORM_CLASS = load_ui("ui_sync_panel.ui")


class SyncUnavailable(Exception):
    """The synchronisation can't be run, the message explains why to the user."""


@dataclass
class SyncContext:
    """Everything needed to compare and synchronise, given by the plugin.

    :param pairs: The pairs of directories, the repository first.
    :param server_label: URL of the WebDAV server, the remote directories of the pairs are relative to it.
    :param preferences: Default preference by status, the default ones if None.
    :param protected_paths: Files used by the layers of the open project, relative to the directory
        of the repository.
    :param project_path: The open project, relative to the directory of the repository.
    """

    pairs: list[SyncPair]
    server_label: str = ""
    preferences: Mapping[FileStatus, Preference] | None = None
    protected_paths: frozenset[str] = field(default_factory=frozenset)
    project_path: str | None = None

    def pair(self, kind: PairKind) -> SyncPair | None:
        """Pair of a given kind.

        :param kind: The kind.
        :return: The pair, None if not synchronised.
        """
        return next((pair for pair in self.pairs if pair.kind == kind), None)


class SyncPanel(QWidget, FORM_CLASS):  # type: ignore[misc,valid-type]
    """Compare the local directory with the server, choose the actions, then synchronise.

    :param parent: Parent widget.
    :param context_provider: Called when the user compares, raises ``SyncUnavailable`` with a message
        for the user if the synchronisation is not possible.
    :param repository_combo: Combobox of the repositories in the dialog, mirrored at the top of the panel.
    :param new_repository: Called when the user wants to create a new repository.
    :param open_options: Called when the user wants to edit the options, returns True if they changed.
    """

    # Emitted after a synchronisation, with True if the open project has been downloaded
    synchronised = pyqtSignal(bool)
    # Emitted when the user changes the direction of a pair, with the PairKind and the Direction
    directionChanged = pyqtSignal(object, object)

    def __init__(
        self,
        parent: QWidget | None,
        context_provider: Callable[[], SyncContext],
        repository_combo: QComboBox | None = None,
        new_repository: Callable[[], None] | None = None,
        open_options: Callable[[], bool] | None = None,
    ):
        super().__init__(parent)
        self._provider = context_provider
        self._open_options = open_options
        self._source_combo = repository_combo
        self._context: SyncContext | None = None
        self._results: list[CompareResult] = []
        self._task: CompareTask | SyncTask | None = None
        # Result of the last synchronisation, displayed with the next comparison
        self._sync_message = ""

        self._build_interface(new_repository)
        self._update_buttons()

    # Interface

    def _build_interface(self, new_repository: Callable[[], None] | None):
        """Set up the widgets of the Designer file.

        :param new_repository: Called when the user wants to create a new repository.
        """
        self.setupUi(self)

        # Repository, mirroring the combobox of the dialog
        self.new_repository_button.setIcon(QgsApplication.getThemeIcon("/mActionNewFolder.svg"))
        self.new_repository_button.setVisible(new_repository is not None)
        if new_repository:
            self.new_repository_button.clicked.connect(new_repository)
        self._mirror_repository_combo()

        # Widgets of each pair of directories, in the grid
        self.pair_widgets: dict[PairKind, tuple[QLabel, QLabel, QLabel, QComboBox]] = {
            PairKind.Repository: (
                self.label_pair_repository,
                self.label_local_repository,
                self.label_remote_repository,
                self.direction_repository,
            ),
            PairKind.SharedMedia: (
                self.label_pair_shared_media,
                self.label_local_shared_media,
                self.label_remote_shared_media,
                self.direction_shared_media,
            ),
        }
        for kind, (_title, _local, _remote, combo) in self.pair_widgets.items():
            for direction in Direction:
                combo.addItem(direction_label(direction), direction.value)
            # A change compares again, without any request
            combo.currentIndexChanged.connect(
                lambda _index, k=kind, c=combo: self._direction_changed(k, Direction(c.currentData()))
            )

        # Comparison and filters
        self.compare_button.setIcon(QgsApplication.getThemeIcon("/mActionRefresh.svg"))
        self.compare_button.clicked.connect(self.compare)
        for mode, label in (
            (FilterMode.Changes, tr("Differences")),
            (FilterMode.Actions, tr("Files to synchronise")),
            (FilterMode.Problems, tr("Files needing a decision")),
            (FilterMode.All, tr("All files")),
        ):
            self.filter_mode.addItem(label, mode.value)
        self.search.setShowSearchIcon(True)

        # Tree of the files
        self.model = SyncTreeModel(self)
        self.proxy = SyncFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.tree.setModel(self.proxy)
        self.tree.setItemDelegateForColumn(Column.Action, ActionDelegate(self.tree))
        self.tree.setEditTriggers(
            QAbstractItemView.EditTrigger.SelectedClicked | QAbstractItemView.EditTrigger.DoubleClicked
        )
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        # All columns fit their content, a horizontal scroll bar is better than truncated names
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.filter_mode.currentIndexChanged.connect(self._filter_changed)
        self.search.valueChanged.connect(self._filter_changed)
        self.model.actionsChanged.connect(self._update_summary)

        # Bulk choices on all files, the options and the synchronisation on the same row
        self.bulk_buttons = []
        for button, tooltip, preference in (
            (self.button_prefer_local, tr("The local version wins for all files"), Preference.Local),
            (self.button_prefer_server, tr("The server version wins for all files"), Preference.Remote),
            (self.button_no_action, tr("Do nothing for all files"), Preference.Nothing),
            (self.button_default_choices, tr("Restore the default choices"), None),
        ):
            button.setToolTip(
                tooltip + "\n" + tr("Use a right click in the list for the selected files only.")
            )
            button.clicked.connect(lambda _checked, p=preference: self._apply_to(QModelIndex(), p))
            self.bulk_buttons.append(button)
        self.options_button.setIcon(QgsApplication.getThemeIcon("/mActionOptions.svg"))
        self.options_button.setVisible(self._open_options is not None)
        self.options_button.clicked.connect(self.edit_options)
        self.sync_button.setIcon(QgsApplication.getThemeIcon("/mActionStart.svg"))
        self.sync_button.clicked.connect(self.synchronise)

        self.cancel_button.clicked.connect(self.cancel)
        self.progress.setVisible(False)
        self.cancel_button.setVisible(False)

        self._set_directories(None)

    def _mirror_repository_combo(self):
        """Share the model of the combobox of the dialog, and keep both current items in sync."""
        if self._source_combo is None:
            self.repository.setVisible(False)
            self.label_repository_title.setVisible(False)
            return

        self.repository.setModel(self._source_combo.model())
        self.repository.setCurrentIndex(self._source_combo.currentIndex())

        def from_dialog(index: int):
            """Follow the dialog.

            :param index: The new index.
            """
            if self.repository.currentIndex() != index:
                self.repository.setCurrentIndex(index)
            self.invalidate()

        def to_dialog(index: int):
            """Update the dialog.

            :param index: The new index.
            """
            if self._source_combo and self._source_combo.currentIndex() != index:
                self._source_combo.setCurrentIndex(index)

        self._source_combo.currentIndexChanged.connect(from_dialog)
        self.repository.currentIndexChanged.connect(to_dialog)

    def _set_directories(self, context: SyncContext | None):
        """Display the WebDAV server, then the local and remote directories and the direction of each pair.

        :param context: The context, None if not known yet.
        """
        self.label_help.setVisible(context is None)
        self.label_server_title.setVisible(context is not None)
        self.label_server.setText(context.server_label if context else "")
        self.label_server.setVisible(context is not None)

        for kind, (title, local, remote, combo) in self.pair_widgets.items():
            pair = context.pair(kind) if context else None
            for widget in (title, local, remote, combo):
                widget.setVisible(pair is not None)
            if pair is None:
                continue

            title.setText(pair.label)
            url = QUrl.fromLocalFile(str(pair.root)).toString()
            local.setText(f"<a href='{url}'>{pair.root}</a>")
            remote.setText(f"⇄ {pair.remote_label}")
            # Without signal, the direction comes from the settings, it's not a choice of the user
            combo.blockSignals(True)
            combo.setCurrentIndex(combo.findData(pair.settings.direction.value))
            combo.blockSignals(False)

    def _direction_changed(self, kind: PairKind, direction: Direction):
        """Apply the new direction of a pair to its comparison.

        :param kind: The kind of pair.
        :param direction: The new direction.
        """
        self.directionChanged.emit(kind, direction)
        for index, result in enumerate(self._results):
            if result.pair.kind == kind:
                settings = replace(result.pair.settings, direction=direction)
                preferences = self._context.preferences if self._context else None
                self._results[index] = recompare(result, settings, preferences)
        if self._results:
            self._display_results()

    def _pair_of(self, index: QModelIndex) -> SyncPair | None:
        """Pair of a row of the tree.

        :param index: Index in the proxy.
        :return: The pair, None if unknown.
        """
        while index.parent().isValid():
            index = index.parent()
        kind = index.data(SECTION_ROLE)
        return self._context.pair(kind) if self._context and kind else None

    # State of the widgets

    @property
    def busy(self) -> bool:
        """Tell if a task is running.

        :return: True during a comparison or a synchronisation.
        """
        return self._task is not None

    def _update_buttons(self):
        """Enable or disable the widgets according to the current state."""
        busy = self.busy
        has_actions = any(section.comparison.to_run() for section in self.model.sections)
        self.compare_button.setEnabled(not busy)
        self.options_button.setEnabled(not busy)
        self.repository.setEnabled(not busy)
        self.new_repository_button.setEnabled(not busy)
        self.sync_button.setEnabled(not busy and has_actions)
        for button in self.bulk_buttons:
            button.setEnabled(not busy and bool(self.model.sections))
        for _title, _local, _remote, combo in self.pair_widgets.values():
            combo.setEnabled(not busy)
        self.tree.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.cancel_button.setVisible(busy)

    def _show_message(self, text: str, color: str | None = None):
        """Display a message under the buttons.

        :param text: The message, rich text.
        :param color: Color of the text, the default one if None.
        """
        self.message.setText(f"<span style='color:{color}'>{text}</span>" if color else text)

    def _append_log(self, text: str):
        """Add a line in the detailed log.

        :param text: The line.
        """
        self.log.appendPlainText(text)

    def _update_summary(self) -> None:
        """Display the number of files and bytes to transfer, by action."""
        if not self.model.sections:
            self.summary.setText("")
            self._update_buttons()
            return

        # Sum of the summaries of all pairs
        totals: dict[SyncAction, list[int]] = {}
        for section in self.model.sections:
            for action, (count, size) in section.comparison.summary().items():
                total = totals.setdefault(action, [0, 0])
                total[0] += count
                total[1] += size

        parts = []
        for action, (count, size) in totals.items():
            text = f"{action_label(action)} : {count}"
            if action in (SyncAction.Upload, SyncAction.Download):
                text += f" ({file_size(size)})"
            parts.append(text)
        self.summary.setText(" | ".join(parts) if parts else tr("Nothing to synchronise."))
        self._update_buttons()

    def _filter_changed(self):
        """Apply the filter mode and the searched text."""
        self.proxy.set_mode(FilterMode(self.filter_mode.currentData()))
        self.proxy.set_text(self.search.value())
        self.tree.expandAll()

    def invalidate(self):
        """Forget the comparison, for instance when the repository changed."""
        if self.busy:
            return
        self._results = []
        self._context = None
        self.model.set_sections([])
        self._set_directories(None)
        self._show_message("")

    # Choices

    def _apply_to(self, index: QModelIndex, preference: Preference | None):
        """Apply a preference to a subtree, or restore the default choices.

        :param index: Index in the proxy, invalid for all files.
        :param preference: The preference, None to restore the default choices.
        """
        source = self.proxy.mapToSource(index) if index.isValid() else QModelIndex()
        if preference is None:
            self.model.reset_actions(source)
        else:
            self.model.apply_preference(preference, source)

    def _apply_to_all(self, indexes: list[QModelIndex], preference: Preference | None):
        """Apply a preference to several subtrees, or restore their default choices.

        :param indexes: Indexes in the proxy.
        :param preference: The preference, None to restore the default choices.
        """
        # Persistent indexes, the proxy may change while applying the first preferences
        persistent = [QPersistentModelIndex(index) for index in indexes]
        for index in persistent:
            if index.isValid():
                self._apply_to(QModelIndex(index), preference)

    def _context_menu(self, position: QPoint):
        """Menu on the selected files and directories.

        :param position: Position of the click in the tree.
        """
        indexes = list(self.tree.selectionModel().selectedRows(Column.Name))
        if not indexes:
            return

        menu = QMenu(self.tree)
        for label, preference in (
            (tr("Prefer local"), Preference.Local),
            (tr("Prefer server"), Preference.Remote),
            (tr("Most recent"), Preference.Newest),
            (tr("No action"), Preference.Nothing),
            (tr("Default choice"), None),
        ):
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked, p=preference: self._apply_to_all(indexes, p))

        # Open the local directory of the clicked file
        diff = indexes[0].data(DIFF_ROLE)
        pair = self._pair_of(indexes[0])
        if pair and diff and diff.local:
            menu.addSeparator()
            folder = pair.root.joinpath(diff.path).parent
            action = menu.addAction(tr("Open the local directory"))
            action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def edit_options(self):
        """Edit the options, then compare again if a comparison is displayed."""
        if self.busy or self._open_options is None:
            return
        if self._open_options() and self._results:
            # The excluded files may change the scan, a new comparison is needed
            self.compare()

    def confirm(self, title: str, text: str) -> bool:
        """Ask a question to the user. Can be replaced in tests.

        :param title: Title of the dialog.
        :param text: The question, rich text.
        :return: True if the user accepted.
        """
        answer = QMessageBox.question(
            self, title, text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return answer == QMessageBox.StandardButton.Yes

    # Comparison

    def compare(self):
        """Compare the local directories with the server, in the background."""
        if self.busy:
            return

        try:
            context = self._provider()
        except SyncUnavailable as e:
            self._show_message(str(e), RED)
            return

        self._start_comparison(context)

    def _start_comparison(self, context: SyncContext):
        """Run the comparison task.

        :param context: The context of the synchronisation.
        """
        self._context = context
        self._results = []
        self._set_directories(context)
        self.model.set_sections([])
        self._show_message(tr("Comparison in progress…"))
        self.progress.setRange(0, 0)

        task = CompareTask(context.pairs, context.preferences)
        task.taskCompleted.connect(self._compare_finished)
        task.taskTerminated.connect(self._compare_finished)
        self._task = task
        self._update_buttons()
        QgsApplication.taskManager().addTask(task)

    def _display_results(self):
        """Display the comparisons, one root by pair."""
        sections = []
        for result in self._results:
            notes = []
            if not result.remote_exists:
                notes.append(tr("missing on the server, created by the first upload"))
            if not result.pair.root.is_dir():
                notes.append(tr("missing locally, created by the first download"))
            tooltip = f"{result.pair.root}\n{result.pair.remote_label}"
            sections.append(
                TreeSection(result.pair.kind, result.pair.label, result.comparison, ", ".join(notes), tooltip)
            )
        self.model.set_sections(sections)
        self.tree.expandAll()

    def _compare_finished(self):
        """Display the comparison, or the errors."""
        task = self._task
        self._task = None
        self._update_buttons()
        if not isinstance(task, CompareTask):
            return

        self._results = task.results
        self._display_results()
        for result in task.results:
            for path, error in result.local.errors.items():
                self._append_log(f"{result.pair.label} : {path} : {error}")

        # Errors of some pairs, the other ones are displayed
        lines = []
        if self._sync_message:
            lines.append(self._sync_message)
            self._sync_message = ""
        labels = {pair.kind: pair.label for pair in self._context.pairs} if self._context else {}
        for kind, error in task.errors.items():
            lines.append(f"<span style='color:{RED}'>{labels.get(kind, kind)} : {error}</span>")
        if task.results:
            count = sum(len(result.comparison.diffs) for result in task.results)
            lines.append(tr("{} files compared.").format(count))
        elif not task.errors:
            lines.append(tr("Comparison canceled."))
        self._show_message("<br>".join(lines))
        self._update_summary()

    # Synchronisation

    def _repository_result(self) -> CompareResult | None:
        """Comparison of the repository of the project.

        :return: The comparison, None if not available.
        """
        return next((r for r in self._results if r.pair.kind == PairKind.Repository), None)

    def _protected_operations(self) -> list[str]:
        """List the files used by the open project which will be replaced or deleted locally.

        :return: The relative paths, in the directory of the repository.
        """
        result = self._repository_result()
        if result is None or self._context is None:
            return []
        protected = set(self._context.protected_paths)
        if self._context.project_path:
            protected.add(self._context.project_path)
        return sorted(
            diff.path
            for diff in result.comparison.to_run()
            if diff.path in protected and diff.action in (SyncAction.Download, SyncAction.DeleteLocal)
        )

    def synchronise(self):
        """Ask for a confirmation, then run the synchronisation of all pairs in the background."""
        if self.busy or not self._results:
            return

        operations = [diff for result in self._results for diff in result.comparison.to_run()]
        if not operations:
            return

        # Confirmation, with a warning for deletions and files used by the project
        text = tr("Synchronise {} files?").format(len(operations)) + "<br>" + self.summary.text()
        deletions = [
            d.path for d in operations if d.action in (SyncAction.DeleteLocal, SyncAction.DeleteRemote)
        ]
        if deletions:
            text += "<br><br><b>" + tr("{} files will be deleted.").format(len(deletions)) + "</b>"
        protected_files = [d.path for d in operations if d.protected and d.action != SyncAction.Download]
        if protected_files:
            text += (
                "<br><br><b>"
                + tr("These files have been produced by the server, such as files sent with a web form:")
                + "</b><br>"
                + "<br>".join(protected_files[:10])
            )
        protected = self._protected_operations()
        if protected:
            text += (
                "<br><br><b>"
                + tr("These files are used by the open project, they will be replaced or deleted:")
                + "</b><br>"
                + "<br>".join(protected[:10])
                + "<br>"
                + tr("You should reload the project after the synchronisation.")
            )
        if not self.confirm(tr("Synchronisation"), text):
            return

        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._show_message(tr("Synchronisation in progress…"))
        task = SyncTask(self._results)
        # A method of the panel, not a lambda: the signal comes from the worker thread,
        # the progress bar must be updated in the thread of the interface
        task.progressChanged.connect(self._task_progress)
        task.taskCompleted.connect(self._sync_finished)
        task.taskTerminated.connect(self._sync_finished)
        self._task = task
        self._update_buttons()
        QgsApplication.taskManager().addTask(task)

    def _sync_finished(self):
        """Display the result of the synchronisation, then compare again."""
        task = self._task
        self._task = None
        self._update_buttons()
        if not isinstance(task, SyncTask):
            return

        for message in task.messages:
            self._append_log(message)

        # Summary of the result of all pairs
        labels = {pair.kind: pair.label for pair in self._context.pairs} if self._context else {}
        results = task.results
        lines = []
        canceled = any(result.canceled for result in results.values())
        if results and not task.errors and all(result.success for result in results.values()):
            lines.append(f"<span style='color:{GREEN}'>{tr('Synchronisation done.')}</span>")
        elif canceled or not results:
            lines.append(f"<span style='color:{RED}'>{tr('Synchronisation canceled.')}</span>")
        for kind, error in task.errors.items():
            lines.append(f"<span style='color:{RED}'>{labels.get(kind, kind)} : {error}</span>")
        for kind, result in results.items():
            for path, reason in {**result.conflicts, **result.errors}.items():
                lines.append(f"<span style='color:{RED}'>{labels.get(kind, kind)} : {path} : {reason}</span>")
            if result.trash:
                url = QUrl.fromLocalFile(str(result.trash)).toString()
                lines.append(
                    tr("Previous versions of local files are kept in the <a href='{}'>trash</a>.").format(url)
                )

        repository = results.get(PairKind.Repository)
        project_path = self._context.project_path if self._context else None
        project_downloaded = bool(
            repository
            and project_path
            and any(op.kind == OperationKind.Download and op.path == project_path for op in repository.done)
        )
        if project_downloaded:
            lines.append(f"<b>{tr('The project has been downloaded from the server, reload it.')}</b>")

        # Refresh the comparison with the same context, the states have been updated
        self._sync_message = "<br>".join(lines)
        self.synchronised.emit(project_downloaded)
        if self._context:
            self._start_comparison(self._context)

    @pyqtSlot(float)
    def _task_progress(self, value: float):
        """Display the progress of the running task.

        :param value: Progress in percent.
        """
        self.progress.setValue(int(value))

    def cancel(self):
        """Cancel the running task."""
        if self._task:
            self._task.cancel()
