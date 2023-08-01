"""Base class for definitions."""

from collections import OrderedDict
from enum import Enum, unique

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


@unique
class InputType(Enum):
    Collection = 'Collection'  # Does not have an input widget, it's a JSON representation
    Color = 'Color'  # QgsColorButton
    CheckBox = 'CheckBox'  # QCheckbox
    CheckBoxAsDropdown = 'CheckBoxAsDropdown'  # QComboBox with only two options
    Field = 'Field'  # QgsFieldComboBox
    PrimaryKeyField = 'PrimaryKeyField'  # QgsFieldComboBox, enabled if not coming from a database (SQlite, GPKG, PG)
    Fields = 'Fields'  # QListWidget then ListFieldsSelection, a custom widget in qgis_plugin_tools
    File = 'File'  # QgsFileWidget
    HtmlWysiwyg = 'HtmlWysiwyg'  # Own Lizmap Wysiwyg widget
    Json = 'Json'  # QTextEdit then JsonEditor, a custom widget in qgis_plugin_tools
    Layer = 'Layer'  # QgsMapLayerComboBox
    Layers = 'Layers'  # ListLayersSelection
    List = 'List'  # QComboBox with multiple_selection=False (by default), otherwise a QgsCheckableComboBox
    SpinBox = 'SpinBox'  # QSpinbox
    Text = 'Text'  # QLineEdit
    MultiLine = 'MultiLine'  # QPlainTextEdit or QgsCodeEditorHTML


class BaseDefinitions:

    def __init__(self):
        self._layer_config = OrderedDict()
        self._general_config = OrderedDict()
        self._use_single_row = False

    def key(self) -> str:
        raise NotImplementedError

    @property
    def help_path(self) -> str:
        """ The online help path. """
        raise NotImplementedError

    @property
    def use_single_row(self) -> bool:
        return self._use_single_row

    @property
    def layer_config(self) -> OrderedDict:
        return self._layer_config

    @property
    def general_config(self) -> OrderedDict:
        return self._general_config

    @staticmethod
    def primary_keys() -> tuple:
        return tuple()

    def add_layer_widget(self, key, widget):
        if key not in self._layer_config:
            raise Exception('Key does not exist in layer config')
        self._layer_config[key]['widget'] = widget

    def add_layer_label(self, key, widget):
        if key not in self._layer_config:
            raise Exception('Key does not exist in layer config')
        self._layer_config[key]['label'] = widget

    def add_general_widget(self, key, widget):
        if key not in self._general_config:
            raise Exception('Key does not exist in general config')
        self._general_config[key]['widget'] = widget

    def add_general_label(self, key, widget):
        if key not in self._general_config:
            raise Exception('Key does not exist in general config')
        self._general_config[key]['label'] = widget
