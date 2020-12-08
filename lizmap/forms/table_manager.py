"""Table manager."""

import json
import logging

from typing import Type

from qgis.core import QgsMapLayerModel, QgsProject, QgsSettings
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import QAbstractItemView, QDialog, QTableWidgetItem

from lizmap import DEFAULT_LWC_VERSION
from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.definitions.dataviz import AggregationType, GraphType
from lizmap.definitions.definitions import LwcVersions
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import plugin_name
from lizmap.qt_style_sheets import NEW_FEATURE

LOGGER = logging.getLogger(plugin_name())


__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TableManager:

    def __init__(self, parent, definitions: BaseDefinitions, edition: Type[QDialog], table, remove_button, edit_button, up_button, down_button):
        self.parent = parent
        self.definitions = definitions
        self.edition = edition
        self.table = table
        self.remove_button = remove_button
        self.edit_button = edit_button
        self.up_button = up_button
        self.down_button = down_button

        self.lwc_versions = list()
        self.lwc_versions.append(LwcVersions.Lizmap_3_1)
        self.lwc_versions.append(LwcVersions.Lizmap_3_2)
        self.lwc_versions.append(LwcVersions.Lizmap_3_3)
        self.lwc_versions.append(LwcVersions.Lizmap_3_4)

        self.keys = [i for i, j in self.definitions.layer_config.items() if j.get('plural') is None]
        self.table.setColumnCount(len(self.keys))

        for i, key in enumerate(self.keys):
            item = self.definitions.layer_config[key]
            column = QTableWidgetItem(item['header'])
            tooltip = item.get('tooltip')
            if tooltip:
                column.setToolTip(tooltip)
            self.table.setHorizontalHeaderItem(i, column)

        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.edit_existing_row)

        # This is a hack to get the layer and then field icons.
        self._layer = None

        # header = self.table.horizontalHeader()
        # header.setSectionResizeMode(QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(0, QHeaderView.Stretch)

        if self.definitions.key() == 'datavizLayers' and self.parent:
            self.definitions.add_general_widget('datavizLocation', self.parent.liDatavizContainer)
            self.definitions.add_general_widget('datavizTemplate', self.parent.inDatavizTemplate)
            self.definitions.add_general_widget('theme', self.parent.combo_theme)

            self.definitions.add_general_label('datavizLocation', self.parent.label_dataviz_location)
            self.definitions.add_general_label('datavizTemplate', self.parent.label_dataviz_template)
            self.definitions.add_general_label('theme', self.parent.label_dataviz_theme)

        # Set tooltips
        for general_config in self.definitions.general_config.values():
            widget = general_config.get('widget')
            if not widget:
                continue
            tooltip = general_config.get('tooltip')
            if tooltip:
                widget.setToolTip(tooltip)
                label = general_config.get('label')
                if label:
                    label.setToolTip(tooltip)

        # Set versions
        current_version = QgsSettings().value('lizmap/lizmap_web_client_version', DEFAULT_LWC_VERSION.value, str)
        current_version = LwcVersions(current_version)
        self.set_lwc_version(current_version)

    def set_lwc_version(self, current_version):
        found = False
        for lwc_version in self.lwc_versions:
            if found:
                for general_config in self.definitions.general_config.values():
                    version = general_config.get('version')
                    if version == lwc_version:
                        label = general_config.get('label')
                        if label:
                            label.setStyleSheet(NEW_FEATURE)
            else:
                for general_config in self.definitions.general_config.values():
                    version = general_config.get('version')
                    if version == lwc_version:
                        label = general_config.get('label')
                        if label:
                            label.setStyleSheet('')

            if lwc_version == current_version:
                found = True

    def _primary_keys(self) -> dict:
        unicity_dict = dict()
        rows = self.table.rowCount()

        for key in self.definitions.primary_keys():
            unicity_dict[key] = list()

            for i, config_key in enumerate(self.keys):
                if config_key == key:
                    for row in range(rows):
                        item = self.table.item(row, i)
                        if item is None:
                            # Do not put if not item, it might be False
                            raise Exception('Cell is not initialized ({}, {})'.format(row, i))

                        cell = item.data(Qt.UserRole)
                        if cell is None:
                            # Do not put if not cell, it might be False
                            raise Exception('Cell has no data ({}, {})'.format(row, i))

                        unicity_dict[key].append(cell)

        return unicity_dict

    def add_new_row(self):
        # noinspection PyCallingNonCallable
        row = self.table.rowCount()

        dialog = self.edition(self.parent, self._primary_keys())
        result = dialog.exec_()
        if result == QDialog.Accepted:
            data = dialog.save_form()
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self._edit_row(row, data)

    def edit_existing_row(self):
        selection = self.table.selectedIndexes()

        if len(selection) <= 0:
            return

        row = selection[0].row()

        data = dict()
        for i, key in enumerate(self.keys):
            cell = self.table.item(row, i)
            value = cell.data(Qt.UserRole)
            data[key] = value

        dialog = self.edition()
        dialog.load_form(data)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            data = dialog.save_form()
            self._edit_row(row, data)

        return result

    def _edit_row(self, row, data):
        """Internal function to edit a row."""
        self._layer = None
        for i, key in enumerate(data.keys()):
            value = data[key]
            cell = QTableWidgetItem()

            input_type = self.definitions.layer_config[key]['type']

            if self._layer and hasattr(value, '__call__'):
                # Value is a for now a function, we need to evaluate it
                value = value(self._layer)

            if input_type == InputType.Layer:
                layer = QgsProject.instance().mapLayer(value)
                self._layer = layer
                cell.setText(layer.name())
                cell.setData(Qt.UserRole, layer.id())
                cell.setData(Qt.ToolTipRole, '{} ({})'.format(layer.name(), layer.crs().authid()))
                cell.setIcon(QgsMapLayerModel.iconForLayer(layer))

            elif input_type == InputType.Layers:
                names = []
                for layer in value:
                    if layer != '':
                        vector = QgsProject.instance().mapLayer(layer)
                        if vector:
                            names.append(vector.name())
                display = ' ,'.join(names)
                cell.setText(display)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, display)

            elif input_type == InputType.Field:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)

                # Get the icon for the field
                if self._layer:
                    index = self._layer.fields().indexFromName(value)
                    if index >= 0:
                        cell.setIcon(self._layer.fields().iconForField(index))

            elif input_type == InputType.Fields:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)

            elif input_type == InputType.Color:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)
                if value:
                    cell.setData(Qt.DecorationRole, QColor(value))

            elif input_type == InputType.CheckBox:
                if value:
                    cell.setText('✓')
                    cell.setData(Qt.UserRole, True)
                    cell.setData(Qt.ToolTipRole, tr('True'))
                else:
                    cell.setText('')
                    cell.setData(Qt.UserRole, False)
                    cell.setData(Qt.ToolTipRole, tr('False'))
                cell.setTextAlignment(Qt.AlignCenter)

            elif input_type == InputType.Json:
                if value:
                    cell.setText(json.dumps(value))
                    cell.setData(Qt.UserRole, value)
                    cell.setData(Qt.ToolTipRole, value)
                else:
                    cell.setText('')
                    cell.setData(Qt.UserRole, '')
                    cell.setData(Qt.ToolTipRole, '')

            elif input_type == InputType.List:
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)
                items = self.definitions.layer_config[key].get('items')
                if items:
                    for item_enum in items:
                        if item_enum.value['data'] == value:
                            text = item_enum.value['label']
                            icon = item_enum.value.get('icon')
                            break
                    else:
                        msg = 'Error with value = "{}" in list "{}"'.format(value, key)
                        LOGGER.critical(msg)
                        raise Exception(msg)
                    cell.setText(text)
                    if icon:
                        cell.setIcon(QIcon(icon))
                else:
                    cell.setText(value)

            elif input_type == InputType.SpinBox:
                unit = self.definitions.layer_config[key].get('unit')
                if unit:
                    display = '{}{}'.format(value, unit)
                else:
                    display = '{}'.format(value)
                cell.setText(display)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)

            elif input_type == InputType.Text:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)

            elif input_type == InputType.MultiLine:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)

            elif input_type == InputType.Collection:
                json_dump = json.dumps(value)
                cell.setText(json_dump)
                cell.setData(Qt.UserRole, value)
                function = self.definitions.layer_config[key]['represent_value']
                cell.setData(Qt.ToolTipRole, function(value))

            else:
                raise Exception('InputType "{}" not implemented'.format(input_type))

            self.table.setItem(row, i, cell)
        self._layer = None
        self.table.clearSelection()

    def move_layer_up(self):
        """Move the selected layer up."""
        row = self.table.currentRow()
        if row <= 0:
            return
        column = self.table.currentColumn()
        self.table.insertRow(row - 1)
        for i in range(self.table.columnCount()):
            self.table.setItem(row - 1, i, self.table.takeItem(row + 1, i))
            self.table.setCurrentCell(row - 1, column)
        self.table.removeRow(row + 1)

    def move_layer_down(self):
        """Move the selected layer down."""
        row = self.table.currentRow()
        if row == self.table.rowCount() - 1 or row < 0:
            return
        column = self.table.currentColumn()
        self.table.insertRow(row + 2)
        for i in range(self.table.columnCount()):
            self.table.setItem(row + 2, i, self.table.takeItem(row, i))
            self.table.setCurrentCell(row + 2, column)
        self.table.removeRow(row)

    def remove_selection(self):
        """Remove the selected row from the table."""
        selection = self.table.selectedIndexes()
        if len(selection) <= 0:
            return

        row = selection[0].row()
        self.table.clearSelection()
        self.table.removeRow(row)

    def layers_has_been_deleted(self, layer_ids):
        """When some layers have been deleted from QGIS."""
        for layer in layer_ids:
            row = self.table.rowCount()
            for i in range(row):
                cell = self.table.item(i, 0)
                value = cell.data(Qt.UserRole)
                if value == layer:
                    self.table.removeRow(i)

    def truncate(self):
        """Truncate the table."""
        self.table.setRowCount(0)

    def use_single_row(self):
        return self.definitions.use_single_row

    def to_json(self, version=None) -> dict:
        """Write the configuration to JSON.

        Since Lizmap 3.4, the JSON is different.
        """
        if not version:
            version = QgsSettings().value('lizmap/lizmap_web_client_version', DEFAULT_LWC_VERSION.value, str)
            version = LwcVersions(version)

        data = dict()

        # TODO Lizmap 4
        # data['config'] = dict()

        data['layers'] = list()

        rows = self.table.rowCount()

        export_legacy_single_row = self.definitions.use_single_row and rows == 1

        for row in range(rows):
            layer_data = dict()
            for i, key in enumerate(self.keys):
                input_type = self.definitions.layer_config[key]['type']
                item = self.table.item(row, i)

                if export_legacy_single_row:
                    key = '{}{}{}'.format(self.definitions.key(), key[0].capitalize(), key[1:])

                if item is None:
                    # Do not put if not item, it might be False
                    raise Exception('Cell is not initialized ({}, {})'.format(row, i))

                cell = item.data(Qt.UserRole)
                if cell is None:
                    # Do not put if not cell, it might be False
                    raise Exception('Cell has no data ({}, {})'.format(row, i))

                if input_type == InputType.Layer:
                    layer_data[key] = cell
                elif input_type == InputType.Collection:
                    layer_data[key] = cell
                elif input_type == InputType.Layers:
                    layer_data[key] = cell
                elif input_type == InputType.Color:
                    layer_data[key] = cell
                elif input_type == InputType.Field:
                    layer_data[key] = cell
                elif input_type == InputType.Fields:
                    layer_data[key] = cell
                elif input_type == InputType.Json:
                    layer_data[key] = cell
                elif input_type == InputType.CheckBox:
                    # Lizmap 4 #176
                    layer_data[key] = 'True' if cell else 'False'
                elif input_type == InputType.SpinBox:
                    layer_data[key] = cell
                elif input_type == InputType.List:
                    layer_data[key] = cell
                elif input_type == InputType.Text:
                    layer_data[key] = cell
                elif input_type == InputType.MultiLine:
                    layer_data[key] = cell
                else:
                    raise Exception('InputType "{}" not implemented'.format(input_type))

                if layer_data[key] == '':
                    layer_data.pop(key)

            if self.definitions.key() == 'datavizLayers':
                if layer_data['type'] == GraphType.Box.value['data']:
                    if layer_data['aggregation'] == AggregationType.No.value['data']:
                        layer_data['aggregation'] = ''

            if self.definitions.key() == 'editionLayers':
                capabilities_keys = [
                    'createFeature',
                    'allow_without_geom',
                    'modifyAttribute',
                    'modifyGeometry',
                    'deleteFeature',
                ]
                layer_data['capabilities'] = {key: layer_data[key] for key in capabilities_keys}
                for key in capabilities_keys:
                    layer_data.pop(key)

                geometry_type = {
                    0: 'point',
                    1: 'line',
                    2: 'polygon',
                    3: 'unknown',
                    4: 'none'
                }
                vector_layer = QgsProject.instance().mapLayer(layer_data['layerId'])
                layer_data['geometryType'] = geometry_type[vector_layer.geometryType()]

            if self.definitions.key() == 'datavizLayers':
                if version != LwcVersions.Lizmap_3_4:
                    traces = layer_data.pop('traces')
                    for j, trace in enumerate(traces):
                        for key in trace:
                            definition = self.definitions.layer_config[key]
                            if j == 0:
                                json_key = definition['plural'].format('')
                                if json_key.endswith('_'):
                                    # If the plural is at the end
                                    json_key = json_key[:-1]
                            else:
                                json_key = definition['plural'].format(j + 1)

                            layer_data[json_key] = trace[key]

            if export_legacy_single_row:
                if self.definitions.key() == 'atlas':
                    layer_data['atlasEnabled'] = 'True'
                    layer_data['atlasMaxWidth'] = 25
                return layer_data

            data['layers'].append(layer_data)

        if self.definitions.key() in [
            'locateByLayer',
            'loginFilteredLayers',
            'tooltipLayers',
            'attributeLayers',
            'editionLayers',
            'timemanagerLayers',
            'formFilterLayers',
            'datavizLayers',
        ]:
            result = {}
            for i, layer in enumerate(data['layers']):
                layer_id = layer.get('layerId')
                vector_layer = QgsProject.instance().mapLayer(layer_id)
                layer_name = vector_layer.name()
                if self.definitions.key() in ['formFilterLayers', 'datavizLayers']:
                    key = str(i)
                else:
                    key = layer_name
                if result.get(layer_name):
                    LOGGER.warning(
                        'Skipping "{}" while saving "{}" JSON configuration. Duplicated entry.'.format(
                            layer_name, self.definitions.key()))
                result[key] = layer
                result[key]['order'] = i
                if self.definitions.key() == 'formFilterLayers':
                    result[key]['provider'] = vector_layer.providerType()

            return result

        return data

    def _from_json_legacy(self, data) -> list:
        """Reformat the JSON data from 3.3 to 3.4 format.

        Used for atlas when all keys are stored in the main config scope.
        """
        layer = {}
        for key in data:
            if not key.startswith(self.definitions.key()):
                continue
            key_def = key[len(self.definitions.key()):]
            key_def = key_def[0].lower() + key_def[1:]
            definition = self.definitions.layer_config.get(key_def)
            if definition:
                layer[key_def] = data[key]

        return [layer]

    @staticmethod
    def _from_json_legacy_order(data):
        """Used when there is a dictionary with the row number as a key.

        No keys will be removed.
        """
        new_data = dict()
        new_data['layers'] = []

        def layer_from_order(layers, row):
            for a_layer in layers.values():
                if a_layer['order'] == row:
                    return a_layer

        order = []
        for layer in data.values():
            order.append(layer.get('order'))

        order.sort()

        for i in order:
            new_data['layers'].append(layer_from_order(data, i))

        return new_data

    @staticmethod
    def _from_json_legacy_capabilities(data):
        """Function used for the edition capabilities.
        ACL are stored in a sub list."""
        for layer in data.get('layers'):
            capabilities = layer.get('capabilities')
            layer.update(capabilities)
            layer.pop('capabilities')
            layer.pop('geometryType')
        return data

    @staticmethod
    def _from_json_legacy_dataviz(data):
        """Read legacy dataviz without the traces config."""

        # Todo, we should read the definition file
        legacy = [
            {
                'y_field': 'y_field',
                'color': 'color',
                'colorfield': 'colorfield',
            }, {
                'y2_field': 'y_field',
                'color2': 'color',
                'colorfield2': 'colorfield',
            }
        ]

        for layer in data.get('layers'):

            if layer.get('traces'):
                # Already in the new format, we do nothing.
                continue

            # Remove unused parameter
            if layer.get('has_y2_field'):
                del layer['has_y2_field']

            layer['traces'] = []
            for trace in legacy:
                one_trace = dict()
                for key in trace.keys():
                    value = layer.get(key)

                    if value is not None:
                        one_trace[trace[key]] = layer.get(key)
                        del layer[key]

                if one_trace:
                    y_field = one_trace.get('y_field')
                    missing_field = y_field is None or y_field == ''
                    if not missing_field:
                        # We skip if Y field is missing
                        layer['traces'].append(one_trace)

        return data

    def from_json(self, data):
        """Load JSON into the table."""
        if self.definitions.key() in [
            'locateByLayer',
            'loginFilteredLayers',
            'tooltipLayers',
            'attributeLayers',
            'editionLayers',
            'timemanagerLayers',
            'formFilterLayers',
            'datavizLayers',
        ]:
            data = self._from_json_legacy_order(data)

        if self.definitions.key() == 'editionLayers':
            data = self._from_json_legacy_capabilities(data)

        if self.definitions.key() == 'datavizLayers':
            data = self._from_json_legacy_dataviz(data)

        layers = data.get('layers')

        if not layers:
            layers = self._from_json_legacy(data)

        for layer in layers:
            if not layer:
                continue
            layer_data = {}
            valid_layer = True
            for key, definition in self.definitions.layer_config.items():
                if definition.get('plural'):
                    continue

                value = layer.get(key)
                if value:
                    if definition['type'] == InputType.Layer:
                        vector_layer = QgsProject.instance().mapLayer(value)
                        if not vector_layer or not vector_layer.isValid():
                            LOGGER.warning(
                                'In CFG file, section "{}", the layer with ID "{}" is invalid or does not exist.'
                                ' Skipping that layer.'.format(
                                    self.definitions.key(), value))
                            valid_layer = False
                        layer_data[key] = value
                    elif definition['type'] == InputType.Layers:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Field:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Fields:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Color:
                        layer_data[key] = value
                    elif definition['type'] == InputType.CheckBox:
                        layer_data[key] = True if value in ['true', 'True'] else False
                    elif definition['type'] == InputType.Json:
                        layer_data[key] = value
                    elif definition['type'] == InputType.List:
                        items = definition.get('items')
                        if items:
                            for item_enum in items:
                                if item_enum.value['data'] == value:
                                    break
                            else:
                                default_list_value = definition.get('default').value['data']
                                msg = 'Error with value = "{}" in list "{}", set default to {}'.format(value, key, default_list_value)
                                LOGGER.warning(msg)
                                value = default_list_value
                        layer_data[key] = value
                    elif definition['type'] == InputType.SpinBox:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Text:
                        layer_data[key] = value
                    elif definition['type'] == InputType.MultiLine:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Collection:
                        layer_data[key] = value
                    else:
                        raise Exception('InputType "{}" not implemented'.format(definition['type']))
                else:
                    default_value = definition.get('default')
                    if default_value is not None and not hasattr(default_value, '__call__'):
                        if self.definitions.key() == 'datavizLayers' and layer_data['type'] == 'box' and key == 'aggregation':
                            layer_data[key] = AggregationType.No.value['data']
                        elif definition['type'] == InputType.List and default_value != '':
                            layer_data[key] = default_value.value['data']
                        else:
                            layer_data[key] = default_value
                    elif default_value is not None and hasattr(default_value, '__call__'):
                        # The function will evaluated layer, with the layer context
                        layer_data[key] = default_value
                    else:
                        # raise InvalidCfgFile(')
                        LOGGER.warning(
                            'In CFG file, section "{}", one layer is missing the key "{}" which is mandatory. Skipping that layer.'.format(
                                self.definitions.key(), key))
                        valid_layer = False
                        continue

            if valid_layer:
                row = self.table.rowCount()
                self.table.setRowCount(row + 1)
                self._edit_row(row, layer_data)
