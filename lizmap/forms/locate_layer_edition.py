"""Dialog for locate by layer edition."""

from qgis.core import QgsMapLayerProxyModel

from lizmap.definitions.locate_by_layer import LocateByLayerDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_locate_layer.ui')


class LocateLayerEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
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
        self.layer.layerChanged.connect(self.check_layer_wfs)
        self.layer.layerChanged.connect(self.display_field.setLayer)
        self.layer.layerChanged.connect(self.field_group_by.setLayer)

        self.display_field.setAllowEmptyFieldName(False)
        self.display_field.setLayer(self.layer.currentLayer())

        self.field_group_by.setAllowEmptyFieldName(True)
        self.field_group_by.setLayer(self.layer.currentLayer())

        self.setup_ui()
        self.check_layer_wfs()

    def check_layer_wfs(self):
        """ When the layer has changed in the combobox, check if the layer is published as WFS. """
        layer = self.layer.currentLayer()
        if not layer:
            self.show_error(tr('A layer is mandatory.'))
            return

        not_in_wfs = self.is_layer_in_wfs(layer)
        self.show_error(not_in_wfs)

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        layer = self.layer.currentLayer()
        not_in_wfs = self.is_layer_in_wfs(layer)
        if not_in_wfs:
            return not_in_wfs

        if not self.display_field.currentField():
            return tr('Display field is mandatory.')
