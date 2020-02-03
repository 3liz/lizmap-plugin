"""Dialog for atlas edition."""

from qgis.core import QgsMapLayerProxyModel

from .base_edition_dialog import BaseEditionDialog
from ..definitions.atlas import AtlasDefinitions
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


CLASS = load_ui('ui_form_atlas.ui')


class AtlasEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, unicity=None):
        super().__init__(unicity)
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

        self.layer.layerChanged.connect(self.primary_key.setLayer)
        self.layer.layerChanged.connect(self.feature_label.setLayer)
        self.layer.layerChanged.connect(self.sort_field.setLayer)

        self.primary_key.setLayer(self.layer.currentLayer())
        self.feature_label.setLayer(self.layer.currentLayer())
        self.sort_field.setLayer(self.layer.currentLayer())

        self.zoom.addItem('', '')
        self.zoom.addItem('zoom', 'zoom')
        self.zoom.addItem('center', 'center')
        self.setup_ui()

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        if not self.primary_key.currentField():
            return tr('Primary key field is compulsory.')

        if not self.feature_label.currentField():
            return tr('Label field is compulsory.')

        if not self.sort_field.currentField():
            return tr('Sort field is compulsory.')
