"""Dialog for time manager."""

from qgis.core import QgsMapLayerProxyModel, QgsProject

from .base_edition_dialog import BaseEditionDialog
from ..definitions.time_manager import TimeManagerDefinitions
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.resources import load_ui

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
        self.config.add_layer_widget('label', self.feature_label)
        self.config.add_layer_widget('group', self.group_id)
        self.config.add_layer_widget('groupTitle', self.group_title)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('startAttribute', self.label_start_attribute)
        self.config.add_layer_label('label', self.label_feature_label)
        self.config.add_layer_label('group', self.label_group_id)
        self.config.add_layer_label('groupTitle', self.label_group_title)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)

        self.start_field.setAllowEmptyFieldName(False)
        self.feature_label.setAllowEmptyFieldName(True)

        self.layer.layerChanged.connect(self.start_field.setLayer)
        self.layer.layerChanged.connect(self.feature_label.setLayer)

        self.start_field.setLayer(self.layer.currentLayer())
        self.feature_label.setLayer(self.layer.currentLayer())

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
