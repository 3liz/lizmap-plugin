"""Definitions for time manager."""

from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.qgis_plugin_tools.tools.i18n import tr

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
        self._layer_config['label'] = {
            'type': InputType.Field,
            'header': tr('Hover label'),
            'default': '',
            'tooltip': tr('A field to display as a label when hovering with the mouse over the object')
        }
        self._layer_config['group'] = {
            'type': InputType.Text,
            'header': tr('Group ID'),
            'default': '',
            'tooltip': tr('Optional, an ID and a title for groups of objects.')
        }
        self._layer_config['groupTitle'] = {
            'type': InputType.Text,
            'header': tr('Group title'),
            'default': '',
            'tooltip': tr('Optional, an ID and a title for groups of objects.')
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
