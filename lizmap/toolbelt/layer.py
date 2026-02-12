import os
import urllib

from qgis.core import (
    Qgis,
    QgsDataSourceUri,
    QgsLayerTreeUtils,
    QgsMapLayer,
    QgsProject,
    QgsProviderRegistry,
    QgsVectorLayer,
)

from lizmap.definitions.definitions import LayerProperties


def is_database_layer(layer: QgsMapLayer) -> bool:
    """Check if the layer is a database layer.

    It returns True for postgres, spatialite and gpkg files.
    """
    if layer.providerType() in ("postgres", "spatialite"):
        return True

    uri = QgsProviderRegistry.instance().decodeUri("ogr", layer.source())
    extension = os.path.splitext(uri["path"])[1]
    return extension.lower() == ".gpkg"


def is_vector_pg(layer: QgsMapLayer, geometry_check: bool = False) -> bool:
    """Return boolean if the layer is stored in PG and is a vector with a geometry."""
    return (
        layer.type() == QgsMapLayer.LayerType.VectorLayer
        and layer.dataProvider().name() == "postgres"
        and (not geometry_check or layer.isSpatial())
    )


def relative_path(max_parent: int) -> str:
    """Return the dot notation for a maximum parent folder."""
    parent = [".."] * max_parent
    return "/".join(parent)


def update_uri(layer: QgsMapLayer, uri: QgsDataSourceUri):
    """Set a new datasource URI on a layer."""
    layer.setDataSource(
        uri.uri(True), layer.name(), layer.dataProvider().name(), layer.dataProvider().ProviderOptions()
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


def get_layer_wms_parameters(layer):
    """
    Get WMS parameters for a raster WMS layers
    """
    uri = layer.dataProvider().dataSourceUri()
    # avoid WMTS layers (not supported yet in Lizmap Web Client)
    if "wmts" in uri or "WMTS" in uri:
        return None

    # Split WMS parameters
    wms_params = dict([*p.split("="), ""][:2] for p in uri.split("&"))

    # urldecode WMS url
    wms_params["url"] = urllib.parse.unquote(wms_params["url"]).replace("&&", "&").replace("==", "=")

    return wms_params


def layer_property(layer: QgsVectorLayer, item_property: LayerProperties) -> str:
    """ Get layer server property """
    if item_property == LayerProperties.ShortName:
        if Qgis.versionInt() < 33800:
            return layer.shortName()
        return layer.serverProperties().shortName()
    if item_property == LayerProperties.Title:
        if Qgis.versionInt() < 33800:
            return layer.title()
        return layer.serverProperties().title()
    if item_property == LayerProperties.Abstract:
        if Qgis.versionInt() < 33800:
            return layer.abstract()
        return layer.serverProperties().abstract()
    if item_property == LayerProperties.DataUrl:
        if Qgis.versionInt() < 33800:
            return layer.dataUrl()
        return layer.serverProperties().dataUrl()
    raise NotImplementedError


def set_layer_property(layer: QgsVectorLayer, item_property: LayerProperties, value: str | None):
    """ Set layer server property """
    if item_property == LayerProperties.ShortName:
        if Qgis.versionInt() < 33800:
            layer.setShortName(value)
            return
        layer.serverProperties().setShortName(value)
        return
    if item_property == LayerProperties.Title:
        if Qgis.versionInt() < 33800:
            layer.setTitle(value)
            return
        layer.serverProperties().setTitle(value)
        return
    if item_property == LayerProperties.Abstract:
        if Qgis.versionInt() < 33800:
            layer.setAbstract(value)
            return
        layer.serverProperties().setAbstract(value)
        return
    if item_property == LayerProperties.DataUrl:
        if Qgis.versionInt() < 33800:
            layer.setDataUrl(value)
            return
        layer.serverProperties().setDataUrl(value)
        return
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
