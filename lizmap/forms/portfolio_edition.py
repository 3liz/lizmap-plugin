"""Dialog for portfolio edition."""

from typing import TYPE_CHECKING, Any, Dict, Optional

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QMessageBox,
    QTableWidgetItem,
)

from lizmap.definitions.base import InputType
from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.portfolio import GeometryType, PortfolioDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.forms.folio_portfolio_edition import FolioPortfolioEditionDialog
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui, resources_path

if TYPE_CHECKING:
    from lizmap.dialogs.main import LizmapDialog


CLASS = load_ui('ui_form_portfolio.ui')


class PortfolioEditionDialog(BaseEditionDialog, CLASS):

    def __init__(
        self,
        parent: Optional["LizmapDialog"] = None,
        unicity: Optional[Dict[str, str]] = None,
        lwc_version: Optional[LwcVersions] = None,
    ):
        super().__init__(parent, unicity, lwc_version)
        self.setupUi(self)
        self.parent = parent
        self._drawing_geometry = None
        self.config = PortfolioDefinitions()
        self.config.add_layer_widget('title', self.title)
        self.config.add_layer_widget('description', self.text_description)
        self.config.add_layer_widget('drawing_geometry', self.drawing_geometry)
        self.config.add_layer_widget('folios', self.folios)

        self.config.add_layer_label('title', self.label_title)
        self.config.add_layer_label('description', self.label_description)
        self.config.add_layer_label('drawing_geometry', self.label_drawing_geometry)
        self.config.add_layer_label('folios', self.label_folios)

        # noinspection PyCallByClass,PyArgumentList
        self.add_folio.setText('')
        self.add_folio.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.add_folio.setToolTip(tr('Add a new folio to the portfolio.'))
        self.remove_folio.setText('')
        self.remove_folio.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
        self.remove_folio.setToolTip(tr('Remove the selected folio from the portfolio.'))

        # Set folios table
        items = self.config.layer_config['folios']['items']
        self.folios.setColumnCount(len(items))
        for i, item in enumerate(items):
            sub_definition = self.config.layer_config[item]
            column = QTableWidgetItem(sub_definition['header'])
            column.setToolTip(sub_definition['tooltip'])
            self.folios.setHorizontalHeaderItem(i, column)
        header = self.folios.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.folios.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.folios.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.folios.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.folios.setAlternatingRowColors(True)

        # connect
        self.add_folio.clicked.connect(self.add_new_folio)
        self.remove_folio.clicked.connect(self.remove_selected_folio)
        self.drawing_geometry.currentTextChanged.connect(self.geometry_changed)

        self.setup_ui()

    def folios_collection(self, saved: bool = False) -> list:
        """Return the list of folios collection."""
        collection = list()
        rows = self.folios.rowCount()

        collection_definition = self.config.layer_config['folios']
        for row in range(rows):
            folio_data = dict()
            for i, sub_key in enumerate(collection_definition['items']):
                # Get the item
                item = self.folios.item(row, i)

                if item is None:
                    if saved:
                        raise Exception('Cell is not initialized ({}, {})'.format(row, i))
                    continue

                cell = item.data(Qt.ItemDataRole.UserRole)
                if cell is None or cell == '':
                    # Safeguard
                    # Do not put if not item, it might be False or 0
                    if saved:
                        # raise exception for required cell
                        if sub_key in ['layout', 'theme', 'zoom_method']:
                            raise Exception('Cell has no data ({}, {})'.format(row, i))
                    continue

                folio_data[sub_key] = cell

            collection.append(folio_data)

        return collection

    def save_collection(self):
        """Save a collection into JSON"""
        return self.folios_collection(True)

    # TODO Find if value is typable
    def load_collection(self, value: Any) -> None:
        """Load a collection into the table from JSON string."""
        for trace in value:
            row = self.folios.rowCount()
            self.folios.setRowCount(row + 1)
            self._edit_folio_row(row, trace)

    def add_new_folio(self):
        """Add a new folio in the table after clicking the 'add' button."""

        dialog = FolioPortfolioEditionDialog(
            self.parent, self.drawing_geometry.currentData(), self.folios_collection()
        )
        result = dialog.exec()
        if result != QDialog.DialogCode.Accepted:
            return

        data = dialog.save_form()
        row = self.folios.rowCount()
        self.folios.setRowCount(row + 1)
        self._edit_folio_row(row, data)

    def _edit_folio_row(self, row, data):
        """Internal function to edit a row."""
        for i, key in enumerate(self.config.layer_config['folios']['items']):
            cell = QTableWidgetItem()

            value = data.get(key)
            if not value and value != 0:
                cell.setText('')
                cell.setData(Qt.ItemDataRole.UserRole, '')
                self.folios.setItem(row, i, cell)
                continue

            input_type = self.config.layer_config[key]['type']
            if input_type == InputType.List:
                cell.setData(Qt.ItemDataRole.UserRole, value)
                cell.setData(Qt.ItemDataRole.ToolTipRole, value)

                items = self.config.layer_config[key].get('items')
                if items:
                    # Display label from Python enum
                    for item_enum in items:
                        if item_enum.value['data'] != value:
                            continue
                        cell.setText(item_enum.value['label'])
                        break
                else:
                    # Some settings are a list, but not using a Python enum yet
                    # Like folios and themes
                    cell.setText(value)

            elif input_type == InputType.Scale:
                cell.setData(Qt.ItemDataRole.UserRole, value)
                cell.setData(Qt.ItemDataRole.ToolTipRole, value)
                # Format scale value
                cell.setText(f'1:{value}')

            elif input_type == InputType.SpinBox:
                cell.setText(f'{value}')
                cell.setData(Qt.ItemDataRole.UserRole, value)
                cell.setData(Qt.ItemDataRole.ToolTipRole, value)

            else:
                raise Exception('InputType "{}" not implemented'.format(input_type))

            self.folios.setItem(row, i, cell)
        self.folios.clearSelection()

    def remove_selected_folio(self):
        """Remove the selected folio in the table after clicking the 'remove' button."""
        selection = self.folios.selectedIndexes()
        if len(selection) <= 0:
            return

        row = selection[0].row()
        self.folios.clearSelection()
        self.folios.removeRow(row)

    def geometry_changed(self):
        current_geometry = self.drawing_geometry.currentData()
        if current_geometry == self._drawing_geometry:
            return

        if current_geometry == GeometryType.Point.value['data'] \
            or self._drawing_geometry == GeometryType.Point.value['data']:

            if self.folios.rowCount() > 0:
                box = QMessageBox(self.parent)
                box.setIcon(QMessageBox.Icon.Question)
                box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')) )
                box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                box.setDefaultButton(QMessageBox.StandardButton.Yes)
                box.setWindowTitle(tr('Change the geometry'))
                box.setText(tr('Are you sure to change the geometry?\nIt will clear the folios table.'))

                result = box.exec()
                if result == QMessageBox.StandardButton.No:
                    for item_type in GeometryType:
                        if item_type.value['data'] != self._drawing_geometry:
                            continue
                        self.drawing_geometry.setCurrentText(item_type.value['label'])
                        break
                    return

                # clear the table
                self.folios.clearSelection()
                self.folios.setRowCount(0)

        self._drawing_geometry = current_geometry

    def validate(self) -> Optional[str]:
        upstream = super().validate()
        if upstream:
            return upstream

        if not self.title.text():
            return tr('The title is mandatory')

        if self.folios.rowCount() == 0:
            return tr('At least one folio has to be configured')

        return None
