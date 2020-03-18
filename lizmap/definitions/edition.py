"""Definitions for edition."""

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


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

    @staticmethod
    def primary_keys() -> tuple:
        return 'layerId',

    def key(self) -> str:
        return 'editionLayers'
