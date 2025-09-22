"""Dialog for filter by login."""

from qgis.core import QgsMapLayerProxyModel

from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.filter_by_login import (
    FilterByLoginDefinitions,
    SingleOrMultipleValues,
)
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_filter_by_login.ui')


class FilterByLoginEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None, lwc_version: LwcVersions = None):
        super().__init__(parent, unicity, lwc_version)
        self.setupUi(self)
        self.config = FilterByLoginDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('filterAttribute', self.field)
        self.config.add_layer_widget('filterPrivate', self.filter_by)
        self.config.add_layer_widget('allow_multiple_acl_values', self.allow_multiple)
        self.config.add_layer_widget('edition_only', self.edition_only)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('filterAttribute', self.label_field)
        self.config.add_layer_label('allow_multiple_acl_values', self.label_allow_multiple)
        self.config.add_layer_label('filterPrivate', self.label_filter_by)

        self.layer.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)
        self.layer.layerChanged.connect(self.field.setLayer)
        self.layer.layerChanged.connect(self.check_multiple_option)

        self.field.setAllowEmptyFieldName(False)
        self.field.setLayer(self.layer.currentLayer())

        self.check_multiple_option()
        self.setup_ui()

    def check_multiple_option(self):
        """ Check if we can enable the combobox or not. """
        layer = self.layer.currentLayer()

        # We always first disable the combobox
        self.allow_multiple.setEnabled(False)

        default = SingleOrMultipleValues.Single.value['data']
        index = self.allow_multiple.findData(default)

        if not layer or layer.dataProvider().name() != 'postgres':
            self.allow_multiple.setCurrentIndex(index)
        else:
            # Only enable it if the layer is stored in PostgreSQL
            self.allow_multiple.setEnabled(True)

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        if not self.field.currentField():
            return tr('Field is mandatory.')
