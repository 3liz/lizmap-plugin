"""Manage tables and forms in Lizmap."""

import logging

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem, QCheckBox, QComboBox, QAbstractButton
from qgis.core import QgsProject, QgsMapLayerModel
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox

from .qgis_plugin_tools.tools.i18n import tr
from .qgis_plugin_tools.tools.resources import plugin_name


__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'

LOGGER = logging.getLogger(plugin_name())
NEW_ITEM_ROLE = Qt.UserRole + 100


class TableForm:

    def __init__(self, name, config):
        """Constructor

        :param name: Name of the form.
        :type name: basestring

        :param config: The Lizmap utils config.
        :type config: dict
        """
        self.name = name
        self.config = config
        self.fields_child_layer = []

        columns = self.table.columnCount()
        count_fields = len(self.fields)
        count_json_columns = len(self.headers)
        if columns != count_fields or columns != count_json_columns:
            raise Exception('Wrong number of fields')

    @property
    def add_button(self) -> QAbstractButton:
        return self.config.get('addButton')

    @property
    def fields(self):
        return self.config['fields']

    @property
    def form(self):
        return self.config['form']

    @property
    def table(self):
        return self.config['tableWidget']

    @property
    def headers(self):
        return self.config['cols']

    def disconnect_all_signals(self):
        for field in self.fields:
            try:
                # We disconnect everything
                field.disconnect()
            except TypeError:
                pass

    def selection_changed_table(self):
        """When a row is selected, we activate or not the form."""
        selection = self.table.selectedIndexes()

        if len(selection) == 0:
            self.form.setEnabled(False)
            self.disable_form()
        else:
            self.form.setEnabled(True)
            self.enable_form()

    def disable_form(self):
        for field in self.fields:
            if isinstance(field, QCheckBox):
                pass
            elif isinstance(field, QgsFieldComboBox):
                field.setCurrentIndex(0)
            elif isinstance(field, QgsMapLayerComboBox):
                field.setCurrentIndex(0)
            elif isinstance(field, QComboBox):
                field.setCurrentIndex(0)
            else:
                LOGGER.critical('Field is not supported: "{}"'.format(type(field).__name__))

    def enable_form(self):
        """We should connect all signals."""
        row = self.table.selectedIndexes()[0].row()
        item = self.table.item(row, 0)
        is_new_row = item.data(NEW_ITEM_ROLE)
        item.setData(NEW_ITEM_ROLE, False)

        if is_new_row:
            self.update_row_from_form()
        else:
            self.update_form_from_row()

        for i, field in enumerate(self.fields):
            if isinstance(field, QCheckBox):
                field.stateChanged.connect(self.update_row_from_form)
            elif isinstance(field, QgsFieldComboBox):
                field.currentIndexChanged.connect(self.update_row_from_form)
                self.fields_child_layer.append(field)
            elif isinstance(field, QgsMapLayerComboBox):
                field.currentIndexChanged.connect(self.update_row_from_form)
                self.fields[0].currentIndexChanged.connect(self.update_fields_in_combo)
            elif isinstance(field, QComboBox):
                field.currentIndexChanged.connect(self.update_row_from_form)
            else:
                LOGGER.critical('Field is not supported: "{}"'.format(type(field).__name__))
        self.update_fields_in_combo()

    def update_fields_in_combo(self):
        layer = self.fields[0].currentLayer()
        if not layer:
            return
        for field in self.fields_child_layer:
            field.setLayer(layer)

    def update_row_from_form(self):
        """For new row, we setup the row from default values in the form."""
        selection = self.table.selectedIndexes()
        if not selection:
            return
        row = selection[0].row()

        for i, field in enumerate(self.fields):
            item = self.table.item(row, i)
            if isinstance(field, QCheckBox):
                if field.isChecked():
                    item.setText('✓')
                    item.setData(Qt.UserRole, True)
                else:
                    item.setText('')
                    item.setData(Qt.UserRole, False)
            elif isinstance(field, QgsMapLayerComboBox):
                layer = field.currentLayer()
                if layer:
                    item.setText(layer.name())
                    item.setData(Qt.UserRole, layer.id())
                    item.setIcon(QgsMapLayerModel.iconForLayer(layer))
            elif isinstance(field, QgsFieldComboBox):
                data = field.currentField()
                item.setData(Qt.UserRole, data)
                item.setText(data)
                if self.fields[0].currentLayer():
                    # Empty combobox at the beginning of the project
                    index = self.fields[0].currentLayer().fields().indexFromName(data)
                    if index > 0:
                        item.setIcon(self.fields[0].currentLayer().fields().iconForField(index))
                    else:
                        item.setIcon(QIcon())
                else:
                    item.setIcon(QIcon())
            elif isinstance(field, QComboBox):
                data = field.currentText()
                item.setText(data)
                item.setData(Qt.UserRole, data)
            else:
                LOGGER.critical('Field is not supported: "{}"'.format(type(field).__name__))

    def update_form_from_row(self):
        """When we enable the form from an existing row."""
        row = self.table.selectedIndexes()[0].row()

        for i, field in enumerate(self.fields):
            data = self.table.item(row, i).data(Qt.UserRole)
            if isinstance(field, QCheckBox):
                field.setChecked(data)
            elif isinstance(field, QgsMapLayerComboBox):
                layer = QgsProject.instance().mapLayer(data)
                field.setLayer(layer)
            elif isinstance(field, QgsFieldComboBox):
                field.setLayer(self.fields[0].currentLayer())
                field.setField(data)
            elif isinstance(field, QComboBox):
                field.setCurrentText(data)
            else:
                LOGGER.critical('Field is not supported: "{}"'.format(type(field).__name__))

    def set_connections(self):
        self.add_button.clicked.connect(self.add_new_layer_to_table)
        self.add_button.setToolTip(tr('Add a new layer to the list'))
        self.table.itemSelectionChanged.connect(self.selection_changed_table)
        self.selection_changed_table()

    def add_new_layer_to_table(self):
        """Add a new row to the table."""
        row = self.table.rowCount()
        self.table.setRowCount(row + 1)
        for i, field in enumerate(self.fields):
            item = QTableWidgetItem()
            if i == 0:
                item.setData(NEW_ITEM_ROLE, True)
            self.table.setItem(row, i, item)
        self.table.selectRow(row)
        LOGGER.info('Adding one row in table "{}"'.format(self.name))

    def remove_selection(self):
        selection = self.table.selectedIndexes()
        if len(selection):
            row = selection[0].row()
            self.table.clearSelection()
            self.table.removeRow(row)
            LOGGER.info('Removing one row in table "{}"'.format(self.name))

    def to_dict(self):
        data = list()
        rows = self.table.rowCount()
        for row in range(rows):
            row_data = dict()
            for j, name in enumerate(self.headers):
                item = self.table.item(row, j)
                if not item:
                    continue
                cell = item.data(Qt.UserRole)
                if cell is None:
                    row_data[name] = cell
                else:
                    row_data[name] = cell
            data.append(row_data)
        return data

    def from_json(self):
        pass
