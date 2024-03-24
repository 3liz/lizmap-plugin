__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from functools import partial
from pathlib import Path

from qgis.core import QgsProject
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QWidget,
)

from lizmap.toolbelt.i18n import tr
from lizmap.widgets.check_project import Header


class Headers:
    """ List of headers in the table. """

    def __init__(self):
        self.members = []
        self.name = Header('name', tr('Name'), tr("Name of file"))
        self.relative_path = Header('path', tr('Relative path'), tr("Relative path"))
        self.date_time = Header('date_time', tr('Date time'), tr("Date time on the server"))
        self.size = Header('size', tr('Size'), tr('Size on the server'))
        self.actions = Header('action', tr('Actions'), tr('Actions on the layer'))
        self.members.append(self.name)
        self.members.append(self.relative_path)
        self.members.append(self.date_time)
        self.members.append(self.size)
        self.members.append(self.actions)


class TableFiles(QTableWidget):

    """ Subclassing of QTableWidget in the plugin. """

    # noinspection PyUnresolvedReferences
    ABSOLUTE_PATH = Qt.UserRole
    RELATIVE_PATH = ABSOLUTE_PATH + 1

    val_Changed = pyqtSignal(int, str, name='valChanged')

    def setup(self):
        """ Setting up parameters. """
        # Do not use the constructor __init__, it's not working. Maybe because of UI files ?

        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setVisible(True)
        # Bug, same as self.sort()
        # self.setSortingEnabled(True)

        headers = Headers()
        self.setColumnCount(len(headers.members))
        for i, header in enumerate(headers.members):
            column = QTableWidgetItem(header.label)
            column.setToolTip(header.tooltip)
            self.setHorizontalHeaderItem(i, column)

    def add_file(self, file_path: Path, icon: QIcon):
        """ Add a file in the table. """
        row = self.rowCount()
        self.setRowCount(row + 1)

        column = 0

        # Name file
        item = QTableWidgetItem(file_path.name)
        item.setIcon(icon)
        self.setItem(row, column, item)
        column += 1

        # Path file
        absolute_path = Path(file_path.absolute())
        project_home = Path(QgsProject.instance().absolutePath())
        relative_path = absolute_path.relative_to(project_home)

        item = QTableWidgetItem(str(relative_path))
        item.setToolTip(str(file_path))
        item.setData(self.ABSOLUTE_PATH, file_path.absolute())
        item.setData(self.RELATIVE_PATH, relative_path)
        self.setItem(row, column, item)
        column += 1

        # Date file
        item = QTableWidgetItem(tr("Unknown"))
        self.setItem(row, column, item)
        column += 1

        # Size file
        item = QTableWidgetItem(tr("Unknown"))
        self.setItem(row, column, item)
        column += 1

        # Actions
        remove_button = QToolButton()
        remove_button.setText('')
        remove_button.setIcon(QIcon(":/images/themes/default/mActionDeleteSelected.svg"))
        remove_button.setToolTip(tr('Remove the remote file'))
        remove_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        remove_button.clicked.connect(partial(self.button_remove_layer, row))

        cell = QWidget()
        hbox = QHBoxLayout(cell)
        hbox.addStretch()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addWidget(remove_button)
        self.setCellWidget(row, column, cell)

    def file_status(self, row: int, date, size):
        cell = QTableWidgetItem(date)
        self.setItem(row, 2, cell)
        cell = QTableWidgetItem(size)
        self.setItem(row, 3, cell)

    def button_remove_layer(self, index: int):
        self.val_Changed.emit(index, 'using-slider')
