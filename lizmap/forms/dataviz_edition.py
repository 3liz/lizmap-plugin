"""Dialog for dataviz edition."""
from qgis.core import QgsMapLayerProxyModel, QgsProject

from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.definitions.dataviz import DatavizDefinitions, GraphType, AggregationType
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
        self.config = DatavizDefinitions()
        self.config.add_layer_widget('title', self.title)
        self.config.add_layer_widget('type', self.type_graph)
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('x_field', self.x_field)
        self.config.add_layer_widget('aggregation', self.aggregation)
        self.config.add_layer_widget('y_field', self.y_field)
        self.config.add_layer_widget('color', self.color)
        self.config.add_layer_widget('colorfield', self.color_field)
        self.config.add_layer_widget('y2_field', self.y_field_2)
        self.config.add_layer_widget('colorfield2', self.color_field_2)
        self.config.add_layer_widget('color2', self.color_2)
        self.config.add_layer_widget('popup_display_child_plot', self.popup_display_child_plot)
        self.config.add_layer_widget('only_show_child', self.only_show_child)

        self.config.add_layer_label('title', self.label_title)
        self.config.add_layer_label('type', self.label_type)
        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('x_field', self.label_x_field)
        self.config.add_layer_label('aggregation', self.label_aggregation)
        self.config.add_layer_label('y_field', self.label_y_field)
        self.config.add_layer_label('color', self.label_y_color)
        self.config.add_layer_label('y2_field', self.label_y_field_2)
        self.config.add_layer_label('colorfield2', self.label_y_color_2)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer.layerChanged.connect(self.x_field.setLayer)
        self.layer.layerChanged.connect(self.y_field.setLayer)
        self.layer.layerChanged.connect(self.y_field_2.setLayer)
        self.layer.layerChanged.connect(self.color_field.setLayer)
        self.layer.layerChanged.connect(self.color_field_2.setLayer)

        # self.x_field.setAllowEmptyFieldName(False) DONE according to kind of graph
        self.y_field.setAllowEmptyFieldName(False)
        self.y_field_2.setAllowEmptyFieldName(True)
        self.color_field.setAllowEmptyFieldName(True)
        self.color_field_2.setAllowEmptyFieldName(True)
        
        self.x_field.setLayer(self.layer.currentLayer())
        self.y_field.setLayer(self.layer.currentLayer())
        self.y_field_2.setLayer(self.layer.currentLayer())
        self.color_field.setLayer(self.layer.currentLayer())
        self.color_field_2.setLayer(self.layer.currentLayer())

        self.type_graph.currentTextChanged.connect(self.check_form_graph_type)
        self.y_field_2.currentTextChanged.connect(self.check_y_2_field)
        self.color_field.currentTextChanged.connect(self.check_y_color_field)
        self.color_field_2.currentTextChanged.connect(self.check_y_2_color_field)

        self.setup_ui()
        self.check_form_graph_type()
        self.check_y_color_field()
        self.check_y_2_field()

    def check_form_graph_type(self):
        graph = self.type_graph.currentData()
        for item_enum in GraphType:
            if item_enum.value['data'] == graph:
                graph = item_enum
                break
        else:
            raise Exception('Error with list')
        if graph in [GraphType.Scatter, GraphType.Bar, GraphType.Histogram, GraphType.Histogram2D, GraphType.Polar, GraphType.Pie]:
            self.x_field.setAllowEmptyFieldName(False)
        elif graph in [GraphType.Box]:
            self.x_field.setAllowEmptyFieldName(True)
        else:
            raise Exception('unknown graph type for X')

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

        if graph != GraphType.Box:
            index = self.aggregation.findData(AggregationType.No.value['data'])
            if index >= 0:
                self.aggregation.removeItem(index)
            self.aggregation.setCurrentIndex(0)
        else:
            index = self.aggregation.findData(AggregationType.No.value['data'])
            if index < 0:
                self.aggregation.addItem(
                    AggregationType.No.value['label'], AggregationType.No.value['data'])
            index = self.aggregation.findData(AggregationType.No.value['data'])
            self.aggregation.setCurrentIndex(index)

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
