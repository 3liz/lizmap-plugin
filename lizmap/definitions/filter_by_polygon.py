"""Definitions for filter by polygon."""

from enum import Enum, unique

from qgis.core import QgsApplication

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


@unique
class FilterMode(Enum):
    DisplayEditing = {
        'data': 'display_and_editing',
        'label': tr('Display and editing'),
        'icon': ":images/themes/default/propertyicons/digitizing.svg",
    }
    Editing = {
        'data': 'editing',
        'label': tr('Editing only'),
        'icon': QgsApplication.iconPath("mActionToggleEditing.svg"),
    }


class FilterByPolygonDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['layer'] = {
            'type': InputType.Layer,
            'header': tr('Layer'),
            'tooltip': tr('The vector layer to filter.')
        }
        self._layer_config['primary_key'] = {
            'type': InputType.Field,
            'header': tr('Primary key'),
            'tooltip': tr('Layer primary key.')
        }
        self._layer_config['filter_mode'] = {
            'type': InputType.List,
            'header': tr('Mode'),
            'items': FilterMode,
            'default': FilterMode.DisplayEditing,
            'tooltip': tr('If the filtering should be done only for editing or not.')
        }

        self._general_config['polygon_layer_id'] = {
            'type': InputType.Layer,
            'tooltip': tr('The layer to use for filtering.'),
        }

        self._general_config['group_field'] = {
            'type': InputType.Field,
            'tooltip': tr(
                'The field containing Lizmap group names. It must be group IDs and not group labels, '
                'separated by comma.'
            ),
        }

    @staticmethod
    def primary_keys() -> tuple:
        return 'layer',

    def key(self) -> str:
        return 'filter_by_polygon'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/spatial_filtering.html'
