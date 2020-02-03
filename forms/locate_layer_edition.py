"""Dialog for locate by layer edition."""

from qgis.core import QgsMapLayerProxyModel, QgsProject

from .base_edition_dialog import BaseEditionDialog
from ..definitions.locate_by_layer import LocateByLayerDefinitions
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


CLASS = load_ui('ui_form_locate_layer.ui')


class LocateLayerEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, unicity=None):
        super().__init__(unicity)
        self.setupUi(self)
        self.config = LocateByLayerDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('fieldName', self.display_field)
        self.config.add_layer_widget('filterFieldName', self.field_group_by)
        self.config.add_layer_widget('displayGeom', self.display_geometry)
        self.config.add_layer_widget('minLength', self.autocomplete)
        self.config.add_layer_widget('filterOnLocate', self.filter_layer)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('fieldName', self.label_display_field)
        self.config.add_layer_label('filterFieldName', self.label_group_by)
        self.config.add_layer_label('displayGeom', self.label_display_geom)
        self.config.add_layer_label('minLength', self.label_autocomplete)
        self.config.add_layer_label('filterOnLocate', self.label_filter_layer)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer.layerChanged.connect(self.display_field.setLayer)
        self.layer.layerChanged.connect(self.field_group_by.setLayer)

        self.display_field.setAllowEmptyFieldName(False)
        self.display_field.setLayer(self.layer.currentLayer())

        self.field_group_by.setAllowEmptyFieldName(True)
        self.field_group_by.setLayer(self.layer.currentLayer())

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

        if not self.display_field.currentField():
            return tr('Display field is compulsory.')
