"""Dialog for filter by login."""

from qgis.core import QgsMapLayerProxyModel

from lizmap.definitions.filter_by_login import FilterByLoginDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_filter_by_login.ui')


class FilterByLoginEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.config = FilterByLoginDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('filterAttribute', self.field)
        self.config.add_layer_widget('filterPrivate', self.filter_by)
        self.config.add_layer_widget('edition_only', self.edition_only)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('filterAttribute', self.label_field)
        self.config.add_layer_label('filterPrivate', self.label_filter_by)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer.layerChanged.connect(self.field.setLayer)

        self.field.setAllowEmptyFieldName(False)
        self.field.setLayer(self.layer.currentLayer())

        self.setup_ui()

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        if not self.field.currentField():
            return tr('Field is mandatory.')
