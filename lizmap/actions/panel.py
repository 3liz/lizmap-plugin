"""Manager of the actions panel in the main dialog."""

from __future__ import annotations

import copy

from html import escape
from typing import TYPE_CHECKING

from qgis.core import QgsApplication, QgsProject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractButton,
    QDialog,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from lizmap.actions.config import (
    Action,
    ActionFormatError,
    ActionIssue,
    read_actions,
    validate_actions,
    write_actions,
)
from lizmap.actions.edition_dialog import ActionEditionDialog
from lizmap.toolbelt.i18n import tr

if TYPE_CHECKING:
    from pathlib import Path

__copyright__ = "Copyright 2026, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"


class ActionsPanel:
    """Manage the list of actions in the main dialog, read from and written to the action file.

    The file is only written if the user has changed the actions.
    If the file cannot be read, it is only replaced after a confirmation of the user.
    """

    def __init__(
        self,
        parent: QWidget,
        table: QTableWidget,
        add_button: QAbstractButton,
        edit_button: QAbstractButton,
        duplicate_button: QAbstractButton,
        remove_button: QAbstractButton,
        up_button: QAbstractButton,
        down_button: QAbstractButton,
        issues_label: QLabel,
        project: QgsProject | None = None,
    ):
        """Constructor.

        :param parent: The parent widget, for the dialogs.
        :param table: The table listing the actions.
        :param add_button: The button to add an action.
        :param edit_button: The button to edit the selected action.
        :param duplicate_button: The button to duplicate the selected action.
        :param remove_button: The button to remove the selected action.
        :param up_button: The button to move up the selected action.
        :param down_button: The button to move down the selected action.
        :param issues_label: The label displaying the errors and warnings.
        :param project: The QGIS project, the current one by default.
        """
        self.parent = parent
        self.table = table
        self.issues_label = issues_label
        self.project = project or QgsProject.instance()

        self.path: Path | None = None
        self.actions: list[Action] = []
        # True if the actions have been changed by the user since the file has been read
        self.dirty = False
        # Error message if the file cannot be read
        self.read_error: str | None = None

        # Table
        headers = [tr("Name"), tr("Title"), tr("Scope"), tr("Layers")]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self.edit_action)

        # Buttons
        buttons = (
            (add_button, "symbologyAdd.svg", tr("Add a new action"), self.add_action),
            (edit_button, "symbologyEdit.svg", tr("Edit the selected action"), self.edit_action),
            (
                duplicate_button,
                "mActionEditCopy.svg",
                tr("Duplicate the selected action"),
                self.duplicate_action,
            ),
            (remove_button, "symbologyRemove.svg", tr("Remove the selected action"), self.remove_action),
            (up_button, "mActionArrowUp.svg", tr("Move up the selected action"), self.move_up),
            (down_button, "mActionArrowDown.svg", tr("Move down the selected action"), self.move_down),
        )
        for button, icon, tooltip, slot in buttons:
            button.setText("")
            button.setIcon(QIcon(QgsApplication.iconPath(icon)))
            button.setToolTip(tooltip)
            button.clicked.connect(slot)

        self.refresh()

    def load(self, path: Path | None):
        """Read the action file and display the actions.

        :param path: Path of the action file, None if the project is not saved yet.
        """
        self.path = path
        self.actions = []
        self.dirty = False
        self.read_error = None

        if path:
            try:
                self.actions = read_actions(path)
            except ActionFormatError as e:
                self.read_error = str(e)

        self.refresh()

    def reload(self, path: Path | None):
        """Read again the action file, after a confirmation if the actions have been changed.

        :param path: Path of the action file, None if the project is not saved yet.
        """
        if self.dirty:
            answer = QMessageBox.question(
                self.parent,
                tr("Actions"),
                tr("The changes in the actions will be lost. Do you want to read the action file again ?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.load(path)

    def save(self) -> bool:
        """Write the action file if the actions have been changed.

        The file is removed if there is no action anymore.

        :return: True if the file has been written or removed.
        """
        if not self.dirty or not self.path:
            return False
        write_actions(self.path, self.actions)
        self.dirty = False
        return True

    def issues(self) -> list[ActionIssue]:
        """Errors and warnings of the actions.

        :return: The issues.
        """
        return validate_actions(self.actions, self.project)

    def has_errors(self) -> bool:
        """Check if an action has an error, warnings are not blocking.

        :return: True if at least one action has an error.
        """
        return any(not issue.warning for issue in self.issues())

    def refresh(self):
        """Display the actions in the table and their issues."""
        self.table.setRowCount(0)
        for row, action in enumerate(self.actions):
            self.table.insertRow(row)

            # Layer names, or IDs if the layers are not in the project
            names = []
            for layer_id in action.layers if action.scope.has_layers() else []:
                layer = self.project.mapLayer(layer_id)
                names.append(layer.name() if layer else layer_id)

            values = (action.name, action.title, action.scope.value, ", ".join(names))
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(action.description or action.title)
                self.table.setItem(row, column, item)

        # Enable the panel only if the project is saved
        enabled = self.path is not None
        self.table.setEnabled(enabled)

        # File which cannot be read, then issues of the actions
        lines = []
        if not enabled:
            lines.append(escape(tr("The project must be saved before adding some actions.")))
        if self.read_error:
            lines.append(f"<span style='color:red'>{escape(self.read_error)}</span>")
        for issue in self.issues():
            color = "orange" if issue.warning else "red"
            lines.append(
                f"<span style='color:{color}'><b>{escape(issue.action)}</b> : {escape(issue.message)}</span>"
            )
        self.issues_label.setText("<br>".join(lines))
        self.issues_label.setVisible(bool(lines))

    def _set_actions(self, actions: list[Action], selected_row: int | None = None):
        """Replace the actions after a change by the user.

        :param actions: The new list of actions.
        :param selected_row: The row to select after the change.
        """
        self.actions = actions
        self.dirty = True
        self.refresh()
        if selected_row is not None and 0 <= selected_row < len(actions):
            self.table.selectRow(selected_row)

    def _confirm_replace_unreadable_file(self) -> bool:
        """Ask the user to replace the action file which cannot be read.

        :return: True if there is no read error, or if the user accepts to replace the file.
        """
        if not self.read_error:
            return True

        answer = QMessageBox.question(
            self.parent,
            tr("Actions"),
            "{}\n\n{}".format(
                self.read_error,
                tr("The current action file will be replaced when saving. Do you want to continue ?"),
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False

        self.read_error = None
        return True

    def _selected_row(self) -> int | None:
        """The selected row in the table.

        :return: The row, or None if no action is selected.
        """
        row = self.table.currentRow()
        return row if 0 <= row < len(self.actions) else None

    def _open_dialog(self, action: Action | None, other_names: list[str]) -> Action | None:
        """Open the edition dialog.

        :param action: The action to edit, or None for a new one.
        :param other_names: Names of the other actions.
        :return: The action from the dialog, or None if the user has cancelled.
        """
        dialog = ActionEditionDialog(self.parent, self.project, action, other_names)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.action()

    def add_action(self):
        """Add a new action, at the end of the list."""
        if not self.path or not self._confirm_replace_unreadable_file():
            return

        action = self._open_dialog(None, [a.name for a in self.actions])
        if action:
            self._set_actions([*self.actions, action], len(self.actions))

    def edit_action(self):
        """Edit the selected action."""
        row = self._selected_row()
        if row is None:
            return

        other_names = [a.name for i, a in enumerate(self.actions) if i != row]
        action = self._open_dialog(self.actions[row], other_names)
        if action:
            actions = list(self.actions)
            actions[row] = action
            self._set_actions(actions, row)

    def duplicate_action(self):
        """Duplicate the selected action, with a new name, after it."""
        row = self._selected_row()
        if row is None:
            return

        # Find a free name, such as 'buffer_copy' or 'buffer_copy_2'
        names = {a.name for a in self.actions}
        action = copy.deepcopy(self.actions[row])
        base = f"{action.name}_copy"
        action.name = base
        index = 2
        while action.name in names:
            action.name = f"{base}_{index}"
            index += 1

        actions = list(self.actions)
        actions.insert(row + 1, action)
        self._set_actions(actions, row + 1)

    def remove_action(self):
        """Remove the selected action."""
        row = self._selected_row()
        if row is None:
            return

        actions = list(self.actions)
        del actions[row]
        self._set_actions(actions, min(row, len(actions) - 1))

    def move_up(self):
        """Move up the selected action."""
        row = self._selected_row()
        if not row:
            return

        actions = list(self.actions)
        actions[row - 1], actions[row] = actions[row], actions[row - 1]
        self._set_actions(actions, row - 1)

    def move_down(self):
        """Move down the selected action."""
        row = self._selected_row()
        if row is None or row >= len(self.actions) - 1:
            return

        actions = list(self.actions)
        actions[row], actions[row + 1] = actions[row + 1], actions[row]
        self._set_actions(actions, row + 1)
