"""Helper to sort a QTableWidget by clicking on a column header."""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidget

__copyright__ = "Copyright 2024, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"

# Dynamic attributes stored on the table widget to remember the current sort.
_SORT_COLUMN = "_lizmap_sort_column"
_SORT_ORDER = "_lizmap_sort_order"


def make_table_sortable(table: QTableWidget):
    """Enable sorting the rows by clicking on a column header.

    Behaves like the QGIS attribute table: a click sorts by that column,
    a second click on the same column reverses the order.

    We do not use QTableWidget.setSortingEnabled() on purpose. That property
    would sort the table on load (destroying any saved row order) and re-sort
    on every insertion (which corrupts the row content while it is being
    populated). Instead we trigger a one-shot sort only when the user clicks
    on a header.
    """
    setattr(table, _SORT_COLUMN, None)
    setattr(table, _SORT_ORDER, Qt.SortOrder.AscendingOrder)
    header = table.horizontalHeader()
    header.setSectionsClickable(True)
    header.setSortIndicatorShown(True)
    header.sectionClicked.connect(lambda column: sort_table_by_column(table, column))


def sort_table_by_column(table: QTableWidget, column: int):
    """Sort the rows by the given column, toggling ascending/descending."""
    if column < 0:
        return

    if getattr(table, _SORT_COLUMN, None) == column \
            and getattr(table, _SORT_ORDER, Qt.SortOrder.AscendingOrder) == Qt.SortOrder.AscendingOrder:
        order = Qt.SortOrder.DescendingOrder
    else:
        order = Qt.SortOrder.AscendingOrder

    setattr(table, _SORT_COLUMN, column)
    setattr(table, _SORT_ORDER, order)
    table.horizontalHeader().setSortIndicator(column, order)
    table.sortItems(column, order)


def reset_table_sort_indicator(table: QTableWidget):
    """Reset the header sort indicator, e.g. after a manual row reorder.

    The rows no longer match any column sort, so we hide the indicator.
    """
    setattr(table, _SORT_COLUMN, None)
    table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
