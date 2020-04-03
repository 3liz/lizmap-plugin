"""Dialog for dataviz edition."""

from qgis.PyQt.QtWidgets import (
    QTableWidgetItem,
    QAbstractItemView,
    QDialog,
    QHeaderView,
)
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsProject,
    QgsApplication,
    QgsSettings)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QColor

from lizmap.qt_style_sheets import NEW_FEATURE
from lizmap import DEFAULT_LWC_VERSION
from lizmap.definitions.base import InputType
from lizmap.definitions.dataviz import DatavizDefinitions, GraphType
from lizmap.definitions.definitions import LwcVersions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.forms.trace_dataviz_edition import TraceDatavizEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


CLASS = load_ui('ui_form_dataviz.ui')


class DatavizEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.parent = parent
        self.config = DatavizDefinitions()
        self.config.add_layer_widget('title', self.title)
        self.config.add_layer_widget('type', self.type_graph)
        self.config.add_layer_widget('description', self.text_description)
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('x_field', self.x_field)
        self.config.add_layer_widget('aggregation', self.aggregation)
        self.config.add_layer_widget('traces', self.traces)
        self.config.add_layer_widget('html_template', self.html_template)
        self.config.add_layer_widget('horizontal', self.horizontal)
        self.config.add_layer_widget('stacked', self.stacked)
        self.config.add_layer_widget('popup_display_child_plot', self.popup_display_child_plot)
        self.config.add_layer_widget('only_show_child', self.only_show_child)
        self.config.add_layer_widget('display_legend', self.display_legend)
        self.config.add_layer_widget('display_when_layer_visible', self.display_when_layer_visible)

        self.config.add_layer_label('title', self.label_title)
        self.config.add_layer_label('type', self.label_type)
        self.config.add_layer_label('description', self.label_description)
        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('x_field', self.label_x_field)
        self.config.add_layer_label('aggregation', self.label_aggregation)
        self.config.add_layer_label('traces', self.label_traces)
        self.config.add_layer_label('html_template', self.label_html_template)

        # noinspection PyCallByClass,PyArgumentList
        self.add_trace.setText('')
        self.add_trace.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.add_trace.setToolTip(tr('Add a new trace to the chart.'))
        self.remove_trace.setText('')
        self.remove_trace.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
        self.remove_trace.setToolTip(tr('Remove the selected trace from the chart.'))

        # Set traces table
        items = self.config.layer_config['traces']['items']
        self.traces.setColumnCount(len(items))
        for i, item in enumerate(items):
            sub_definition = self.config.layer_config[item]
            column = QTableWidgetItem(sub_definition['header'])
            column.setToolTip(sub_definition['tooltip'])
            self.traces.setHorizontalHeaderItem(i, column)
        header = self.traces.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        self.traces.setSelectionMode(QAbstractItemView.SingleSelection)
        self.traces.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.traces.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.traces.setAlternatingRowColors(True)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer.layerChanged.connect(self.current_layer_changed)

        self.x_field.setLayer(self.layer.currentLayer())

        self.type_graph.currentTextChanged.connect(self.check_form_graph_type)
        self.add_trace.clicked.connect(self.add_new_trace)
        self.remove_trace.clicked.connect(self.remove_selection)

        self.lwc_versions[LwcVersions.Lizmap_3_4] = [
            self.label_graph_34
        ]

        self.setup_ui()
        self.check_form_graph_type()

    def load_collection(self, value) -> None:
        """Load a collection into the table from JSON string."""
        for trace in value:
            row = self.traces.rowCount()
            self.traces.setRowCount(row + 1)
            self._edit_trace_row(row, trace)
        self.disable_more_trace()

    def primary_keys_collection(self) -> list:
        """Return the list of unique values in the collection."""
        values = list()
        for row in range(self.traces.rowCount()):
            item = self.traces.item(row, 0)
            cell = item.data(Qt.UserRole)
            values.append(cell)
        return values

    def save_collection(self) -> list:
        """Save a collection into JSON"""
        value = list()
        rows = self.traces.rowCount()

        collection_definition = self.config.layer_config['traces']
        for row in range(rows):
            trace_data = dict()
            for i, sub_key in enumerate(collection_definition['items']):

                input_type = self.config.layer_config[sub_key]['type']
                item = self.traces.item(row, i)

                if item is None:
                    # Safe guard
                    # Do not put if not item, it might be False
                    raise Exception('Cell is not initialized ({}, {})'.format(row, i))

                cell = item.data(Qt.UserRole)
                if cell is None:
                    # Safe guard
                    # Do not put if not cell, it might be False
                    raise Exception('Cell has no data ({}, {})'.format(row, i))

                if input_type == InputType.Field:
                    trace_data[sub_key] = cell
                elif input_type == InputType.Color:
                    trace_data[sub_key] = cell
                else:
                    raise Exception('InputType "{}" not implemented'.format(input_type))

            value.append(trace_data)

        return value

    def current_layer_changed(self):
        """When the layer is changed."""
        self.x_field.setLayer(self.layer.currentLayer())
        self.traces.setRowCount(0)

    def add_new_trace(self):
        """Add a new trace in the table after clicking the 'add' button."""
        graph = self.type_graph.currentData()
        for item_enum in GraphType:
            if item_enum.value['data'] == graph:
                graph = item_enum
                break
        else:
            raise Exception('Error with list')

        dialog = TraceDatavizEditionDialog(
            self.parent, self.layer.currentLayer(), graph, self.primary_keys_collection())
        result = dialog.exec_()
        if result == QDialog.Accepted:
            data = dialog.save_form()
            row = self.traces.rowCount()
            self.traces.setRowCount(row + 1)
            self._edit_trace_row(row, data)
            self.disable_more_trace()

    def _edit_trace_row(self, row, data):
        """Internal function to edit a row."""
        for i, key in enumerate(self.config.layer_config['traces']['items']):
            cell = QTableWidgetItem()

            value = data.get(key)
            if not value:
                cell.setText('')
                cell.setData(Qt.UserRole, '')
                self.traces.setItem(row, i, cell)
                continue

            input_type = self.config.layer_config[key]['type']
            if input_type == InputType.Field:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)

                # Get the icon for the field
                if self.layer:
                    index = self.layer.currentLayer().fields().indexFromName(value)
                    if index >= 0:
                        cell.setIcon(self.layer.currentLayer().fields().iconForField(index))

            elif input_type == InputType.Color:
                cell.setText(value)
                cell.setData(Qt.UserRole, value)
                cell.setData(Qt.ToolTipRole, value)
                if value:
                    cell.setData(Qt.DecorationRole, QColor(value))

            else:
                raise Exception('InputType "{}" not implemented'.format(input_type))

            self.traces.setItem(row, i, cell)
        self.traces.clearSelection()

    def remove_selection(self):
        """Remove the selected row from the table."""
        selection = self.traces.selectedIndexes()
        if len(selection) <= 0:
            return

        row = selection[0].row()
        self.traces.clearSelection()
        self.traces.removeRow(row)
        self.disable_more_trace()

    def disable_more_trace(self):
        """According to the kind of graph, the button might be disabled."""
        graph = self.type_graph.currentData()
        for item_enum in GraphType:
            if item_enum.value['data'] == graph:
                graph = item_enum
                break
        else:
            raise Exception('Error with list')

        if self.traces.rowCount() > 0 and graph in [GraphType.Pie, GraphType.Histogram2D]:
            self.add_trace.setEnabled(False)
        else:
            self.add_trace.setEnabled(True)

        version = QgsSettings().value(
            'lizmap/lizmap_web_client_version', DEFAULT_LWC_VERSION.value, str)
        version = LwcVersions(version)

        if version in [LwcVersions.Lizmap_3_1, LwcVersions.Lizmap_3_2, LwcVersions.Lizmap_3_3]:
            if self.traces.rowCount() >= 2:
                self.add_trace.setStyleSheet(NEW_FEATURE)
            else:
                self.add_trace.setStyleSheet('')
        else:
            self.add_trace.setStyleSheet('')

    def check_form_graph_type(self):
        """Enable or not features according to the type of graph."""
        graph = self.type_graph.currentData()
        for item_enum in GraphType:
            if item_enum.value['data'] == graph:
                graph = item_enum
                break
        else:
            raise Exception('Error with list')

        # Field X
        if graph in [
                GraphType.Scatter, GraphType.Bar, GraphType.Histogram,
                GraphType.Histogram2D, GraphType.Polar, GraphType.Pie,
                GraphType.Sunburst, GraphType.HtmlTemplate]:
            self.x_field.setAllowEmptyFieldName(False)
        elif graph in [GraphType.Box]:
            self.x_field.setAllowEmptyFieldName(True)
        else:
            raise Exception('Unknown graph type for X')

        # Bar chart
        is_bar_chart = graph == GraphType.Bar
        self.horizontal.setVisible(is_bar_chart)
        self.stacked.setVisible(is_bar_chart)

        # HTML template
        is_html_template = graph == GraphType.HtmlTemplate
        self.label_html_template.setVisible(is_html_template)
        self.html_template.setVisible(is_html_template)
        self.display_legend.setVisible(not is_html_template)

        # Add more trace button
        self.disable_more_trace()

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        layer = self.layer.currentLayer()
        wfs_layers_list = QgsProject.instance().readListEntry('WFSLayers', '')[0]
        for wfs_layer in wfs_layers_list:
            if layer.id() == wfs_layer:
                break
        else:
            msg = tr(
                'The layers you have chosen for this tool must be checked in the "WFS Capabilities"\n'
                ' option of the QGIS Server tab in the "Project Properties" dialog.')
            return msg

        if self.traces.rowCount() == 0:
            return tr('At least one Y field is required.')

        graph = self.type_graph.currentData()
        for item_enum in GraphType:
            if item_enum.value['data'] == graph:
                graph = item_enum
                break
        if graph == GraphType.HtmlTemplate:
            html = self.html_template.text()
            if html == '':
                return tr('HTML template is mandatory.')
