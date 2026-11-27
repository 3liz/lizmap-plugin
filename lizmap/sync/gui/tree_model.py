"""Tree model of the comparison: directories and files, with their status and the chosen action."""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, Any

from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, QObject, Qt, pyqtSignal

from lizmap.sync.diff import resolve_action
from lizmap.sync.gui.presentation import (
    action_color,
    action_icon,
    action_label,
    file_details,
    file_size,
    folder_icon,
    status_color,
    status_icon,
    status_label,
    status_tooltip,
)
from lizmap.sync.model import SyncAction
from lizmap.toolbelt.i18n import tr

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lizmap.sync.diff import Comparison
    from lizmap.sync.model import FileDiff, Preference

# Role giving the FileDiff of a file, None for a directory
DIFF_ROLE = Qt.ItemDataRole.UserRole + 1


class Column(IntEnum):
    """Columns of the tree."""

    Name = 0
    Status = 1
    Action = 2
    Local = 3
    Remote = 4


class _Node:
    """A directory or a file in the tree.

    :param name: Name of the file or of the directory.
    :param parent: Parent node, None for the invisible root.
    :param diff: Comparison result of a file, None for a directory.
    """

    def __init__(self, name: str, parent: _Node | None, diff: FileDiff | None = None):
        self.name = name
        self.parent = parent
        self.diff = diff
        self.children: list[_Node] = []
        self.row = 0

    def files(self) -> Iterator[FileDiff]:
        """Iterate over the files of the subtree.

        :return: The comparison results of the files.
        """
        if self.diff is not None:
            yield self.diff
        for child in self.children:
            yield from child.files()

    def sort(self):
        """Sort the children recursively, directories first, then by name."""
        self.children.sort(key=lambda node: (node.diff is not None, node.name.lower()))
        for row, child in enumerate(self.children):
            child.row = row
            child.sort()


