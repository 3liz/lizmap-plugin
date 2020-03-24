"""Dialog for editing a trace in the dataviz window."""
from collections import OrderedDict

from qgis.PyQt.QtWidgets import QTableWidgetItem, QAbstractItemView, QDialog, QDialogButtonBox
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsProject,
    QgsApplication,
)
from qgis.PyQt.QtGui import QIcon, QColor

from lizmap.definitions.base import InputType
from lizmap.definitions.dataviz import DatavizDefinitions, GraphType
from lizmap.definitions.definitions import LwcVersions
from lizmap.forms.base_edition_dialog import BaseEditionDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


CLASS = load_ui('ui_trace.ui')


class TraceDatavizEditionDialog(QDialog, CLASS):

    def __init__(self, parent, layer):
        super().__init__(parent)
        self.config = DatavizDefinitions()
        self._layer = layer
        self.setupUi(self)
        self.setWindowTitle(tr('Dataviz Trace'))

        self.field.setLayer(self._layer)
        self.color_field.setLayer(self._layer)

        self.config.add_layer_widget('y_field', self.field)
        self.config.add_layer_widget('colorfield', self.color_field)
        self.config.add_layer_widget('color', self.color)

        self.config.add_layer_label('y_field', self.label_y_field)
        self.config.add_layer_label('colorfield', self.label_color)

        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.error.setVisible(False)

        color_definition = self.config.layer_config['color']
        self.color.setDefaultColor(QColor(color_definition['default']))
        self.color.setToDefaultColor()

        self.color_field.setAllowEmptyFieldName(True)
        self.color_field.currentTextChanged.connect(self.check_y_color_field)
        self.check_y_color_field()

    def check_y_color_field(self):
        if self.color_field.currentField() == '':
            self.color.setToDefaultColor()
            self.color.setEnabled(True)
        else:
            self.color.setToNull()
            self.color.setEnabled(False)

    def validate(self):
        if self.field.currentField() == '':
            return tr('Field is required.')

        return

    def accept(self):
        message = self.validate()
        if message:
            self.error.setVisible(True)
            self.error.setText(message)
        else:
            super().accept()

    def save_form(self) -> OrderedDict:
        data = OrderedDict()

        for key in self.config.layer_config['traces']['items']:
            definition = self.config.layer_config[key]
            if definition['type'] == InputType.Field:
                value = definition['widget'].currentField()
            elif definition['type'] == InputType.Color:
                widget = definition['widget']
                if widget.isNull():
                    value = ''
                else:
                    value = widget.color().name()
            else:
                raise Exception('InputType "{}" not implemented'.format(definition['type']))

            data[key] = value
        return data

    def load_form(self, data: OrderedDict) -> None:
        for key in self.config.layer_config['traces']['items']:
            definition = self.config.layer_config[key]
            value = data.get(key)
            if definition['type'] == InputType.Field:
                definition['widget'].setField(value)
            elif definition['type'] == InputType.Color:
                color = QColor(value)
                if color.isValid():
                    definition['widget'].setDefaultColor(color)
                    definition['widget'].setColor(color)
                else:
                    definition['widget'].setToNull()
            else:
                raise Exception('InputType "{}" not implemented'.format(definition['type']))
