__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import QgsLayerTreeGroup, QgsProject


def is_layer_wms_excluded(project: QgsProject, name: str) -> bool:
    """ Is the layer excluded from WMS.

    Project properties → QGIS server → WMS → Exclude layers
    """
    server_wms_excluded_list, server_exclude = project.readListEntry('WMSRestrictedLayers', '')
    return server_exclude and name in server_wms_excluded_list


def is_layer_published_wfs(project: QgsProject, layer_id: str) -> bool:
    """ Is the layer in the WFS service.

    Project properties → QGIS server → WFS → Checked for the layer ID
    """
    server_wfs_included_list, server_exclude = project.readListEntry('WFSLayers', '')
    return server_exclude and layer_id in server_wfs_included_list


def empty_baselayers(project: QgsProject) -> bool:
    """ Check if the "baselayers" group is empty or not. """
    root_group = project.layerTreeRoot()
    groups = root_group.findGroups()
    for qgis_group in groups:
        qgis_group: QgsLayerTreeGroup
        if qgis_group.name() == 'baselayers':
            return len(qgis_group.children()) == 0
    return False
