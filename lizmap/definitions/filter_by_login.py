"""Definitions for filter by login."""
from enum import Enum, unique

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.filter_by_polygon import FilterLogin
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import resources_path

__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


@unique
class SingleOrMultipleValues(Enum):
    Multiple = {
        'data': True,
        'label': tr('comma separated list'),
        'icon': resources_path('icons', 'user_group.svg'),
        'tooltip': tr('The field can contain a list of values separated by a comma.')
    }
    Single = {
        'data': False,
        'label': tr('single value'),
        'icon': resources_path('icons', 'user.svg'),
        'tooltip': tr('The field can contain a single value.')
    }


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
            'type': InputType.CheckBoxAsDropdown,
            'header': tr('Filter by'),
            'items': FilterLogin,
            'default': FilterLogin.Group,
            'tooltip': tr(
                "If the filtering is done either using users or groups. It's a comma separated list of values."),
        }
        self._layer_config['edition_only'] = {
            'type': InputType.CheckBox,
            'header': tr('Edition only'),
            'default': False,
            'tooltip': tr('If this filter is used for edition capabilities only.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['allow_multiple_acl_values'] = {
            'type': InputType.CheckBoxAsDropdown,
            'header': tr('Allow multiple values'),
            'items': SingleOrMultipleValues,
            'default': SingleOrMultipleValues.Single.value['data'],
            'tooltip': tr(
                'If multiple values is allowed in the attribute table. '
                'The multiple option is available only for PostgreSQL layer.'
            ),
            'version': LwcVersions.Lizmap_3_8,
            'use_json': True,
        }

    @staticmethod
    def primary_keys() -> tuple:
        return 'layerId',

    def key(self) -> str:
        return 'loginFilteredLayers'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/filtered_layers_login.html'
