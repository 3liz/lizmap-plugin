"""Dialog for time manager."""

from qgis.core import QgsMapLayerProxyModel, QgsProject

from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.definitions.time_manager import TimeManagerDefinitions
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


CLASS = load_ui('ui_form_time_manager.ui')


class TimeManagerEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.config = TimeManagerDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('startAttribute', self.start_field)
        self.config.add_layer_widget('endAttribute', self.end_field)
        self.config.add_layer_widget('attributeResolution', self.resolution)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('startAttribute', self.label_start_attribute)
        self.config.add_layer_label('endAttribute', self.label_end_attribute)
        self.config.add_layer_label('attributeResolution', self.label_resolution)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)

        self.start_field.setAllowEmptyFieldName(False)
        self.end_field.setAllowEmptyFieldName(True)

        self.layer.layerChanged.connect(self.start_field.setLayer)
        self.layer.layerChanged.connect(self.end_field.setLayer)

        self.start_field.setLayer(self.layer.currentLayer())
        self.end_field.setLayer(self.layer.currentLayer())

        self.setup_ui()

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

        if not self.start_field.currentField():
            return tr('Start attribute is mandatory.')
