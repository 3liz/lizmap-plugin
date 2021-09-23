"""Dialog for attribute table edition."""

from qgis.core import QgsMapLayerProxyModel

from lizmap.definitions.attribute_table import (
    AttributeTableDefinitions,
    layer_has_custom_attribute_table,
)
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_attribute_table.ui')


class AttributeTableEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.config = AttributeTableDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('primaryKey', self.field_primary_key)
        self.config.add_layer_widget('hiddenFields', self.fields_to_hide)
        self.config.add_layer_widget('pivot', self.pivot_table)
        self.config.add_layer_widget('hideAsChild', self.hide_subpanels)
        self.config.add_layer_widget('hideLayer', self.hide_layer)
        self.config.add_layer_widget('custom_config', self.has_custom_config)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('primaryKey', self.label_primary_key)
        self.config.add_layer_label('hiddenFields', self.label_fields_to_hide)
        self.config.add_layer_label('pivot', self.label_pivot_table)
        self.config.add_layer_label('hideAsChild', self.label_hide_subpanels)
        self.config.add_layer_label('hideLayer', self.label_hide_layer)
        self.config.add_layer_label('custom_config', self.label_has_custom_config)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer.layerChanged.connect(self.layer_changed)
        self.layer.layerChanged.connect(self.field_primary_key.setLayer)
        self.field_primary_key.setLayer(self.layer.currentLayer())
        self.layer.layerChanged.connect(self.fields_to_hide.set_layer)
        self.fields_to_hide.set_layer(self.layer.currentLayer())

        self.setup_ui()

    def post_load_form(self):
        self.layer_changed()

    def layer_changed(self):
        layer = self.layer.currentLayer()
        self.has_custom_config.setChecked(layer_has_custom_attribute_table(layer))

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        layer = self.layer.currentLayer()
        not_in_wfs = self.is_layer_in_wfs(layer)
        if not_in_wfs:
            return not_in_wfs

        if not self.field_primary_key.currentField():
            return tr('Primary key field is mandatory.')
