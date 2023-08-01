"""Definitions for filter by polygon."""

from enum import Enum, unique
from typing import Optional, Tuple

from qgis.core import (
    QgsApplication,
    QgsDataSourceUri,
    QgsProviderRegistry,
    QgsVectorLayer,
)

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from lizmap.qgis_plugin_tools.tools.resources import resources_path


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


@unique
class FilterLogin(Enum):
    Login = {
        'data': True,
        'label': tr('users'),
        'icon': resources_path('icons', 'user.svg'),
        'tooltip': tr('The field must contain a list of users separated by comma.')
    }
    Group = {
        'data': False,
        'label': tr('groups'),
        'icon': resources_path('icons', 'user_group.svg'),
        'tooltip': tr('The field must contain a list of group IDs separated by comma.')
    }


@unique
class SpatialRelationShip(Enum):
    Intersects = {
        'data': 'intersects',
        'label': tr('Intersects'),
        'icon': ":images/themes/default/mActionAllowIntersections.svg",
    }
    Contains = {
        'data': 'contains',
        'label': tr('Contains'),
        'icon': ':images/themes/default/algorithms/mAlgorithmRandomPointsWithinPolygon.svg',
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
            'type': InputType.PrimaryKeyField,
            'header': tr('Primary key'),
            'tooltip': tr('Layer primary key.')
        }
        self._layer_config['filter_mode'] = {
            'type': InputType.List,
            'header': tr('Mode'),
            'items': FilterMode,
            'default': FilterMode.DisplayEditing,
            'tooltip': tr('If the filtering should be done only for display or not.')
        }
        self._layer_config['spatial_relationship'] = {
            'type': InputType.List,
            'header': tr('Relationship'),
            'items': SpatialRelationShip,
            'default': SpatialRelationShip.Intersects,
            'tooltip': tr('The spatial relationship to use when filtering data')
        }

        self._layer_config['use_centroid'] = {
            'type': InputType.CheckBox,
            'header': tr('Centroid'),
            'default': False,
            'tooltip': tr(
                'If the tool must use the centroid of the geometry or the full geometry. It\'s quicker to use the'
                'centroid. For a PostgreSQL layer, an index on the centroid is required.'
            ),
            'use_json': True,
        }

        self._general_config['polygon_layer_id'] = {
            'type': InputType.Layer,
            'tooltip': tr('The layer to use for filtering.'),
        }

        self._general_config['group_field'] = {
            'type': InputType.Field,
            'tooltip': tr(
                'The field containing the Lizmap group names. It must be group IDs and not group labels, '
                'separated by comma.'
            ),
        }

        self._general_config['filter_by_user'] = {
            'type': InputType.CheckBoxAsDropdown,
            'items': FilterLogin,
            'default': FilterLogin.Group,
            'tooltip': tr(
                "If the filtering is done either using users or groups. It's a comma separated list of values."),
        }

    @classmethod
    def has_spatial_centroid_index(cls, layer: QgsVectorLayer) -> Tuple[bool, Optional[str]]:
        """ Check if the layer has a spatial index on the centroid. """
        datasource = QgsDataSourceUri(layer.source())

        metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
        connection = metadata.createConnection(datasource.uri(), {})
        result = connection.executeSql("""
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = '{schema}'
            AND tablename = '{table}'
            AND indexdef ILIKE '%{geom}%'
            AND indexdef ILIKE '%st_centroid%'""".format(
            schema=datasource.schema(),
            table=datasource.table(),
            geom=datasource.geometryColumn(),
            )
        )
        if len(result) >= 1:
            return True, None

        message = tr('The layer is stored in PostgreSQL and the option "Use Centroid" is used.')
        message += '\n'
        message += tr(
            'However, we could not detect a spatial index on the centroid. It\'s not possible to use the '
            'option "Use Centroid" <b>without</b> a spatial index.')
        message += '\n'
        message += tr(
            '<b>Either</b> do not use this option, <b>or</b> the following query must be executed by <b>yourself</b>')
        message += '\n'
        message += "CREATE INDEX ON \"{schema}\".\"{table}\" USING GIST (ST_Centroid({geom}));".format(
            schema=datasource.schema(),
            table=datasource.table(),
            geom=datasource.geometryColumn(),
        )
        return False, message

    @staticmethod
    def primary_keys() -> tuple:
        return 'layer',

    def key(self) -> str:
        return 'filter_by_polygon'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/filtered_layers_login.html'
