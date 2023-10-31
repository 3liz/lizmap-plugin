__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import QgsProject


def is_layer_wms_excluded(project: QgsProject, name: str) -> bool:
    """ Is the layer excluded from WMS.

    Project properties → QGIS server → WMS → Exclude layers
    """
    server_wms_excluded_list, server_exclude = project.readListEntry('WMSRestrictedLayers', '')
    return server_exclude and name in server_wms_excluded_list
