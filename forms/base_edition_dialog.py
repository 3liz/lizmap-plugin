"""Base class for the edition dialog."""

from collections import OrderedDict

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.core import QgsProject

from ..definitions.base import InputType, BaseDefinitions

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class BaseEditionDialog(QDialog):

    def __init__(self,):
        super().__init__()
        self.config: BaseDefinitions

    def setup_ui(self):
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.error.setVisible(False)

        for layer_config in self.config.layer_config.values():
            tooltip = layer_config.get('tooltip')
            if tooltip:
                label = layer_config.get('label')
                if label:
                    label.setToolTip(tooltip)
                widget = layer_config.get('widget')
                if widget:
                    widget.setToolTip(tooltip)

    def validate(self):
        raise NotImplementedError

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
            elif definition['type'] == InputType.CheckBox:
                definition['widget'].setChecked(value)
            elif definition['type'] == InputType.List:
                index = definition['widget'].findData(value)
                definition['widget'].setCurrentIndex(index)
            elif definition['type'] == InputType.SpinBox:
                definition['widget'].setValue(value)
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
            elif definition['type'] == InputType.CheckBox:
                value = definition['widget'].isChecked()
            elif definition['type'] == InputType.List:
                value = definition['widget'].currentData()
            elif definition['type'] == InputType.SpinBox:
                value = definition['widget'].value()
            else:
                raise Exception('InputType "{}" not implemented'.format(definition['type']))

            data[key] = value
        return data
