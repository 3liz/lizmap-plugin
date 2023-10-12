"""Table manager."""
import enum
import inspect
import json
import logging
import os

from collections import namedtuple
from typing import Optional, Union

from qgis.core import QgsMapLayerModel, QgsMasterLayoutInterface, QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QMessageBox,
    QTableWidgetItem,
)

from lizmap import DEFAULT_LWC_VERSION
from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.definitions.dataviz import AggregationType, GraphType
from lizmap.definitions.definitions import LwcVersions
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import plugin_name
from lizmap.qt_style_sheets import NEW_FEATURE_CSS
from lizmap.tools import to_bool

LOGGER = logging.getLogger(plugin_name())


__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TableManager:

    """ Class to manage a table with add, edit, remove, reorder rows. """

    def __init__(
            self, parent, definitions: BaseDefinitions, edition: Optional[QDialog], table, remove_button, edit_button,
            up_button, down_button):
        """ Constructor. """
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
        self.lwc_versions.append(LwcVersions.Lizmap_3_5)
        self.lwc_versions.append(LwcVersions.Lizmap_3_6)
        self.lwc_versions.append(LwcVersions.Lizmap_3_7)

        self.keys = [i for i, j in self.definitions.layer_config.items() if j.get('plural') is None]
        self.table.setColumnCount(len(self.keys))

        for i, key in enumerate(self.keys):
            item = self.definitions.layer_config[key]
            column = QTableWidgetItem(item['header'])
            tooltip = item.get('tooltip')
            if tooltip:
                column.setToolTip(tooltip)
            self.table.setHorizontalHeaderItem(i, column)
            if not item.get('visible', True):
                self.table.setColumnHidden(i, True)

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
            self.definitions.add_general_widget('datavizTemplate', self.parent.dataviz_html_template)
            self.definitions.add_general_widget('theme', self.parent.combo_theme)

            self.definitions.add_general_label('datavizLocation', self.parent.label_dataviz_location)
            self.definitions.add_general_label('datavizTemplate', self.parent.label_dataviz_template)
            self.definitions.add_general_label('theme', self.parent.label_dataviz_theme)

        elif self.definitions.key() == 'filter_by_polygon' and self.parent:
            self.definitions.add_general_widget('polygon_layer_id', self.parent.layer_filter_polygon)
            self.definitions.add_general_widget('group_field', self.parent.field_filter_polygon)
            self.definitions.add_general_widget('filter_by_user', self.parent.filter_polygon_by_user)

            self.definitions.add_general_label('polygon_layer_id', self.parent.label_layer_filter_polygon)
            self.definitions.add_general_label('group_field', self.parent.label_field_filter_polygon)
            self.definitions.add_general_label('filter_by_user', self.parent.label_filter_polygon_by_user)

        elif self.definitions.key() == 'layouts' and self.parent:
            self.definitions.add_general_widget('default_popup_print', self.parent.checkbox_default_print)

        # Set tooltips and combobox items if needed
        for general_config in self.definitions.general_config.values():
            general_config: dict
            widget = general_config.get('widget')
            if widget is None:
                continue

            tooltip = general_config.get('tooltip')
            if tooltip:
                widget.setToolTip(tooltip)
                label = general_config.get('label')
                if label:
                    label.setToolTip(tooltip)

            if general_config['type'] == InputType.CheckBoxAsDropdown:
                # Duplicated code from base_edition_dialog.py
                items = general_config.get('items')
                for item in items:
                    icon = item.value.get('icon')
                    if icon:
                        widget.addItem(QIcon(icon), item.value['label'], item.value['data'])
                    else:
                        widget.addItem(item.value['label'], item.value['data'])
                    index = widget.findData(item.value['data'])
                    tooltip = item.value.get('tooltip')
                    if tooltip:
                        widget.setItemData(index, tooltip, Qt.ToolTipRole)
                default = general_config.get('default')
                default: enum
                if default:
                    index = widget.findData(default.value['data'])
                    widget.setCurrentIndex(index)
                # End of duplicated code from base_edition_dialog.py

        # Set versions
        if self.parent:
            self.set_lwc_version(self.parent.current_lwc_version())

        # noinspection PyArgumentList
        self.project = QgsProject.instance()

    def set_lwc_version(self, current_version: LwcVersions):
        """ When the target LWC version is changed, we need to update all widgets to set the color. """
        # LOGGER.debug("Set new LWC version {} in {}".format(current_version.value, self.definitions.key()))
        found = False
        for lwc_version in self.lwc_versions:
            if found:
                for general_config in self.definitions.general_config.values():
                    version = general_config.get('version')
                    if version == lwc_version:
                        label = general_config.get('label')
                        if label:
                            label.setStyleSheet(NEW_FEATURE_CSS)
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
        """ Fetch the list of values part of the primary key for each row. """
        unicity_dict = dict()
        rows = self.table.rowCount()

        for key in self.definitions.primary_keys():
            unicity_dict[key] = list()

            for i, config_key in enumerate(self.keys):
                if config_key == key:
                    for row in range(rows):
                        item = self.table.item(row, i)
                        item: QTableWidgetItem
                        if item is None:
                            # Do not put if not item, it might be False
                            raise Exception('Cell is not initialized ({}, {})'.format(row, i))

                        if item.isSelected():
                            # We do not want to add selected values in the list.
                            # When saving the form, we will check if the current input is already in this list.
                            continue

                        cell = item.data(Qt.UserRole)
                        if cell is None:
                            # Do not put if not cell, it might be False
                            raise Exception('Cell has no data ({}, {})'.format(row, i))

                        unicity_dict[key].append(cell)

        return unicity_dict

    def add_new_row(self):
        """ When clicking on the "add" button, to add new row in the table. """
        # We give the main UI of the plugin in the edition dialog
        dialog = self.edition(self.parent, self._primary_keys())
        result = dialog.exec_()
        if result == QDialog.Accepted:
            data = dialog.save_form()
            row = self.table.rowCount()
            self.table.setRowCount(row + 1)
            self._edit_row(row, data)

    def edit_existing_row(self):
        """ When editing an existing row in the table. """
        selection = self.table.selectedIndexes()

        if len(selection) <= 0:
            return

        row = selection[0].row()

        data = dict()
        for i, key in enumerate(self.keys):
            cell = self.table.item(row, i)
            value = cell.data(Qt.UserRole)
            data[key] = value

        # We give the main UI of the plugin in the edition dialog
        dialog = self.edition(self.parent, self._primary_keys())
        dialog.load_form(data)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            data = dialog.save_form()
            self._edit_row(row, data)

        return result

    def _edit_row(self, row, data):
        """ Internal function to edit a row. """
        self._layer = None
        for i, key in enumerate(data.keys()):
            value = data[key]
            cell = QTableWidgetItem()

            input_type = self.definitions.layer_config[key]['type']

            if self._layer and hasattr(value, '__call__'):
                # Value is a for now a function, we need to evaluate it
                sig = inspect.signature(value)
                if 'plot_type' in [i for i in sig.parameters]:
                    # TODO fixme for dataviz
                    value = value(self._layer, data.get('type'))
                else:
                    value = value(self._layer)

            if input_type == InputType.Layer:
                layer = self.project.mapLayer(value)
                self._layer = layer
                cell.setText(layer.name())
                cell.setData(Qt.UserRole, layer.id())
                cell.setData(Qt.ToolTipRole, '{} ({})'.format(layer.name(), layer.crs().authid()))
                # noinspection PyArgumentList
                cell.setIcon(QgsMapLayerModel.iconForLayer(layer))

            elif input_type == InputType.Layers:
                names = []
                for layer in value:
                    if layer != '':
                        vector = self.project.mapLayer(layer)
                        if vector:
                            names.append(vector.name())
                display = ' ,'.join(names)
                cell.setText(display)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, display)

            elif input_type in (InputType.Field, InputType.PrimaryKeyField):
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

            elif input_type == InputType.File:
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

            elif input_type in (InputType.List, InputType.CheckBoxAsDropdown):
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)
                items = self.definitions.layer_config[key].get('items')
                multiple_selection = self.definitions.layer_config[key].get('multiple_selection', False)
                if items:
                    if not multiple_selection:
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
                        labels = []
                        for item_enum in items:
                            if item_enum.value['data'] in value:
                                # TODO
                                # We should add the label and not the data, but there is a bug later when opening the
                                # form
                                labels.append(item_enum.value['data'])
                        value = ','.join(labels)
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
                separator = self.definitions.layer_config[key].get('separator', ',')
                if separator and isinstance(value, list):
                    value = separator.join(value)

                cell.setText(value)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)

                if self.definitions.key() == 'layouts' and key == 'layout':
                    manager = QgsProject.instance().layoutManager()
                    layout = manager.layoutByName(value)

                    atlas_layout = None
                    if layout.layoutType() == QgsMasterLayoutInterface.PrintLayout:
                        for _print_layout in manager.printLayouts():
                            if _print_layout.name() == value:
                                atlas_layout = _print_layout
                                break

                    if not atlas_layout:
                        # The report shouldn't be loaded
                        return

                    if atlas_layout.atlas().enabled():
                        icon = QIcon(":images/themes/default/mIconAtlas.svg")
                    else:
                        icon = QIcon(":images/themes/default/mActionFilePrint.svg")
                    cell.setIcon(icon)

            elif input_type == InputType.MultiLine:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)

            elif input_type == InputType.HtmlWysiwyg:
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

        if self.definitions.key() == 'dataviz':
            # We want to refresh the plot.
            # noinspection PyUnresolvedReferences
            self.preview_dataviz_dialog()

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
                if not cell:
                    continue

                value = cell.data(Qt.UserRole)
                if value == layer:
                    self.table.removeRow(i)
                    LOGGER.info("Removing '{}' from table {}".format(layer, self.definitions.key()))
                    continue

    def truncate(self):
        """Truncate the table."""
        self.table.setRowCount(0)

    def use_single_row(self):
        return self.definitions.use_single_row

    @staticmethod
    def label_dictionary_list() -> str:
        """ The label in the CFG file prefixing the list. """
        return "layers"

    def to_json(self, version=None) -> dict:
        """Write the configuration to JSON.

        Since Lizmap 3.4, the JSON is different.
        """
        if not version:
            if self.parent:
                version = self.parent.current_lwc_version()
            else:
                version = DEFAULT_LWC_VERSION

        data = dict()

        if self.definitions.key() in ('filter_by_polygon', 'layouts', ):
            data['config'] = dict()
            for config_key, general_config in self.definitions.general_config.items():
                widget = general_config.get('widget')
                if widget is None:
                    continue

                input_type = general_config['type']

                if input_type == InputType.Layer:
                    layer = widget.currentLayer()
                    # The combobox might be empty, the layer me be deleted in the meantime
                    data['config'][config_key] = layer.id() if layer else None
                elif input_type in (InputType.Field, InputType.PrimaryKeyField):
                    data['config'][config_key] = widget.currentField()
                elif input_type == InputType.CheckBox:
                    data['config'][config_key] = widget.isChecked()
                elif input_type == InputType.CheckBoxAsDropdown:
                    data['config'][config_key] = widget.currentData()
                else:
                    raise Exception('InputType global "{}" not implemented'.format(input_type))

        data[self.label_dictionary_list()] = list()

        rows = self.table.rowCount()

        export_legacy_single_row = self.definitions.use_single_row and rows == 1

        for row in range(rows):
            layer_data = dict()
            for i, key in enumerate(self.keys):
                input_type = self.definitions.layer_config[key]['type']
                use_bool_type = self.definitions.layer_config[key].get('use_json', False)
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
                elif input_type in (InputType.Field, InputType.PrimaryKeyField):
                    layer_data[key] = cell
                elif input_type == InputType.Fields:
                    layer_data[key] = cell
                elif input_type == InputType.File:
                    layer_data[key] = cell
                elif input_type == InputType.Json:
                    layer_data[key] = cell
                elif input_type in (InputType.CheckBox, InputType.CheckBoxAsDropdown):
                    if use_bool_type:
                        layer_data[key] = cell
                    else:
                        # Lizmap 4 #176
                        layer_data[key] = str(True) if cell else str(False)
                elif input_type == InputType.SpinBox:
                    layer_data[key] = cell
                elif input_type == InputType.List:
                    layer_data[key] = cell
                elif input_type == InputType.Text:
                    json_array = self.definitions.layer_config[key].get('use_json')
                    separator = self.definitions.layer_config[key].get('separator', ',')
                    if json_array and separator and cell:
                        layer_data[key] = cell.split(separator)
                    else:
                        layer_data[key] = cell
                elif input_type == InputType.MultiLine:
                    layer_data[key] = cell
                elif input_type == InputType.HtmlWysiwyg:
                    layer_data[key] = cell
                else:
                    raise Exception('InputType "{}" not implemented'.format(input_type))

                if layer_data[key] == '':
                    layer_data.pop(key)

            for key in self.keys:
                # Re-iterate after we got the layer ID in the form

                default_value = self.definitions.layer_config[key].get('default')
                is_read_only = self.definitions.layer_config[key].get('read_only', False)

                # By default, some functions might be called everytime : feature count, min/max values of a field
                update = self.definitions.layer_config[key].get('update_on_saving', True)
                if key not in layer_data or layer_data[key] is None or layer_data[key] == '':
                    if not update:
                        # Only the first time if the value wasn't set, we compute the value anyway
                        update = True

                if default_value is not None and hasattr(default_value, '__call__') and is_read_only and update:
                    # Value is a for now a function, we need to evaluate it
                    vector_layer = self.project.mapLayer(layer_data['layerId'])
                    # TODO to make it future-proof by inspecting parameters etc
                    # We assume for now we use the QgsVectorLayer for the input and optional dataviz type
                    sig = inspect.signature(default_value)
                    if 'plot_type' in [i for i in sig.parameters]:
                        # hack, only for dataviz UUID
                        layer_data[key] = default_value(vector_layer, layer_data['type'])
                    else:
                        layer_data[key] = default_value(vector_layer)

                    if isinstance(layer_data[key], bool):
                        if not self.definitions.layer_config[key].get('use_json', False):
                            # Ticket #176 about true boolean
                            layer_data[key] = str(True) if layer_data[key] else str(False)

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
                vector_layer = self.project.mapLayer(layer_data['layerId'])
                layer_data['geometryType'] = geometry_type[vector_layer.geometryType()]

            if self.definitions.key() == 'datavizLayers':
                if version <= LwcVersions.Lizmap_3_3:
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

            if self.definitions.key() == 'formFilterLayers':
                if version < LwcVersions.Lizmap_3_7:
                    # We need to change keys to write in the legacy format
                    if layer_data.get('type') == 'numeric':
                        if layer_data.get('end_field'):
                            # Incompatible with this format, but we don't remove it just in case
                            LOGGER.error(
                                "A end_field is defined for the form filter. This is not compatible for this version "
                                "of Lizmap Web Client"
                            )
                        if layer_data.get('start_field'):
                            layer_data['field'] = layer_data.get('start_field')
                            del layer_data['start_field']
                    elif layer_data.get('type') == 'date':
                        if layer_data.get('start_field'):
                            layer_data['min_date'] = layer_data.get('start_field')
                            del layer_data['start_field']
                        if layer_data.get('end_field'):
                            layer_data['max_date'] = layer_data.get('end_field')
                            del layer_data['end_field']

            if export_legacy_single_row:
                if self.definitions.key() == 'atlas':
                    layer_data['atlasEnabled'] = str(True)
                    layer_data['atlasMaxWidth'] = 25
                return layer_data

            data[self.label_dictionary_list()].append(layer_data)

        # Check for PG with centroid options
        # Maybe move this code later if we have more checks to do when saving CFG
        if self.definitions.key() == 'filter_by_polygon':
            for layer_data in data['layers']:
                if layer_data['use_centroid']:
                    vector_layer = self.project.mapLayer(layer_data['layer'])
                    if vector_layer.providerType() == 'postgres':
                        # noinspection PyUnresolvedReferences
                        has_index, message = self.definitions.has_spatial_centroid_index(vector_layer)
                        if not has_index:
                            # noinspection PyUnresolvedReferences,PyArgumentList
                            QMessageBox.critical(self.parent, tr('Filter by polygon'), message, QMessageBox.Ok)

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
                vector_layer = self.project.mapLayer(layer_id)
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
    def _from_json_legacy_form_filter(data):
        """ Read form filter and transform it if needed. """
        for layer in data.get('layers'):
            if layer.get('type') == 'numeric':

                if layer.get('field'):
                    # We upgrade from < 3.7 to 3.7 format
                    layer['start_field'] = layer['field']
                    del layer['field']

            if layer.get('type') == 'date':
                if layer.get('min_date'):
                    # We upgrade from < 3.7 to 3.7 format
                    layer['start_field'] = layer['min_date']
                    del layer['min_date']

                if layer.get('end_date'):
                    # We upgrade from < 3.7 to 3.7 format
                    layer['end_field'] = layer['end_date']
                    del layer['end_date']

        return data

    @staticmethod
    def _from_json_legacy_dataviz(data):
        """Read legacy dataviz without the trace config."""

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

    def from_json(self, data: dict):
        """Load JSON into the table.

        :param data: The data for the given table to read from the CFG file : layers and general configuration
        """
        if self.definitions.key() in (
            'locateByLayer',
            'loginFilteredLayers',
            'tooltipLayers',
            'attributeLayers',
            'editionLayers',
            'timemanagerLayers',
            'formFilterLayers',
            'datavizLayers',
        ):
            data = self._from_json_legacy_order(data)

        if self.definitions.key() == 'editionLayers':
            data = self._from_json_legacy_capabilities(data)

        if self.definitions.key() == 'datavizLayers':
            data = self._from_json_legacy_dataviz(data)

        if self.definitions.key() == 'formFilterLayers':
            data = self._from_json_legacy_form_filter(data)

        config = data.get('config')
        config: Union[dict, None]
        if config:
            settings = []
            widget_type = None
            Setting = namedtuple('Setting', ['widget', 'type', 'value'])
            for config_key, value in config.items():
                if config_key not in self.definitions.general_config:
                    continue

                widget = self.definitions.general_config[config_key].get('widget')
                if widget is None:
                    # In tests, we don't have this dialog with general config
                    continue

                widget_type = self.definitions.general_config[config_key]['type']
                if widget_type == InputType.Layer:
                    vector_layer = self.project.mapLayer(value)
                    if not vector_layer or not vector_layer.isValid():
                        LOGGER.warning(
                            'In CFG file, section "{}" with key {}, the layer with ID "{}" is invalid or does not '
                            'exist. Skipping that layer.'.format(
                                self.definitions.key(), config_key, value))
                    else:
                        settings.insert(0, Setting(widget, widget_type, vector_layer))
                elif widget_type in (InputType.Field, InputType.PrimaryKeyField):
                    settings.append(Setting(widget, widget_type, value))
                elif widget_type in (InputType.CheckBox, InputType.CheckBoxAsDropdown):
                    settings.append(Setting(widget, widget_type, value))
                else:
                    raise Exception('InputType global "{}" not implemented'.format(widget_type))

            # Now in correct order, because the field depends on the layer
            for setting in settings:
                if setting.type == InputType.Layer:
                    setting.widget.setLayer(setting.value)
                elif setting.type in (InputType.Field, InputType.PrimaryKeyField):
                    setting.widget.setField(setting.value)
                elif setting.type == InputType.CheckBox:
                    setting.widget.setChecked(setting.value)
                elif setting.type == InputType.CheckBoxAsDropdown:
                    index = setting.widget.findData(setting.value)
                    setting.widget.setCurrentIndex(index)
                else:
                    raise Exception('InputType global "{}" not implemented'.format(widget_type))

        layers = data.get(self.label_dictionary_list())

        if not layers:
            layers = self._from_json_legacy(data)

        for layer in layers:
            if not layer:
                continue
            layer_data = {}

            # Fixme, better to mave these two lines in a dedicated function to retrieve QgsVectorLayer from a dict
            vector_layer = None
            valid_layer = True

            for key, definition in self.definitions.layer_config.items():
                if definition.get('plural'):
                    continue

                value = layer.get(key)
                if value:
                    if definition['type'] == InputType.Layer:
                        vector_layer = self.project.mapLayer(value)
                        if not vector_layer or not vector_layer.isValid():
                            LOGGER.warning(
                                'In CFG file, section "{}", the layer with ID "{}" is invalid or does not exist.'
                                ' Skipping that layer.'.format(
                                    self.definitions.key(), value))
                            valid_layer = False
                        layer_data[key] = value
                    elif definition['type'] == InputType.Layers:
                        layer_data[key] = value
                    elif definition['type'] in (InputType.Field, InputType.PrimaryKeyField):
                        layer_data[key] = value
                    elif definition['type'] == InputType.Fields:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Color:
                        layer_data[key] = value
                    elif definition['type'] in (InputType.CheckBox, InputType.CheckBoxAsDropdown):
                        layer_data[key] = to_bool(value, False)
                    elif definition['type'] == InputType.File:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Json:
                        layer_data[key] = value
                    elif definition['type'] == InputType.List:
                        items = definition.get('items')
                        multiple_selection = definition.get('multiple_selection', False)
                        if multiple_selection:
                            layer_data[key] = ''
                            for single_value in value:
                                for item_enum in items:
                                    if item_enum.value['data'] == single_value:
                                        layer_data[key] += single_value
                        else:
                            # Single value
                            if items:
                                for item_enum in items:
                                    if item_enum.value['data'] == value:
                                        break
                                else:
                                    default_list_value = definition.get('default').value['data']
                                    msg = (
                                        'Error with value = "{}" in list "{}", set default to {}'.format(
                                            value, key, default_list_value)
                                    )
                                    LOGGER.warning(msg)
                                    value = default_list_value
                            layer_data[key] = value
                    elif definition['type'] == InputType.SpinBox:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Text:
                        layer_data[key] = value
                    elif definition['type'] == InputType.MultiLine:
                        layer_data[key] = value
                    elif definition['type'] == InputType.HtmlWysiwyg:
                        layer_data[key] = value
                    elif definition['type'] == InputType.Collection:
                        layer_data[key] = value
                    else:
                        raise Exception('InputType "{}" not implemented'.format(definition['type']))
                else:
                    default_value = definition.get('default')
                    if default_value is not None and not hasattr(default_value, '__call__'):
                        if self.definitions.key() == 'datavizLayers' and layer_data['type'] == 'box'\
                                and key == 'aggregation':
                            layer_data[key] = AggregationType.No.value['data']
                        elif definition['type'] == InputType.List and default_value != '':
                            layer_data[key] = default_value.value['data']
                        else:
                            layer_data[key] = default_value
                    elif default_value is not None and hasattr(default_value, '__call__'):
                        # The function will evaluate the value, with the layer context
                        layer_data[key] = default_value
                    else:
                        # raise InvalidCfgFile(')
                        LOGGER.warning(
                            'In CFG file, section "{}", one layer is missing the key "{}" which is mandatory. '
                            'Skipping that layer.'.format(
                                self.definitions.key(), key))
                        valid_layer = False
                        continue

            if not valid_layer:
                # We didn't find any valid layer during the process of reading this JSON dictionary
                row = self.table.rowCount()
                LOGGER.info(
                    "No valid layer found when reading this section {}. Not adding the row number {}".format(
                        row + 1,
                        self.definitions.key()
                    )
                )
                continue

            # For editing, keep only postgresql, follow up about #364, #361
            if self.definitions.key() == 'editionLayers' and not to_bool(os.getenv("CI"), default_value=False):
                # In CI, we still want to test this layer, sorry.
                if vector_layer.dataProvider().name() != 'postgres':
                    LOGGER.warning(
                        "The layer for editing {} is not stored in PostgreSQL. Now, only PostgreSQL layers "
                        "are supported for editing capabilities. Removing this layer from the "
                        "configuration.".format(vector_layer.id()))
                    valid_layer = False

            if valid_layer:
                row = self.table.rowCount()
                self.table.setRowCount(row + 1)
                self._edit_row(row, layer_data)
