"""Dialog for tooltip edition."""

from qgis.core import QgsMapLayerProxyModel, QgsProject
from qgis.PyQt.QtGui import QColor

from lizmap.definitions.tooltip import ToolTipDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

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
        self.layer.layerChanged.connect(self.fields.set_layer)
        self.fields.set_layer(self.layer.currentLayer())

        self.display_geometry.toggled.connect(self.enable_color)
        self.enable_color()

        self.setup_ui()

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
        wfs_layers_list = QgsProject.instance().readListEntry('WFSLayers', '')[0]
        for wfs_layer in wfs_layers_list:
            if layer.id() == wfs_layer:
                break
        else:
            msg = tr(
                'The layers you have chosen for this tool must be checked in the "WFS Capabilities"\n'
                ' option of the QGIS Server tab in the "Project Properties" dialog.')
            return msg

        if not self.fields.selection():
            return tr('At least one field is mandatory.')
