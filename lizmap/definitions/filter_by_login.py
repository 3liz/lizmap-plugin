"""Definitions for filter by login."""

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.definitions.definitions import LwcVersions
from lizmap.qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class FilterByLoginDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['layerId'] = {
            'type': InputType.Layer,
            'header': tr('Layer'),
            'default': None,
            'tooltip': tr('The vector layer for filtering by login.')
        }
        self._layer_config['filterAttribute'] = {
            'type': InputType.Field,
            'header': tr('Field'),
            'default': None,
            'tooltip': tr('The field to use for filtering.')
        }
        self._layer_config['filterPrivate'] = {
            'type': InputType.CheckBox,
            'header': tr('Filter by user'),
            'default': False,
            'tooltip': tr('If Lizmap should use the group or the username for filtering data.')
        }
        self._layer_config['edition_only'] = {
            'type': InputType.CheckBox,
            'header': tr('Edition only'),
            'default': False,
            'tooltip': tr('If this filter is used for edition capabilities only.'),
            'version': LwcVersions.Lizmap_3_4,
        }

    @staticmethod
    def primary_keys() -> tuple:
        return 'layerId',

    def key(self) -> str:
        return 'loginFilteredLayers'

    def help(self) -> str:
        return 'publish/lizmap_plugin/filtered_layers_login.html'
