__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from enum import Enum

from qgis.core import QgsMarkerSymbol, QgsSymbolLayerUtils
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QTableWidget,
    QTableWidgetItem,
)

from lizmap.qgis_plugin_tools.tools.i18n import tr


class Header:
    def __init__(self, label, tooltip):
        self.label = label
        self.tooltip = tooltip


class Headers(Header, Enum):
    Severity = tr('Severity'), tr("Severity of the error")
    Level = tr('Level'), tr("Level of the error")
    Object = tr('Object name'), tr("Name of the object bringing the issue")
    Name = tr('Name'), tr('Name of the error')
    Error = tr('Error'), tr('Description of the error')


class Severity:
    def __init__(self, data, label, tooltip, color):
        self.data = data
        self.label = label
        self.color = color
        self.tooltip = tooltip

    def marker(self) -> QIcon:
        pixmap = QgsSymbolLayerUtils.symbolPreviewPixmap(
            QgsMarkerSymbol.createSimple(
                {
                    "name": "circle",
                    "color": self.color,
                    "size": "2",
                }
            ),
            QSize(16, 16)
        )
        return QIcon(pixmap)


class Severities(Severity, Enum):
    Blocking = 'blocking', tr('Blocking'), tr('This is blocking the CFG file'), 'green'
    Important = 'important', tr('Important'), tr('This is important to fix, to improve performance'), 'red'
    Normal = 'normal', tr('Normal'), tr('This would be nice to have look'), 'blue'
    Low = 'low', tr('Low'), tr('Nice to do'), 'green'


class Level:
    def __init__(self, data: str, label: str, tooltip: str, icon: QIcon):
        self.data = data
        self.label = label
        self.icon = icon
        self.tooltip = tooltip


class Levels:
    GlobalConfig = Level(
        'global',
        tr('Global'),
        tr('Issue in the global configuration'),
        QIcon(':/images/themes/default/console/iconSettingsConsole.svg'),
    )
    Project = Level(
        'project',
        tr('Project'),
        tr('Issue at the project level, usually in Project properties dialog'),
        QIcon(':/images/themes/default/mIconQgsProjectFile.svg'),
    )
    Layer = Level(
        'layer',
        tr('Layer'),
        tr('Issue at the layer level'),
        QIcon(':/images/themes/default/algorithms/mAlgorithmMergeLayers.svg'),
    )


class Check:
    def __init__(self, title: str, description: str, tooltip: str, level: Level, severity: Severity):
        self.title = title
        self.description = description
        self.tooltip = tooltip
        self.level = level
        self.severity = severity


class Checks(Check, Enum):
    EstimatedMetadata = (
        tr('Estimated metadata'),
        tr("Estimated metadata is missing on the layer"),
        '<ul><li>Do that</li><li>And then that</li></ul>',
        Levels.Layer,
        Severities.Blocking,
    )
    DuplicatedLayerNameOrGroup = (
        tr('Duplicated layer name or group'),
        tr("It's not possible to store all the Lizmap configuration for these layer(s) or group(s)."),
        '<ul><li>'
        'You must change them to make them unique'
        '</li><li>'
        'Reconfigure their settings in the "Layers" tab of the plugin'
        '</li></ul>',
        Levels.Project,
        Severities.Blocking,
    )


class Error:
    def __init__(self, identifier: str, check: Check):
        self.identifier = identifier
        self.check = check


class TableCheck(QTableWidget):
    def setup(self):
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setVisible(True)

        self.setColumnCount(len(Headers))
        for i, header in enumerate(Headers):
            column = QTableWidgetItem(header.label)
            column.setToolTip(header.tooltip)
            self.setHorizontalHeaderItem(i, column)

    def add_error(self, error: Error):
        self.add_row(
            error.check.severity,
            error.check.level,
            error.identifier,
            error.check.title,
            error.check.description,
            error.check.tooltip
        )

    def add_row(self, severity: Severity, level: Level, identifier: str, error_name, error_description, error_help):
        row = self.rowCount()
        self.setRowCount(row + 1)

        item = QTableWidgetItem(severity.label)
        item.setData(Qt.UserRole, severity.data)
        item.setToolTip(severity.tooltip)
        item.setIcon(severity.marker())
        self.setItem(row, 0, item)

        item = QTableWidgetItem(level.label)
        item.setData(Qt.UserRole, level.data)
        item.setToolTip(level.tooltip)
        item.setIcon(level.icon)
        self.setItem(row, 1, item)

        item = QTableWidgetItem(identifier)
        item.setData(Qt.UserRole, identifier)
        self.setItem(row, 2, item)

        item = QTableWidgetItem(error_name)
        item.setData(Qt.UserRole, error_name)
        self.setItem(row, 3, item)

        item = QTableWidgetItem(error_description)
        item.setData(Qt.UserRole, error_description)
        item.setToolTip(error_help)
        self.setItem(row, 4, item)

# class TableModel(QAbstractTableModel):
#
#     def __init__(self, parent=None, *args, **kwargs):
#         super().__init__(parent, *args, **kwargs)
#         self.rows = []
#
#     def add_row(self, name, date, interest):
#         self.rows.append((name, date, interest))
#
#         index = self.createIndex(0,0)
#         self.dataChanged.emit(index, index, [Qt.DisplayRole])
#         # print(self.insertRow(0))
#         # print(self.rowCount())
#         # self.setData(self.createIndex(self.rowCount(), 0), name, Qt.EditRole)
#         # self.setData(self.createIndex(self.rowCount(), 1), date, Qt.EditRole)
#         # self.setData(self.createIndex(self.rowCount(), 2), interest, Qt.EditRole)
#
#     def rowCount(self, parent=None):
#         return len(self.rows)
#
#     def columnCount(self, parent):
#         return len(Headers)
#     def data(self, index, role):
#         if role != Qt.DisplayRole:
#             return QVariant()
#
#         if index.column() >= len(self.rows[index.row()]):
#             return 'a'
#
#         # What's the value of the cell at the given index?
#         return self.rows[index.row()][index.column()]
#
#     def headerData(self, section, orientation, role):
#         if orientation != Qt.Horizontal:
#             return ''
#
#         header: Header = list(Headers)[section]
#
#         if role == Qt.DisplayRole:
#             return header.label
#
#         if role == Qt.ToolTipRole:
#             return header.tooltip
