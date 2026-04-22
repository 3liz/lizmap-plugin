"""Dialog for folio portfolio edition."""
from collections import OrderedDict
from functools import reduce

from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from lizmap.definitions.base import InputType, InputTypeError
from lizmap.definitions.portfolio import (
    GeometryType,
    PortfolioDefinitions,
    ZoomMethodType,
)
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


CLASS = load_ui('ui_portfolio_folio.ui')


class FolioPortfolioEditionDialog(QDialog, CLASS):

    def __init__(self, parent, geometry, uniques):
        super().__init__(parent)
        self.config = PortfolioDefinitions()
        self._geometry = geometry
        self.uniques = uniques
        self.setupUi(self)

        self.config.add_layer_widget('layout', self.layout)
        self.config.add_layer_widget('theme', self.theme)
        self.config.add_layer_widget('zoom_method', self.zoom_method)
        self.config.add_layer_widget('fixed_scale', self.fixed_scale)
        self.config.add_layer_widget('margin', self.margin)

        self.config.add_layer_label('layout', self.label_layout)
        self.config.add_layer_label('theme', self.label_theme)
        self.config.add_layer_label('zoom_method', self.label_zoom_method)
        self.config.add_layer_label('fixed_scale', self.label_fixed_scale)
        self.config.add_layer_label('margin', self.label_margin)

        layout_manager = QgsProject.instance().layoutManager()
        for layout in layout_manager.printLayouts():
            if layout.atlas().enabled():
                continue
            self.layout.addItem(layout.name(), layout.name())

        theme_collection = QgsProject.instance().mapThemeCollection()
        for theme_name in theme_collection.mapThemes():
            self.theme.addItem(theme_name, theme_name)

        self.fixed_scale.setScale(self.config.layer_config['fixed_scale'].get('default'))
        self.margin.setValue(self.config.layer_config['margin'].get('default'))

        if self._geometry == GeometryType.Point.value['data']:
            fixed_scale = ZoomMethodType.FixedScale
            self.zoom_method.addItem(fixed_scale.value['label'], fixed_scale.value['data'])
            self.zoom_method.setCurrentText(fixed_scale.value['data'])
            self.zoom_method.setEnabled(False)
        else:
            for item_type in ZoomMethodType:
                if item_type == ZoomMethodType.FixedScale:
                    continue
                self.zoom_method.addItem(item_type.value['label'], item_type.value['data'])

        # connect
        self.zoom_method.currentTextChanged.connect(self.zoom_method_changed)

        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.accept)
        self.error.setVisible(False)

        self.zoom_method_changed()

    def zoom_method_changed(self):
        """Enable or disable scale and margin widgets."""
        zoom_method = self.zoom_method.currentData()
        enable_margin = False
        enable_fixed_scale = False
        if zoom_method == ZoomMethodType.Margin.value['data']:
            enable_margin = True
        elif zoom_method == ZoomMethodType.FixedScale.value['data']:
            enable_fixed_scale = True

        self.margin.setEnabled(enable_margin)
        self.fixed_scale.setEnabled(enable_fixed_scale)

    def validate(self):
        """validate the form."""
        self.error.setVisible(False)
        data = self.save_form()
        messages = []

        # Check mandatories
        if not data.get('layout'):
            messages.append(tr('Layout is mandatory'))
        if not data.get('theme'):
            messages.append(tr('Theme is mandatory'))
        if not data.get('zoom_method'):
            messages.append(tr('Zoom method is mandatory'))

        if messages:
            return '\n'.join(messages)

        # Check unicity
        for layout_data in self.uniques:
            equalities = []
            for key in self.config.layer_config['folios']['items']:
                equalities.append(data.get(key) == layout_data.get(key))
            if reduce(lambda x, y: x and y, equalities):
                messages.append(tr('This layout definition is already set'))
                break

        if messages:
            return '\n'.join(messages)

        return None

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

        for key in self.config.layer_config['folios']['items']:
            definition = self.config.layer_config[key]
            if definition['type'] == InputType.List:
                value = definition['widget'].currentData()
            elif definition['type'] == InputType.Scale:
                value = definition['widget'].scale()
            elif definition['type'] == InputType.SpinBox:
                value = int(definition['widget'].value())
            else:
                raise InputTypeError('InputType "{}" not implemented'.format(definition['type']))

            data[key] = value

        if data['zoom_method'] == ZoomMethodType.BestScale.value['data']:
            del data['fixed_scale']
            del data['margin']
        elif data['zoom_method'] == ZoomMethodType.Margin.value['data']:
            del data['fixed_scale']
        elif data['zoom_method'] == ZoomMethodType.FixedScale.value['data']:
            del data['margin']
        return data
