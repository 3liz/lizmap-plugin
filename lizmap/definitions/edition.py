"""Definitions for edition."""

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.definitions.definitions import LwcVersions
from lizmap.qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


def layer_provider(layer):
    if not layer:
        return ''

    return layer.dataProvider().name()


class EditionDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['layerId'] = {
            'type': InputType.Layer,
            'header': tr('Layer'),
            'default': None,
            'tooltip': tr('The vector layer for the edition.')
        }
        self._layer_config['createFeature'] = {
            'type': InputType.CheckBox,
            'header': tr('Create'),
            'default': False,
            'tooltip': tr('If a new feature can be added.')
        }
        self._layer_config['allow_without_geom'] = {
            'type': InputType.CheckBox,
            'header': tr('Allow feature without geometry'),
            'default': False,
            'tooltip': tr('If a feature can be geometry less.'),
            'version': LwcVersions.Lizmap_3_3,
        }
        self._layer_config['modifyAttribute'] = {
            'type': InputType.CheckBox,
            'header': tr('Edit attributes'),
            'default': False,
            'tooltip': tr('If attributes can be edited.')
        }
        self._layer_config['modifyGeometry'] = {
            'type': InputType.CheckBox,
            'header': tr('Edit geometry'),
            'default': False,
            'tooltip': tr('If geometry can be edited.')
        }
        self._layer_config['deleteFeature'] = {
            'type': InputType.CheckBox,
            'header': tr('Remove'),
            'default': False,
            'tooltip': tr('If a feature can be removed.')
        }
        self._layer_config['acl'] = {
            'type': InputType.Text,
            'header': tr('Groups'),
            'default': '',
            'tooltip': tr(
                'Use a comma separated list of Lizmap groups ids to restrict access '
                'to this layer edition.')
        }
        self._layer_config['snap_layers'] = {
            'type': InputType.Layers,
            'header': tr('Layers'),
            'default': '',
            'tooltip': tr('List of layers to snap on.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['snap_vertices'] = {
            'type': InputType.CheckBox,
            'header': tr('Node'),
            'default': False,
            'tooltip': tr('If we should snap on vertices.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['snap_segments'] = {
            'type': InputType.CheckBox,
            'header': tr('Segments'),
            'default': False,
            'tooltip': tr('If we should snap on segments.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['snap_intersections'] = {
            'type': InputType.CheckBox,
            'header': tr('Intersections'),
            'default': False,
            'tooltip': tr('If we should snap on intersections.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['snap_vertices_tolerance'] = {
            'type': InputType.SpinBox,
            'header': tr('Vertices tolerance'),
            'default': 10,
            'unit': ' px',
            'tooltip': tr('Snapping tolerance for vertices.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['snap_segments_tolerance'] = {
            'type': InputType.SpinBox,
            'header': tr('Segments tolerance'),
            'default': 10,
            'unit': ' px',
            'tooltip': tr('Snapping tolerance for segments.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['snap_intersections_tolerance'] = {
            'type': InputType.SpinBox,
            'header': tr('Intersections tolerance'),
            'default': 10,
            'unit': ' px',
            'tooltip': tr('Snapping tolerance for intersections.'),
            'version': LwcVersions.Lizmap_3_4,
        }
        self._layer_config['provider'] = {
            'type': InputType.Text,
            'read_only': True,
            'default': layer_provider,
            'header': tr('Provider name'),
            'tooltip': tr('Provider name, read only field.'),
            'version': LwcVersions.Lizmap_3_3,
            'visible': False,
        }

    @staticmethod
    def primary_keys() -> tuple:
        return 'layerId',

    def key(self) -> str:
        return 'editionLayers'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/editing.html'
