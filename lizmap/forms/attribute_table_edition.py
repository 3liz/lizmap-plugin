"""Dialog for attribute table edition."""

from qgis.core import QgsMapLayerProxyModel, QgsProject

from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.definitions.attribute_table import AttributeTableDefinitions
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui


__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


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

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('primaryKey', self.label_primary_key)
        self.config.add_layer_label('hiddenFields', self.label_fields_to_hide)
        self.config.add_layer_label('pivot', self.label_pivot_table)
        self.config.add_layer_label('hideAsChild', self.label_hide_subpanels)
        self.config.add_layer_label('hideLayer', self.label_hide_layer)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer.layerChanged.connect(self.field_primary_key.setLayer)
        self.field_primary_key.setLayer(self.layer.currentLayer())
        self.layer.layerChanged.connect(self.fields_to_hide.set_layer)
        self.fields_to_hide.set_layer(self.layer.currentLayer())

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

        if not self.field_primary_key.currentField():
            return tr('Primary key field is mandatory.')
