"""Dialog for editing a trace in the dataviz window."""
from collections import OrderedDict

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from lizmap.definitions.base import InputType
from lizmap.definitions.dataviz import DatavizDefinitions, GraphType
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_trace.ui')


class TraceDatavizEditionDialog(QDialog, CLASS):

    def __init__(self, parent, layer, graph, uniques):
        super().__init__(parent)
        self.config = DatavizDefinitions()
        self._graph = graph
        self._layer = layer
        self.uniques = uniques
        self.setupUi(self)
        self.setWindowTitle(tr('Dataviz Trace'))

        self.y_field.setLayer(self._layer)
        self.color_field.setLayer(self._layer)
        self.z_field.setLayer(self._layer)

        self.config.add_layer_widget('y_field', self.y_field)
        self.config.add_layer_widget('colorfield', self.color_field)
        self.config.add_layer_widget('color', self.color)
        self.config.add_layer_widget('z_field', self.z_field)

        self.config.add_layer_label('y_field', self.label_y_field)
        self.config.add_layer_label('colorfield', self.label_color)
        self.config.add_layer_label('z_field', self.label_z_field)

        self.y_field.setAllowEmptyFieldName(False)
        self.z_field.setAllowEmptyFieldName(True)
        self.color_field.setAllowEmptyFieldName(True)

        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.error.setVisible(False)

        color_definition = self.config.layer_config['color']
        self.color.setDefaultColor(QColor(color_definition['default']))
        self.color.setToDefaultColor()

        self.color_field.setAllowEmptyFieldName(True)
        self.color_field.currentTextChanged.connect(self.check_y_color_field)
        self.check_y_color_field()

        # Z Field
        if self._graph == GraphType.Sunburst:
            self.label_z_field.setVisible(True)
            self.z_field.setVisible(True)
            self.z_field.setAllowEmptyFieldName(False)
        else:
            self.label_z_field.setVisible(False)
            self.z_field.setVisible(False)
            self.z_field.setAllowEmptyFieldName(True)
            self.z_field.setCurrentIndex(0)

        # Color field
        histo_2d = self._graph == GraphType.Histogram2D
        self.label_color.setVisible(not histo_2d)
        self.color_field.setVisible(not histo_2d)
        self.color.setVisible(not histo_2d)

    def check_y_color_field(self):
        """Enable or disable the color input."""
        if self.color_field.currentField() == '':
            self.color.setToDefaultColor()
            self.color.setEnabled(True)
        else:
            self.color.setToNull()
            self.color.setEnabled(False)

    def validate(self):
        y_field = self.y_field.currentField()
        if y_field == '':
            return tr('Y field is required.')
        if y_field in self.uniques:
            return tr('This Y field is already existing.')
        return

    def accept(self):
        message = self.validate()
        if message:
            self.error.setVisible(True)
            self.error.setText(message)
        else:
            super().accept()

    def save_form(self) -> OrderedDict:
        """Save the form into a dictionary."""
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
        """Load a dictionary into the form."""
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
