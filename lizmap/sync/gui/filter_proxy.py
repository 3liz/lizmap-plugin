"""Filter of the tree of the comparison."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from qgis.PyQt.QtCore import QModelIndex, QObject, QSortFilterProxyModel

from lizmap.sync.gui.tree_model import DIFF_ROLE
from lizmap.sync.model import FileStatus, SyncAction

if TYPE_CHECKING:
    from lizmap.sync.model import FileDiff


class FilterMode(Enum):
    """Which files are displayed."""

    # Files which are not identical nor excluded
    Changes = "changes"
    # Files with an action to run
    Actions = "actions"
    # Files needing a decision of the user
    Problems = "problems"
    # All files, identical and excluded ones included
    All = "all"


# Statuses needing a decision of the user
PROBLEM_STATUSES = (
    FileStatus.Conflict,
    FileStatus.Different,
    FileStatus.Unverified,
    FileStatus.DeletedLocal,
    FileStatus.DeletedRemote,
    FileStatus.CaseConflict,
)


class SyncFilterProxy(QSortFilterProxyModel):
    """Filter the files of the tree by mode and by text.

    A directory is displayed when at least one of its files is displayed.
    """

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.setRecursiveFilteringEnabled(True)
        self._mode = FilterMode.Changes
        self._text = ""

    def set_mode(self, mode: FilterMode):
        """Change the filter mode.

        :param mode: The mode.
        """
        self._mode = mode
        self.invalidateFilter()

    def set_text(self, text: str):
        """Filter the files by a part of their path.

        :param text: Text to search, case insensitive. Empty for all files.
        """
        self._text = text.strip().lower()
        self.invalidateFilter()

    def accepts(self, diff: FileDiff) -> bool:
        """Tell if a file is displayed.

        :param diff: The comparison result of the file.
        :return: True if the file matches the mode and the text.
        """
        if self._text and self._text not in diff.path.lower():
            return False
        if self._mode == FilterMode.Changes:
            return diff.status not in (FileStatus.Identical, FileStatus.Excluded)
        if self._mode == FilterMode.Actions:
            return diff.action != SyncAction.Nothing
        if self._mode == FilterMode.Problems:
            return diff.status in PROBLEM_STATUSES
        return True

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Accept a row of the source model.

        Directories are refused here, the recursive filtering displays them if a file is accepted.

        :param source_row: Row in the source model.
        :param source_parent: Parent index in the source model.
        :return: True if the row is displayed.
        """
        index = self.sourceModel().index(source_row, 0, source_parent)
        diff = index.data(DIFF_ROLE)
        return diff is not None and self.accepts(diff)
