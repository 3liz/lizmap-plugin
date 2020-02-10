"""Definitions for time manager."""

from .base import BaseDefinitions, InputType
from ..qgis_plugin_tools.tools.i18n import tr

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TimeManagerDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()
        self._layer_config['layerId'] = {
            'type': InputType.Layer,
            'header': tr('Layer'),
            'default': None,
            'tooltip': tr('Layer with the date/time.')
        }
        self._layer_config['startAttribute'] = {
            'type': InputType.Field,
            'header': tr('Start'),
            'default': None,
            'tooltip': tr('Column with the date/time.')
        }
        self._layer_config['endAttribute'] = {
            'type': InputType.Field,
            'header': tr('End'),
            'default': '',
            'tooltip': tr('Field with the end date/time.')
        }
        self._layer_config['attributeResolution'] = {
            'type': InputType.List,
            'header': tr('Attribute resolution'),
            'default': 'years',
            'tooltip': tr('Date/time resolution of the chosen attribute(s).')
        }
        self._general_config['inTimeFrameSize'] = {
            'type': InputType.SpinBox,
            'default': 10,
        }
        self._general_config['tmTimeFrameType'] = {
            'type': InputType.List,
            'default': 'seconds',
        }
        self._general_config['tmAnimationFrameLength'] = {
            'type': InputType.SpinBox,
            'default': 1000,
        }

    @staticmethod
    def primary_keys() -> tuple:
        return 'layerId',

    def key(self) -> str:
        return 'timemanagerLayers'
