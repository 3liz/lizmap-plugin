"""Definitions for tooltip."""

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class ToolTipDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['layerId'] = {
            'type': InputType.Layer,
            'header': tr('Layer'),
            'default': None,
            'tooltip': tr('The vector layer for the tooltip.')
        }
        self._layer_config['fields'] = {
            'type': InputType.Fields,
            'header': tr('Fields'),
            'default': None,
            'tooltip': tr('Fields to display in the tooltip.')
        }
        self._layer_config['displayGeom'] = {
            'type': InputType.CheckBox,
            'header': tr('Display geometry'),
            'default': False,
            'tooltip': tr('If you want to display geometry with the tooltip.')
        }
        self._layer_config['colorGeom'] = {
            'type': InputType.Color,
            'header': tr('Color'),
            'default': '',
            'tooltip': tr('The color to use for displaying the geometry.')
        }

    @staticmethod
    def primary_keys() -> tuple:
        return 'layerId',

    def key(self) -> str:
        return 'tooltipLayers'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/tooltip.html'
