__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from typing import List, Optional, Tuple

from qgis.core import (
    QgsDataSourceUri,
    QgsLayerTree,
    QgsMapLayer,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
)

from lizmap.qgis_plugin_tools.tools.i18n import tr

""" Some checks which can be done on a layer. """

# https://github.com/3liz/lizmap-web-client/issues/3692


def auto_generated_primary_key_field(layer: QgsVectorLayer) -> Tuple[bool, Optional[str]]:
    """ If the primary key has been detected as tid/ctid but the field does not exist. """
    # Example
    # CREATE TABLE IF NOT EXISTS public.test_tid
    # (
    #     id bigint,
    #     label text
    # )
    # In QGIS source code, look for "Primary key is ctid"

    if layer.dataProvider().uri().keyColumn() == '':
        # GeoJSON etc
        return False, None

    # QgsVectorLayer.primaryKeyAttributes is returning a list.
    if len(layer.primaryKeyAttributes()) >= 2:
        # We don't check for composite keys here
        return False, None

    if layer.dataProvider().uri().keyColumn() in layer.fields().names():
        return False, None

    # The layer has "tid" or "ctid" as a primary key, but the field is not found.
    return True, layer.dataProvider().uri().keyColumn()


def invalid_int8_primary_key(layer: QgsVectorLayer) -> bool:
    """ If the layer has a primary key as int8, alias bigint. """
    # Example
    # CREATE TABLE IF NOT EXISTS france.test_bigint
    # (
    #     id bigint PRIMARY KEY,
    #     label text
    # )
    # QgsVectorLayer.primaryKeyAttributes is returning a list.
    if len(layer.primaryKeyAttributes()) != 1:
        # We might have either no primary key,
        # or a composite primary key
        return False

    uri = QgsDataSourceUri(layer.source())
    primary_key = uri.keyColumn()
    if not primary_key:
        return False

    field_type = layer.fields().field(primary_key).typeName()
    return field_type.lower() == 'int8'


def duplicated_layer_name_or_group(project: QgsProject) -> dict:
    """ The CFG can only store layer/group names which are unique. """
    result = {}
    # Vector and raster layers
    for layer in project.mapLayers().values():
        layer: QgsMapLayer
        name = layer.name()
        if name not in result.keys():
            result[name] = 1
        else:
            result[name] += 1

    # Groups
    for child in project.layerTreeRoot().children():
        if QgsLayerTree.isGroup(child):
            name = child.name()
            if name not in result.keys():
                result[name] = 1
            else:
                result[name] += 1

    return result


def duplicated_layer_with_filter(project: QgsProject) -> Optional[str]:
    """ Check for duplicated layers with the same datasource but different filters. """
    unique_datasource = {}
    for layer in project.mapLayers().values():
        uri = QgsDataSourceUri(layer.source())
        uri_filter = uri.sql()
        if uri_filter == '':
            continue

        uri.setSql('')

        uri_string = uri.uri(True)

        if uri_string not in unique_datasource.keys():
            # First time we meet this datasource, we append
            unique_datasource[uri_string] = {}

        if uri_filter not in unique_datasource[uri_string]:
            # We add the filter with the layer name
            unique_datasource[uri_string][uri_filter] = layer.name()

    if len(unique_datasource.keys()) == 0:
        return None

    text = ''
    for datasource, filters in unique_datasource.items():
        if len(filters.values()) <= 1:
            continue

        layer_names = ','.join([f"'{k}'" for k in filters.values()])
        uri_filter = ','.join([f"'{k}'" for k in filters.keys()])
        text += tr(
            "Review layers <strong>{layers}</strong> having the same datasource '{datasource}' with these "
            "filters {uri_filter}."
        ).format(
            layers=layer_names,
            datasource=QgsDataSourceUri.removePassword(QgsDataSourceUri(datasource).uri(False)),
            uri_filter=uri_filter
        )
        text += '<br>'

    text += '<br>'
    text += tr(
        'Checkbox are supported natively in the legend. Using filters for the same '
        'datasource are highly discouraged.'
    )
    text += '<br>'
    return text


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


def simplify_provider_side(project: QgsProject, fix=False) -> List[str]:
    """ Return the list of layer name which can be simplified on the server side. """
    results = []
    for layer in project.mapLayers().values():
        if not is_vector_pg(layer, geometry_check=True):
            continue

        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            continue

        if not layer.simplifyMethod().forceLocalOptimization():
            continue

        results.append(layer.name())

        if fix:
            simplify = layer.simplifyMethod()
            simplify.setForceLocalOptimization(False)
            layer.setSimplifyMethod(simplify)

    return results


def use_estimated_metadata(project: QgsProject, fix: bool = False) -> List[str]:
    """ Return the list of layer name which can use estimated metadata. """
    results = []
    for layer in project.mapLayers().values():
        if not is_vector_pg(layer, geometry_check=True):
            continue

        uri = layer.dataProvider().uri()
        if not uri.useEstimatedMetadata():
            results.append(layer.name())

            if fix:
                uri.setUseEstimatedMetadata(True)
                update_uri(layer, uri)

    return results


def project_trust_layer_metadata(project: QgsProject, fix: bool = False) -> bool:
    """ Trust layer metadata at the project level. """
    if not fix:
        return project.trustLayerMetadata()

    project.setTrustLayerMetadata(True)
    return True


def update_uri(layer: QgsMapLayer, uri: QgsDataSourceUri):
    """ Set a new datasource URI on a layer. """
    layer.setDataSource(
        uri.uri(True),
        layer.name(),
        layer.dataProvider().name(),
        layer.dataProvider().ProviderOptions()
    )
