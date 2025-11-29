"""Definitions for DXF export."""
from lizmap.definitions.base import BaseDefinitions, InputType
from lizmap.definitions.definitions import LwcVersions
from lizmap.toolbelt.i18n import tr

__copyright__ = 'Copyright 2025, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class DxfExportDefinitions(BaseDefinitions):

    def __init__(self):
        super().__init__()

        # Layer-specific configuration
        self._layer_config['layerId'] = {
            'type': InputType.Layer,
            'wfs_required': True,
            'header': tr('Layer'),
            'default': None,
            'tooltip': tr('The vector layer for DXF export. Only WFS-enabled layers can be exported to DXF.')
        }
        self._layer_config['enabled'] = {
            'type': InputType.CheckBox,
            'header': tr('Enabled'),
            'default': True,
            'tooltip': tr('If the DXF export is enabled for this layer.'),
            'version': LwcVersions.Lizmap_3_9,
            'use_json': True,
        }

        # Global configuration
        self._general_config['dxfExportEnabled'] = {
            'type': InputType.CheckBox,
            'header': tr('Allow DXF export'),
            'default': False,
            'tooltip': tr('Enable or disable the DXF export functionality globally.'),
            'version': LwcVersions.Lizmap_3_9,
        }
        self._general_config['allowedGroups'] = {
            'type': InputType.Text,
            'header': tr('Allowed groups'),
            'default': '',
            'tooltip': tr('Comma-separated list of Lizmap group IDs allowed to export DXF. If empty, all users can export.'),
            'version': LwcVersions.Lizmap_3_9,
        }

    @staticmethod
    def primary_keys() -> tuple:
        return ('layerId',)

    def key(self) -> str:
        return 'dxfExport'

    def help_path(self) -> str:
        return 'publish/lizmap_plugin/dxf_export.html'
