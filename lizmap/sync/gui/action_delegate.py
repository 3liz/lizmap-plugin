"""Editor of the action of a file, a combobox with the allowed actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt
from qgis.PyQt.QtWidgets import QComboBox, QStyledItemDelegate, QStyleOptionViewItem, QWidget

from lizmap.sync.gui.presentation import action_icon, action_label
from lizmap.sync.gui.tree_model import DIFF_ROLE
from lizmap.sync.model import SyncAction

if TYPE_CHECKING:
    from lizmap.sync.model import FileDiff


class ActionDelegate(QStyledItemDelegate):
    """Edit the action of a file with a combobox, the new action is applied as soon as it's chosen."""

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QWidget | None:
        """Build the combobox with the allowed actions of the file.

        :param parent: Parent widget.
        :param option: Style options.
        :param index: Index of the "Action" cell.
        :return: The combobox, None for a directory.
        """
        diff: FileDiff | None = index.data(DIFF_ROLE)
        if diff is None:
            return None

        combo = QComboBox(parent)
        for action in diff.allowed_actions:
            # The value of the enum, a Python object can't be compared by Qt
            combo.addItem(action_icon(action), action_label(action), action.value)

        # Apply the action as soon as it's chosen
        def commit():
            """Send the chosen action to the model and close the editor."""
            self.commitData.emit(combo)
            self.closeEditor.emit(combo)

        combo.activated.connect(commit)
        return combo

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        """Select the current action in the combobox.

        :param editor: The combobox.
        :param index: Index of the "Action" cell.
        """
        action = index.data(Qt.ItemDataRole.EditRole)
        if isinstance(editor, QComboBox) and isinstance(action, SyncAction):
            editor.setCurrentIndex(max(0, editor.findData(action.value)))

    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex):
        """Send the chosen action to the model.

        :param editor: The combobox.
        :param model: The model.
        :param index: Index of the "Action" cell.
        """
        if isinstance(editor, QComboBox) and editor.currentData():
            model.setData(index, SyncAction(editor.currentData()), Qt.ItemDataRole.EditRole)
