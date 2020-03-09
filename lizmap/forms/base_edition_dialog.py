"""Base class for the edition dialog."""

from collections import OrderedDict

from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.core import QgsProject

from ..definitions.base import InputType
from ..qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class BaseEditionDialog(QDialog):

    def __init__(self, parent=None, unicity=None):
        super().__init__(parent)
        self.config = None
        self.unicity = unicity

    def setup_ui(self):
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.error.setVisible(False)

        for layer_config in self.config.layer_config.values():
            widget = layer_config.get('widget')

            tooltip = layer_config.get('tooltip')
            if tooltip:
                label = layer_config.get('label')
                if label:
                    label.setToolTip(tooltip)
                if widget:
                    widget.setToolTip(tooltip)

            if layer_config['type'] == InputType.List:
                if widget is not None:
                    items = layer_config.get('items')
                    if items:
                        for item in items:
                            icon = item.value.get('icon')
                            if icon:
                                widget.addItem(QIcon(icon), item.value['label'], item.value['data'])
                            else:
                                widget.addItem(item.value['label'], item.value['data'])
                        default = layer_config.get('default')
                        if default:
                            index = widget.findData(default.value['data'])
                            widget.setCurrentIndex(index)

            if layer_config['type'] == InputType.CheckBox:
                if widget is not None:
                    widget.setChecked(layer_config['default'])

            if layer_config['type'] == InputType.Color:
                if widget is not None:
                    if layer_config['default'] == '':
                        widget.setShowNull(True)
                        widget.setToNull()
                    else:
                        widget.setDefaultColor(QColor(layer_config['default']))
                        widget.setToDefaultColor()

    def validate(self):
        if self.unicity:
            for key in self.unicity:
                for k, layer_config in self.config.layer_config.items():
                    if key == k:
                        if layer_config['type'] == InputType.Layer:
                            if layer_config['widget'].currentLayer().id() in self.unicity[key]:
                                msg = tr(
                                    'A duplicated "{}"="{}" is already in the table.'.format(
                                        key, layer_config['widget'].currentLayer().name()))
                                return msg
                        else:
                            raise Exception('InputType "{}" not implemented'.format(layer_config['type']))

        return None

    def accept(self):
        message = self.validate()
        if message:
            self.error.setVisible(True)
            self.error.setText(message)
        else:
            super().accept()

    def load_form(self, data: OrderedDict) -> None:
        """A dictionary to load in the UI."""
        for key, definition in self.config.layer_config.items():
            value = data.get(key)

            if definition['type'] == InputType.Layer:
                layer = QgsProject.instance().mapLayer(value)
                definition['widget'].setLayer(layer)
            elif definition['type'] == InputType.Field:
                definition['widget'].setField(value)
            elif definition['type'] == InputType.Fields:
                definition['widget'].set_selection(value.split(','))
            elif definition['type'] == InputType.CheckBox:
                definition['widget'].setChecked(value)
            elif definition['type'] == InputType.Color:
                color = QColor(value)
                if color.isValid():
                    definition['widget'].setDefaultColor(color)
                    definition['widget'].setColor(color)
                else:
                    definition['widget'].setToNull()
            elif definition['type'] == InputType.List:
                index = definition['widget'].findData(value)
                definition['widget'].setCurrentIndex(index)
            elif definition['type'] == InputType.SpinBox:
                definition['widget'].setValue(value)
            elif definition['type'] == InputType.Text:
                definition['widget'].setText(value)
            else:
                raise Exception('InputType "{}" not implemented'.format(definition['type']))

    def save_form(self) -> OrderedDict:
        """Save the UI in the dictionary with QGIS objects"""
        data = OrderedDict()
        for key, definition in self.config.layer_config.items():
            if definition['type'] == InputType.Layer:
                value = definition['widget'].currentLayer().id()
            elif definition['type'] == InputType.Field:
                value = definition['widget'].currentField()
            elif definition['type'] == InputType.Fields:
                value = ','.join(definition['widget'].selection())
            elif definition['type'] == InputType.Color:
                widget = definition['widget']
                if widget.isNull():
                    value = ''
                else:
                    value = widget.color().name()
            elif definition['type'] == InputType.CheckBox:
                value = definition['widget'].isChecked()
            elif definition['type'] == InputType.List:
                value = definition['widget'].currentData()
            elif definition['type'] == InputType.SpinBox:
                value = definition['widget'].value()
            elif definition['type'] == InputType.Text:
                value = definition['widget'].text().strip(' \t')
            else:
                raise Exception('InputType "{}" not implemented'.format(definition['type']))

            data[key] = value
        return data
