"""Dialog for dataviz edition."""
from qgis.PyQt.QtWidgets import QTableWidgetItem, QAbstractItemView, QDialog, QHeaderView
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsProject,
    QgsApplication,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QColor

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
        # self.config.add_layer_widget('y_field', self.y_field)
        # self.config.add_layer_widget('color', self.color)
        # self.config.add_layer_widget('colorfield', self.color_field)
        # self.config.add_layer_widget('y2_field', self.y_field_2)
        # self.config.add_layer_widget('colorfield2', self.color_field_2)
        # self.config.add_layer_widget('color2', self.color_2)
        # self.config.add_layer_widget('z_field', self.z_field)
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

        # self.config.add_layer_label('colorfield2', self.label_y_color_2)
        # self.config.add_layer_label('z_field', self.label_z_field)
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
        # self.traces.cellDoubleClicked.connect(self.edit_existing_row)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer.layerChanged.connect(self.current_layer_changed)
        # self.layer.layerChanged.connect(self.y_field.setLayer)
        # self.layer.layerChanged.connect(self.z_field.setLayer)
        # self.layer.layerChanged.connect(self.color_field.setLayer)
        # self.layer.layerChanged.connect(self.y_field_2.setLayer)
        # self.layer.layerChanged.connect(self.color_field_2.setLayer)

        # self.y_field.setAllowEmptyFieldName(False)
        # self.z_field.setAllowEmptyFieldName(True)
        # self.y_field_2.setAllowEmptyFieldName(True)
        # self.color_field.setAllowEmptyFieldName(True)
        # self.color_field_2.setAllowEmptyFieldName(True)

        self.x_field.setLayer(self.layer.currentLayer())
        # self.y_field.setLayer(self.layer.currentLayer())
        # self.z_field.setLayer(self.layer.currentLayer())
        # self.y_field_2.setLayer(self.layer.currentLayer())
        # self.color_field.setLayer(self.layer.currentLayer())
        # self.color_field_2.setLayer(self.layer.currentLayer())

        # self.type_graph.currentTextChanged.connect(self.check_form_graph_type)
        # self.y_field_2.currentTextChanged.connect(self.check_y_2_field)
        # self.color_field.currentTextChanged.connect(self.check_y_color_field)
        # self.color_field_2.currentTextChanged.connect(self.check_y_2_color_field)
        self.add_trace.clicked.connect(self.add_new_trace)
        self.remove_trace.clicked.connect(self.remove_selection)

        self.lwc_versions[LwcVersions.Lizmap_3_4] = [
            self.label_graph_34
        ]

        self.setup_ui()
        # self.check_form_graph_type()
        # self.check_y_color_field()
        # self.check_y_2_field()

    def current_layer_changed(self):
        """When the layer is changed."""
        self.x_field.setLayer(self.layer.currentLayer())
        self.traces.setRowCount(0)

    def add_new_trace(self):
        graph = self.type_graph.currentData()
        for item_enum in GraphType:
            if item_enum.value['data'] == graph:
                graph = item_enum
                break
        else:
            raise Exception('Error with list')
        dialog = TraceDatavizEditionDialog(self.parent, self.layer.currentLayer(), graph)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            data = dialog.save_form()
            row = self.traces.rowCount()
            self.traces.setRowCount(row + 1)
            self._edit_trace_row(row, data)

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

    def check_form_graph_type(self):
        graph = self.type_graph.currentData()
        for item_enum in GraphType:
            if item_enum.value['data'] == graph:
                graph = item_enum
                break
        else:
            raise Exception('Error with list')

        if graph in [
                GraphType.Scatter, GraphType.Bar, GraphType.Histogram,
                GraphType.Histogram2D, GraphType.Polar, GraphType.Pie,
                GraphType.Sunburst, GraphType.HtmlTemplate]:
            self.x_field.setAllowEmptyFieldName(False)
        elif graph in [GraphType.Box]:
            self.x_field.setAllowEmptyFieldName(True)
        else:
            raise Exception('Unknown graph type for X')

        self.label_y_color.setVisible(graph != GraphType.Histogram2D)
        self.color_field.setVisible(graph != GraphType.Histogram2D)
        self.color.setVisible(graph != GraphType.Histogram2D)

        if graph in [GraphType.Pie, GraphType.Histogram2D]:
            # Disable Y field 2
            self.y_field_2.setAllowEmptyFieldName(True)
            self.y_field_2.setCurrentIndex(0)
            self.y_field_2.setVisible(False)
            self.color_2.setVisible(False)
            self.color_field_2.setVisible(False)
            self.label_y_field_2.setVisible(False)
            self.label_y_color_2.setVisible(False)
        else:
            # Enable Y field 2
            self.y_field_2.setAllowEmptyFieldName(True)
            self.y_field_2.setVisible(True)
            self.color_2.setVisible(True)
            self.color_field_2.setVisible(True)
            self.label_y_field_2.setVisible(True)
            self.label_y_color_2.setVisible(True)

        # Bar chart
        self.horizontal.setVisible(graph == GraphType.Bar)
        self.stacked.setVisible(graph == GraphType.Bar)

        self.label_html_template.setVisible(graph == GraphType.HtmlTemplate)
        self.html_template.setVisible(graph == GraphType.HtmlTemplate)
        self.display_legend.setVisible(graph != GraphType.HtmlTemplate)

    def check_y_color_field(self):
        if self.color_field.currentField() == '':
            self.color.setToDefaultColor()
            self.color.setEnabled(True)
        else:
            self.color.setToNull()
            self.color.setEnabled(False)

    def check_y_2_field(self):
        """Enable or disable the Y2 color."""
        if self.y_field_2.currentField() == '':
            self.color_field_2.setEnabled(False)
        else:
            self.color_field_2.setEnabled(True)
        self.color_field_2.setCurrentIndex(0)
        self.check_y_2_color_field()

    def check_y_2_color_field(self):
        if self.y_field_2.currentField() == '':
            self.color_2.setToNull()
            self.color_2.setEnabled(False)
            return

        if self.color_field_2.currentField():
            self.color_2.setToNull()
            self.color_2.setEnabled(False)
        else:
            self.color_2.setToDefaultColor()
            self.color_2.setEnabled(True)

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

        graph = self.type_graph.currentData()
        for item_enum in GraphType:
            if item_enum.value['data'] == graph:
                graph = item_enum
                break
        if graph == GraphType.HtmlTemplate:
            html = self.html_template.toPlainText()
            if html == '':
                return tr('HTML template is mandatory.')
