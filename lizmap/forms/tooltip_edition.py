"""Dialog for tooltip edition."""

from qgis.core import QgsMapLayerProxyModel
from qgis.PyQt.QtGui import QColor

from lizmap.definitions.tooltip import ToolTipDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


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
        self.layer.layerChanged.connect(self.check_layer_wfs)
        self.layer.layerChanged.connect(self.fields.set_layer)
        self.fields.set_layer(self.layer.currentLayer())

        self.display_geometry.toggled.connect(self.enable_color)
        self.enable_color()

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

    def enable_color(self):
        if self.display_geometry.isChecked():
            self.color.setEnabled(True)
            self.color.setColor(QColor('blue'))
        else:
            self.color.setEnabled(False)
            self.color.setToNull()

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        layer = self.layer.currentLayer()
        not_in_wfs = self.is_layer_in_wfs(layer)
        if not_in_wfs:
            return not_in_wfs

        if not self.fields.selection():
            return tr('At least one field is mandatory.')
