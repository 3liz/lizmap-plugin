"""Dialog for atlas edition."""

from qgis.core import QgsMapLayerProxyModel

from lizmap.definitions.atlas import AtlasDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_atlas.ui')


class AtlasEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.config = AtlasDefinitions()
        self.config.add_layer_widget('layer', self.layer)
        self.config.add_layer_widget('primaryKey', self.primary_key)
        self.config.add_layer_widget('displayLayerDescription', self.display_layer_description)
        self.config.add_layer_widget('featureLabel', self.feature_label)
        self.config.add_layer_widget('sortField', self.sort_field)
        self.config.add_layer_widget('highlightGeometry', self.highlight_geometry)
        self.config.add_layer_widget('zoom', self.zoom)
        self.config.add_layer_widget('displayPopup', self.display_popup)
        self.config.add_layer_widget('triggerFilter', self.trigger_filter)
        self.config.add_layer_widget('duration', self.duration)

        self.config.add_layer_label('layer', self.label_layer)
        self.config.add_layer_label('primaryKey', self.label_primary_key)
        self.config.add_layer_label('displayLayerDescription', self.label_layer_description)
        self.config.add_layer_label('featureLabel', self.label_feature_label)
        self.config.add_layer_label('sortField', self.label_sort_field)
        self.config.add_layer_label('highlightGeometry', self.label_highlight)
        self.config.add_layer_label('zoom', self.label_zoom)
        self.config.add_layer_label('displayPopup', self.label_popup)
        self.config.add_layer_label('triggerFilter', self.label_trigger)
        self.config.add_layer_label('duration', self.label_duration)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.primary_key.setAllowEmptyFieldName(False)
        self.feature_label.setAllowEmptyFieldName(False)
        self.sort_field.setAllowEmptyFieldName(False)

        self.layer.layerChanged.connect(self.check_layer_wfs)
        self.layer.layerChanged.connect(self.primary_key.setLayer)
        self.layer.layerChanged.connect(self.feature_label.setLayer)
        self.layer.layerChanged.connect(self.sort_field.setLayer)
        self.layer.layerChanged.connect(self.enable_primary_key_field)

        self.primary_key.setLayer(self.layer.currentLayer())
        self.feature_label.setLayer(self.layer.currentLayer())
        self.sort_field.setLayer(self.layer.currentLayer())

        self.setup_ui()
        self.check_layer_wfs()
        self.enable_primary_key_field()

    def check_layer_wfs(self):
        """ When the layer has changed in the combobox, check if the layer is published as WFS. """
        layer = self.layer.currentLayer()
        if not layer:
            self.show_error(tr('A layer is mandatory.'))
            return

        not_in_wfs = self.is_layer_in_wfs(layer)
        self.show_error(not_in_wfs)

    def validate(self) -> str:
        layer = self.layer.currentLayer()
        if not layer:
            return tr('A layer is mandatory.')

        upstream = super().validate()
        if upstream:
            return upstream

        not_in_wfs = self.is_layer_in_wfs(layer)
        if not_in_wfs:
            return not_in_wfs
