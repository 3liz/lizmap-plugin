"""Definitions for locate by layer."""

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class LocateByLayerDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['layerId'] = {
            'type': InputType.Layer,
            'header': tr('Layer'),
            'default': None,
            'tooltip': tr('The vector layer for the locate by layer.')
        }
        self._layer_config['fieldName'] = {
            'type': InputType.Field,
            'header': tr('Display field'),
            'default': None,
            'tooltip': tr('The field to display.')
        }
        self._layer_config['filterFieldName'] = {
            'type': InputType.Field,
            'header': tr('Optional group by field'),
            'default': '',
            'tooltip': tr(
                'A field describing the upper level to regroup these features. '
                'This will display another combobox on top to make some filtering.')
        }
        self._layer_config['displayGeom'] = {
            'type': InputType.CheckBox,
            'header': tr('Display the geometry'),
            'default': False,
            'tooltip': tr('If Lizmap must highlight the geometry after one result is selected.')
        }
        self._layer_config['minLength'] = {
            'type': InputType.SpinBox,
            'header': tr('Number of characters before autocompletion'),
            'default': 0,
            'tooltip': tr(
                'If you set a value above 0, autocompletion will be used after this amount of characters while the '
                'user types. The classical combobox will be replaced by a editable text input.')
        }
        self._layer_config['filterOnLocate'] = {
            'type': InputType.CheckBox,
            'header': tr('Filter layer on zoom'),
            'default': False,
            'tooltip': tr(
                'If the layer is published via the attribute layers tool below, and this checkbox is checked, '
                'zooming on a feature with the locate tool will trigger the filter of the layer for the selected '
                'feature. Only the selected feature will be visible on the map.')
        }

    @staticmethod
    def primary_keys() -> tuple:
        return 'layerId',

    def key(self) -> str:
        return 'locateByLayer'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/locate_by_layer.html'
