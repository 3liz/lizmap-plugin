"""Tools for layers."""

from qgis.core import QgsProject, QgsLayerTreeUtils

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


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