class SyncTreeModel(QAbstractItemModel):
    """Tree of the comparison.

    The action of a file is edited in the "Action" column, with the ``EditRole``
    and a ``SyncAction`` value.
    """

    # Emitted when the chosen actions changed
    actionsChanged = pyqtSignal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._root = _Node("", None)
        self._comparison: Comparison | None = None

    @property
    def comparison(self) -> Comparison | None:
        """The displayed comparison.

        :return: The comparison, None if there isn't any.
        """
        return self._comparison

    def set_comparison(self, comparison: Comparison | None):
        """Display a comparison.

        :param comparison: The comparison, None to clear the tree.
        """
        self.beginResetModel()
        self._comparison = comparison
        self._root = _Node("", None)

        if comparison:
            directories: dict[str, _Node] = {"": self._root}
            for diff in comparison.diffs:
                # Create the missing parent directories
                segments = diff.path.split("/")
                parent = self._root
                for depth in range(len(segments) - 1):
                    path = "/".join(segments[: depth + 1])
                    if path not in directories:
                        directories[path] = _Node(segments[depth], parent)
                        parent.children.append(directories[path])
                    parent = directories[path]
                parent.children.append(_Node(segments[-1], parent, diff))
            self._root.sort()

        self.endResetModel()
        self.actionsChanged.emit()

    def _node(self, index: QModelIndex) -> _Node:
        """Node of an index.

        :param index: The index, invalid for the root.
        :return: The node.
        """
        return index.internalPointer() if index.isValid() else self._root

    # QAbstractItemModel API

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        """Index of a cell.

        :param row: Row in the parent.
        :param column: Column.
        :param parent: Parent index.
        :return: The index, invalid if out of range.
        """
        node = self._node(parent)
        if not (0 <= row < len(node.children) and 0 <= column < len(Column)):
            return QModelIndex()
        return self.createIndex(row, column, node.children[row])

    def parent(self, index: QModelIndex = QModelIndex()) -> QModelIndex:  # type: ignore[override]
        """Parent of an index.

        :param index: The index.
        :return: The parent index, invalid for a top-level row.
        """
        if not index.isValid():
            return QModelIndex()
        parent = self._node(index).parent
        if parent is None or parent is self._root:
            return QModelIndex()
        return self.createIndex(parent.row, 0, parent)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Number of children.

        :param parent: Parent index.
        :return: The number of rows.
        """
        if parent.column() > 0:
            return 0
        return len(self._node(parent).children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Number of columns.

        :param parent: Parent index.
        :return: The number of columns.
        """
        return len(Column)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        """Header of the columns.

        :param section: Column.
        :param orientation: Only horizontal headers are provided.
        :param role: Only the display role is provided.
        :return: The label.
        """
        if orientation != Qt.Orientation.Horizontal or role != Qt.ItemDataRole.DisplayRole:
            return None
        labels = {
            Column.Name: tr("File"),
            Column.Status: tr("Status"),
            Column.Action: tr("Action"),
            Column.Local: tr("Local"),
            Column.Remote: tr("Server"),
        }
        return labels[Column(section)]

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Flags of a cell, the action of a file is editable if several actions are allowed.

        :param index: The index.
        :return: The flags.
        """
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        diff = self._node(index).diff
        if index.column() == Column.Action and diff and len(diff.allowed_actions) > 1:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Content of a cell.

        :param index: The index.
        :param role: The role.
        :return: The value.
        """
        if not index.isValid():
            return None

        node = self._node(index)
        if role == DIFF_ROLE:
            return node.diff
        if node.diff is None:
            return self._directory_data(node, index.column(), role)
        return self._file_data(node, node.diff, index.column(), role)

    def _directory_data(self, node: _Node, column: int, role: int) -> Any:
        """Content of a cell of a directory.

        :param node: The directory.
        :param column: The column.
        :param role: The role.
        :return: The value.
        """
        if column == Column.Name:
            if role == Qt.ItemDataRole.DisplayRole:
                return node.name
            if role == Qt.ItemDataRole.DecorationRole:
                return folder_icon()
        elif column == Column.Status and role == Qt.ItemDataRole.DisplayRole:
            count = sum(1 for diff in node.files() if diff.action != SyncAction.Nothing)
            return tr("{} action(s)").format(count) if count else ""
        return None

    @staticmethod
    def _file_data(node: _Node, diff: FileDiff, column: int, role: int) -> Any:
        """Content of a cell of a file.

        :param node: The file.
        :param diff: The comparison result of the file.
        :param column: The column.
        :param role: The role.
        :return: The value.
        """
        if column == Column.Name:
            if role == Qt.ItemDataRole.DisplayRole:
                return node.name
            if role == Qt.ItemDataRole.DecorationRole:
                return status_icon(diff.status)
            if role == Qt.ItemDataRole.ToolTipRole:
                return diff.path

        elif column == Column.Status:
            if role == Qt.ItemDataRole.DisplayRole:
                return status_label(diff.status)
            if role == Qt.ItemDataRole.ForegroundRole:
                return status_color(diff.status)
            if role == Qt.ItemDataRole.ToolTipRole:
                tooltip = status_tooltip(diff.status)
                return f"{tooltip}\n{diff.exclusion}" if diff.exclusion else tooltip

        elif column == Column.Action:
            if role == Qt.ItemDataRole.DisplayRole:
                return action_label(diff.action)
            if role == Qt.ItemDataRole.EditRole:
                return diff.action
            if role == Qt.ItemDataRole.DecorationRole:
                return action_icon(diff.action)
            if role == Qt.ItemDataRole.ForegroundRole:
                return action_color(diff.action)

        elif column in (Column.Local, Column.Remote):
            # The size in the cell, the modification time in the tooltip, the dialog is narrow
            entry = diff.local if column == Column.Local else diff.remote
            if role == Qt.ItemDataRole.DisplayRole:
                return file_size(entry.size) if entry else "-"
            if role == Qt.ItemDataRole.ToolTipRole and entry:
                return file_details(entry.size, entry.mtime)

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Choose the action of a file.

        :param index: Index in the "Action" column.
        :param value: The ``SyncAction``.
        :param role: Only the edit role is supported.
        :return: True if the action has been changed.
        """
        if role != Qt.ItemDataRole.EditRole or index.column() != Column.Action:
            return False
        diff = self._node(index).diff
        if diff is None or not isinstance(value, SyncAction):
            return False
        try:
            diff.choose(value)
        except ValueError:
            return False

        self._notify_changed(self._node(index))
        return True

    # Bulk changes

    def apply_preference(self, preference: Preference, index: QModelIndex = QModelIndex()):
        """Choose the action of all files of a subtree from a preference.

        :param preference: The side which wins.
        :param index: The directory or the file, the whole tree if invalid.
        """
        node = self._node(index)
        for diff in node.files():
            diff.choose(resolve_action(diff, preference))
        self._notify_changed(node)

    def reset_actions(self, index: QModelIndex = QModelIndex()):
        """Restore the default action of all files of a subtree.

        :param index: The directory or the file, the whole tree if invalid.
        """
        node = self._node(index)
        for diff in node.files():
            diff.reset()
        self._notify_changed(node)

    def _notify_changed(self, node: _Node):
        """Notify the views that the actions of a subtree and the summaries of its parents changed.

        :param node: The root of the changed subtree.
        """
        self._emit_subtree(node)
        parent = node.parent
        while parent is not None and parent is not self._root:
            index = self.createIndex(parent.row, Column.Status, parent)
            self.dataChanged.emit(index, index)
            parent = parent.parent
        self.actionsChanged.emit()

    def _emit_subtree(self, node: _Node):
        """Notify the views that all rows of a subtree changed.

        :param node: The root of the subtree.
        """
        if node is not self._root and node.parent is not None:
            first = self.createIndex(node.row, 0, node)
            last = self.createIndex(node.row, len(Column) - 1, node)
            self.dataChanged.emit(first, last)
        for child in node.children:
            self._emit_subtree(child)
