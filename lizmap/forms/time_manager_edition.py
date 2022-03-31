"""Dialog for time manager."""

from qgis.core import (
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsMapLayerProxyModel,
    QgsProject,
)

from lizmap.definitions.time_manager import TimeManagerDefinitions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui
from lizmap.tools import is_database_layer

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_form_time_manager.ui')


class TimeManagerEditionDialog(BaseEditionDialog, CLASS):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent, unicity)
        self.setupUi(self)
        self.config = TimeManagerDefinitions()
        self.config.add_layer_widget('layerId', self.layer)
        self.config.add_layer_widget('startAttribute', self.start_field)
        self.config.add_layer_widget('endAttribute', self.end_field)
        self.config.add_layer_widget('attributeResolution', self.resolution)
        self.config.add_layer_widget('min_timestamp', self.edit_min_value)
        self.config.add_layer_widget('max_timestamp', self.edit_max_value)

        self.config.add_layer_label('layerId', self.label_layer)
        self.config.add_layer_label('startAttribute', self.label_start_attribute)
        self.config.add_layer_label('endAttribute', self.label_end_attribute)
        self.config.add_layer_label('attributeResolution', self.label_resolution)
        self.config.add_layer_label('min_timestamp', self.label_min_value)
        self.config.add_layer_label('max_timestamp', self.label_max_value)

        self.layer.setFilters(QgsMapLayerProxyModel.VectorLayer)

        self.start_field.setAllowEmptyFieldName(False)
        self.end_field.setAllowEmptyFieldName(True)

        self.layer.layerChanged.connect(self.check_layer_wfs)
        self.layer.layerChanged.connect(self.start_field.setLayer)
        self.layer.layerChanged.connect(self.end_field.setLayer)
        self.layer.layerChanged.connect(self.set_visible_min_max)

        self.start_field.setLayer(self.layer.currentLayer())
        self.start_field.fieldChanged.connect(self.start_field_changed)
        self.end_field.setLayer(self.layer.currentLayer())
        self.end_field.fieldChanged.connect(self.end_field_changed)

        self.set_min_value.clicked.connect(self.compute_minimum_value)
        self.set_max_value.clicked.connect(self.compute_maximum_value)

        self.set_visible_min_max()
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

    def compute_minimum_value(self):
        value = self.compute_value_min_max(True)
        self.edit_min_value.setText(value)

    def compute_maximum_value(self):
        value = self.compute_value_min_max(False)
        self.edit_max_value.setText(value)

    def compute_value_min_max(self, is_min):
        layer = self.layer.currentLayer()
        start_field = self.start_field.currentField()
        end_field = self.end_field.currentField()

        if is_min:
            expression = 'minimum("{}")'.format(start_field)
        else:
            if end_field:
                expression = 'maximum("{}")'.format(end_field)
            else:
                expression = 'maximum("{}")'.format(start_field)

        exp_context = QgsExpressionContext()
        exp_context.appendScope(QgsExpressionContextUtils.globalScope())
        exp_context.appendScope(QgsExpressionContextUtils.projectScope(QgsProject.instance()))
        exp_context.appendScope(QgsExpressionContextUtils.layerScope(layer))

        exp = QgsExpression('to_string({})'.format(expression))
        exp.prepare(exp_context)
        value = exp.evaluate(exp_context)
        return value

    def set_visible_min_max(self):
        """ Some widgets are hidden when the layer is stored in a database.

        For PostgreSQL, GPKG and Sqlite, we don't display these widgets.
        """
        layer = self.layer.currentLayer()
        is_file_based = not is_database_layer(layer)
        self.label_min_value.setVisible(is_file_based)
        self.label_max_value.setVisible(is_file_based)
        self.set_min_value.setVisible(is_file_based)
        self.set_max_value.setVisible(is_file_based)
        self.edit_min_value.setVisible(is_file_based)
        self.edit_max_value.setVisible(is_file_based)
        self.edit_min_value.setText('')
        self.edit_max_value.setText('')

    def start_field_changed(self):
        self.edit_min_value.setText('')
        if not self.end_field.currentField():
            self.edit_max_value.setText('')

    def end_field_changed(self):
        self.edit_max_value.setText('')

    def validate(self) -> str:
        upstream = super().validate()
        if upstream:
            return upstream

        layer = self.layer.currentLayer()
        not_in_wfs = self.is_layer_in_wfs(layer)
        if not_in_wfs:
            return not_in_wfs

        if not self.start_field.currentField():
            return tr('Start attribute is mandatory.')

        msg = tr('The min/max values must be computed.')
        if self.edit_min_value.isVisible():
            if self.edit_min_value.text() == '' or self.edit_max_value.text() == '':
                return msg
