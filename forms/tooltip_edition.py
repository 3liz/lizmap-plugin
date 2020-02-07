"""Dialog for tooltip edition."""

from qgis.core import QgsMapLayerProxyModel, QgsProject

from .base_edition_dialog import BaseEditionDialog
from ..definitions.tooltip import ToolTipDefinitions
from ..qgis_plugin_tools.tools.i18n import tr
from ..qgis_plugin_tools.tools.resources import load_ui
from ..qgis_plugin_tools.widgets.selectable_combobox import CheckableFieldComboBox


__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


CLASS = load_ui('ui_form_tooltip.ui')


class ToolTipEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.config = ToolTipDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('fields', self.fields)
        self.config.add_layer_widget('displayGeom', self.display_geometry)
        self.config.add_layer_widget('colorGeom', self.color)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('fields', self.label_fields)
        self.config.add_layer_label('displayGeom', self.label_display_geometry)
        self.config.add_layer_label('colorGeom', self.label_color)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.fields_checkable = CheckableFieldComboBox(self.fields)
        self.layer.layerChanged.connect(self.fields_checkable.set_layer)
        self.fields_checkable.set_layer(self.layer.currentLayer())

        self.setup_ui()

    def load_fields(self, key, values):
        _ = key
        self.fields_checkable.set_selected_items(values)

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

        if not self.fields_checkable.selected_items():
            return tr('At least one field is compulsory.')
