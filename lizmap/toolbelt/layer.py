__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import os
import urllib

from qgis.core import (
    QgsDataSourceUri,
    QgsLayerTreeUtils,
    QgsMapLayer,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsVectorLayer,
)

from lizmap.definitions.definitions import LayerProperties


def is_database_layer(layer) -> bool:
    """ Check if the layer is a database layer.

    It returns True for postgres, spatialite and gpkg files.
    """
    if layer.providerType() in ('postgres', 'spatialite'):
        return True

    uri = QgsProviderRegistry.instance().decodeUri('ogr', layer.source())
    extension = os.path.splitext(uri['path'])[1]
    if extension.lower() == '.gpkg':
        return True

    return False


def is_vector_pg(layer: QgsMapLayer, geometry_check=False) -> bool:
    """ Return boolean if the layer is stored in PG and is a vector with a geometry. """
    if layer.type() != QgsMapLayer.VectorLayer:
        return False

    if layer.dataProvider().name() != 'postgres':
        return False

    if not geometry_check:
        return True

    if not layer.isSpatial():
        return False

    return True


def relative_path(max_parent: int) -> str:
    """ Return the dot notation for a maximum parent folder. """
    parent = ['..'] * max_parent
    return '/'.join(parent)


def update_uri(layer: QgsMapLayer, uri: QgsDataSourceUri):
    """ Set a new datasource URI on a layer. """
    layer.setDataSource(
        uri.uri(True),
        layer.name(),
        layer.dataProvider().name(),
        layer.dataProvider().ProviderOptions()
    )


def is_ghost_layer(layer):
    """Check if the given layer is a ghost layer or not.

    A ghost layer is included in the QgsProject list of layers
    but is not present in the layer tree.

    :param layer: QgsMapLayer coming from the QgsProject.mapLayers.
    :type layer: QgsMapLayer

    :return: If the layer is ghost, IE not found in the legend layer tree.
    :rtype: bool
    """
    # noinspection PyArgumentList
    project = QgsProject.instance()
    # noinspection PyArgumentList
    count = QgsLayerTreeUtils.countMapLayerInTree(project.layerTreeRoot(), layer)
    return count == 0


def layer_wms_parameters(layer: QgsRasterLayer):
    """ WMS parameters from a WMS layer. """
    uri = layer.dataProvider().dataSourceUri()
    if 'wmts' in uri.lower():
        # Avoid WMTS layers (not supported yet in Lizmap Web Client)
        # This test is fragile as WMTS might not be in the URL
        return None

    # noinspection PyUnresolvedReferences
    wms_params = urllib.parse.parse_qs(uri)
    wms_params = {k: v[0] for k, v in wms_params.items()}
    return wms_params


def layer_property(layer: QgsVectorLayer, item_property: LayerProperties) -> str:
    if item_property == LayerProperties.DataUrl:
        return layer.dataUrl()
    else:
        raise NotImplementedError


def remove_all_ghost_layers():
    """Remove all ghost layers from project.

    :return: The list of layers name which have been removed.
    :rtype: list
    """
    # noinspection PyArgumentList
    project = QgsProject.instance()
    ghosts = []
    for layer in project.mapLayers().values():
        if is_ghost_layer(layer):
            ghosts.append(layer.name())
            project.removeMapLayer(layer.id())

    project.setDirty(True)
    return ghosts
