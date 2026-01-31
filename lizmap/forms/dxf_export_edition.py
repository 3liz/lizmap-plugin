"""Dialog for DXF export edition."""
from typing import Dict, Optional

from qgis.core import QgsMapLayerProxyModel
from qgis.PyQt.QtWidgets import QWidget

from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.dxf_export import DxfExportDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui

CLASS = load_ui('ui_form_dxf_export.ui')


class DxfExportEditionDialog(BaseEditionDialog, CLASS):

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        unicity: Optional[Dict[str, str]] = None,
        lwc_version: Optional[LwcVersions] = None,
    ):
        super().__init__(parent, unicity, lwc_version)
        self.setupUi(self)
        self.config = DxfExportDefinitions()

        # Layer configuration
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('enabled', self.enabled)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('enabled', self.label_enabled)

        # Set layer filter to only show vector layers
        self.layer.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)
        self.layer.layerChanged.connect(self.check_layer_wfs)

        self.setup_ui()
        self.check_layer_wfs()

    def check_layer_wfs(self):
        """When the layer has changed in the combobox, check if the layer is published as WFS."""
        layer = self.layer.currentLayer()
        if not layer:
            self.show_error(tr('A layer is mandatory.'))
            return

        not_in_wfs = self.is_layer_in_wfs(layer)
        self.show_error(not_in_wfs)

    def validate(self) -> Optional[str]:
        upstream = super().validate()
        if upstream:
            return upstream

        layer = self.layer.currentLayer()
        not_in_wfs = self.is_layer_in_wfs(layer)
        if not_in_wfs:
            return not_in_wfs

        return None
