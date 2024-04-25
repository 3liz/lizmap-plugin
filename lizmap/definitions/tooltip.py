"""Definitions for tooltip."""

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.definitions.definitions import LwcVersions
from lizmap.toolbelt.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class ToolTipDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['layerId'] = {
            'type': InputType.Layer,
            'wfs_required': True,
            'header': tr('Layer'),
            'default': None,
            'tooltip': tr('The vector layer for the tooltip.')
        }
        self._layer_config['fields'] = {
            'type': InputType.Fields,
            'wfs_required': True,
            'header': tr('Fields'),
            'default': '',  # Since LWC 3.8, it's not mandatory anymore, because it can be an HTML template
            'tooltip': tr('Fields to display in the tooltip.')
        }
        self._layer_config['template'] = {
            'type': InputType.HtmlWysiwyg,
            'header': tr('Template'),
            'default': '',
            'tooltip': tr('The HTML template to use. It can contain some QGIS expressions.'),
            'version': LwcVersions.Lizmap_3_8,
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
