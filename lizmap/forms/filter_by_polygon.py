"""Dialog for filter by polygon."""

from qgis.core import QgsMapLayerProxyModel

from lizmap.definitions.filter_by_polygon import FilterByPolygonDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_filter_by_polygon.ui')


class FilterByPolygonEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.config = FilterByPolygonDefinitions()
        self.config.add_layer_widget('layer', self.layer)
        self.config.add_layer_widget('primary_key', self.primary_key)
        self.config.add_layer_widget('filter_mode', self.filter_mode)

        self.config.add_layer_label('layer', self.label_layer)
        self.config.add_layer_label('primary_key', self.label_primary_key)
        self.config.add_layer_label('filter_mode', self.label_filter_mode)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer.layerChanged.connect(self.primary_key.setLayer)

        self.primary_key.setAllowEmptyFieldName(False)
        self.primary_key.setLayer(self.layer.currentLayer())

        self.setup_ui()

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        if not self.primary_key.currentField():
            return tr('Field is mandatory.')
