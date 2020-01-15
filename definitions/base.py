"""Base class for definitions."""

from collections import OrderedDict
from enum import Enum, unique

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


@unique
class InputType(Enum):
    Layer = 'Layer'
    Field = 'Field'
    CheckBox = 'CheckBox'
    SpinBox = 'SpinBox'
    List = 'List'


class BaseDefinitions:

    def __init__(self):
        self._layer_config = OrderedDict()
        self._general_config = OrderedDict()
        self._use_single_row = False

    def key(self) -> str:
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

    def add_layer_widget(self, key, widget):
        if key not in self._layer_config:
            raise Exception('Key does not exist in layer config')
        self._layer_config[key]['widget'] = widget

    def add_layer_label(self, key, widget):
        if key not in self._layer_config:
            raise Exception('Key does not exist in layer config')
        self._layer_config[key]['label'] = widget
