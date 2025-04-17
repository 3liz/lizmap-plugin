__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import html

from os.path import relpath
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from qgis.core import (
    QgsAbstractDatabaseProviderConnection,
    QgsDataSourceUri,
    QgsFeatureRenderer,
    QgsLayerTree,
    QgsLayerTreeNode,
    QgsMapLayer,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsVectorSimplifyMethod,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QUrlQuery

from lizmap.definitions.lizmap_cloud import CLOUD_DOMAIN
from lizmap.toolbelt.convert import cast_to_group, cast_to_layer
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.layer import is_vector_pg, update_uri
from lizmap.widgets.check_project import (
    RASTER_COUNT_CELL,
    Checks,
    Error,
    SourceGroup,
    SourceLayer,
)

""" Some checks which can be done on a layer. """

# https://github.com/3liz/lizmap-web-client/issues/3692

FORCE_LOCAL_FOLDER = tr('Prevent file based layers from being in a parent folder')
ALLOW_PARENT_FOLDER = tr('Allow file based layers to be in a parent folder')
PREVENT_OTHER_DRIVE = tr('Prevent file based layers from being stored on another drive (network or local)')
PREVENT_SERVICE = tr('Prevent PostgreSQL layers from using a service file')
PREVENT_AUTH_DB = tr('Prevent PostgreSQL layers from using the QGIS authentication database')
FORCE_PG_USER_PASS = tr(
    'PostgreSQL layers, if using a user and password, must have credentials saved in the datasource')
PREVENT_ECW = tr('Prevent from using a ECW raster')


class InvalidType:
    Int8 = 'int8'
    Varchar = 'varchar'


def project_safeguards_checks(
        project: QgsProject,
        prevent_ecw: bool,
        prevent_auth_id: bool,
        prevent_service: bool,
        force_pg_user_pass: bool,
        prevent_other_drive: bool,
        allow_parent_folder: bool,
        parent_folder: str,
        lizmap_cloud: bool,
) -> Dict:
    """ Check the project about safeguards. """
    # Do not use homePath, it's not designed for this if the user has set a custom home path
    project_home = Path(project.absolutePath())
    results = {}
    checks = Checks()

    for layer in project.mapLayers().values():

        if isinstance(layer, QgsRasterLayer):
            if layer.source().lower().endswith('ecw') and prevent_ecw:
                results[SourceLayer(layer.name(), layer.id())] = checks.PreventEcw

            if prevent_auth_id:
                if french_geopf_authcfg_url_parameters(layer.source()):
                    results[SourceLayer(layer.name(), layer.id())] = checks.FrenchGeoPlateformeUrl
                elif authcfg_url_parameters(layer.source()):
                    results[SourceLayer(layer.name(), layer.id())] = checks.RasterAuthenticationDb

        if is_vector_pg(layer):
            # Make a copy by using a string, so we are sure to have user or password
            datasource = QgsDataSourceUri(layer.source())
            if datasource.authConfigId() != '' and prevent_auth_id:
                results[SourceLayer(layer.name(), layer.id())] = checks.AuthenticationDb

                # We can continue
                continue

            if datasource.service() != '' and prevent_service:
                results[SourceLayer(layer.name(), layer.id())] = checks.PgService

                # We can continue
                continue

            if not datasource.service():
                if datasource.host().endswith(CLOUD_DOMAIN) or force_pg_user_pass:
                    if not datasource.username() or not datasource.password():
                        results[SourceLayer(layer.name(), layer.id())] = checks.PgForceUserPass

                    # We can continue
                    continue

        # Only vector/raster file based

        components = QgsProviderRegistry.instance().decodeUri(layer.dataProvider().name(), layer.source())
        if 'path' not in components.keys():
            # The layer is not file base.
            continue

        layer_path = Path(components['path'])
        try:
            if not layer_path.exists():
                # Let's skip, QGIS is already warning this layer
                # Or the file might be a COG on Linux :
                # /vsicurl/https://demo.snap.lizmap.com/lizmap_3_6/cog/...
                continue
        except OSError:
            # Ticket https://github.com/3liz/lizmap-plugin/issues/541
            # OSError: [WinError 123] La syntaxe du nom de fichier, de répertoire ou de volume est incorrecte:
            # '\\vsicurl\\https:\\XXX.lizmap.com\\YYY\\cog\\ZZZ.tif'
            continue

        try:
            relative_path = relpath(layer_path, project_home)
        except ValueError:
            # https://docs.python.org/3/library/os.path.html#os.path.relpath
            # On Windows, ValueError is raised when path and start are on different drives.
            # For instance, H: and C:

            if lizmap_cloud or prevent_other_drive:
                results[SourceLayer(layer.name(), layer.id())] = checks.PreventDrive
                continue

            # Not sure what to do for now...
            # We can't compute a relative path, but the user didn't enable the safety check, so we must still skip
            continue

        if allow_parent_folder:
            # The user allow parent folder, so we check against the string provided in the function call
            if parent_folder in relative_path:
                results[SourceLayer(layer.name(), layer.id())] = checks.PreventParentFolder
        else:
            # The user wants only local files, we only check for ".."
            if '..' in relative_path:
                results[SourceLayer(layer.name(), layer.id())] = checks.PreventParentFolder

        if isinstance(layer, QgsRasterLayer):
            # Only file based raster
            if not layer.dataProvider().hasPyramids():
                if layer.width() * layer.height() >= RASTER_COUNT_CELL:
                    results[SourceLayer(layer.name(), layer.id())] = checks.RasterWithoutPyramid

    return results


def project_invalid_pk(project: QgsProject) -> Tuple[List[SourceLayer], List[SourceLayer], List[SourceLayer]]:
    """ Check either non existing PK or bigint. """
    autogenerated_keys = []
    int8 = []
    varchar = []
    for layer in project.mapLayers().values():

        if not isinstance(layer, QgsVectorLayer):
            continue

        result, field = auto_generated_primary_key_field(layer)
        if result:
            autogenerated_keys.append(SourceLayer(layer.name(), layer.id()))

        if invalid_type_primary_key(layer, InvalidType.Int8):
            int8.append(SourceLayer(layer.name(), layer.id()))
            continue

        if invalid_type_primary_key(layer, InvalidType.Varchar):
            varchar.append(SourceLayer(layer.name(), layer.id()))
            continue

    return autogenerated_keys, int8, varchar


def project_tos_layers(project: QgsProject, google_check: bool, bing_check: bool) -> List[SourceLayer]:
    """ Check for Google or Bing layers. """
    layers = []
    for layer in project.mapLayers().values():
        datasource = layer.source().lower()
        if 'google.com' in datasource and google_check:
            layers.append(SourceLayer(layer.name(), layer.id()))
        elif 'virtualearth.net' in datasource and bing_check:
            layers.append(SourceLayer(layer.name(), layer.id()))

    return layers


def auto_generated_primary_key_field(layer: QgsVectorLayer) -> Tuple[bool, Optional[str]]:
    """ If the primary key has been detected as tid/ctid but the field does not exist. """
    # In QGIS source code, look for "Primary key is ctid"

    if layer.dataProvider().name() != 'postgres':
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


def invalid_type_primary_key(layer: QgsVectorLayer, check_field: str) -> bool:
    """ If the layer has a primary key as int8, alias bigint. """
    # QgsVectorLayer.primaryKeyAttributes is returning a list.
    if len(layer.primaryKeyAttributes()) != 1:
        # We might have either no primary key,
        # or a composite primary key
        return False

    uri = QgsDataSourceUri(layer.source())
    primary_key = uri.keyColumn()
    if not primary_key:
        return False

    if primary_key not in layer.fields().names():
        # The primary key used in the datasource doesn't exist in the proper layer fields
        # We don't check, because this test is done in "auto_generated_primary_key_field"
        return False

    field = layer.fields().field(primary_key)
    return field.typeName().lower() == check_field


def _duplicated_layer_name_or_group(layer_tree: QgsLayerTreeNode, result: Dict) -> Dict[str, int]:
    """ Recursive function to check all group names. """
    for child in layer_tree.children():
        if QgsLayerTree.isGroup(child):
            child = cast_to_group(child)
            name = child.name()
            if name not in result.keys():
                result[name] = 1
            else:
                result[name] += 1
            result = _duplicated_layer_name_or_group(child, result)
    return result


def duplicated_layer_name_or_group(project: QgsProject) -> dict:
    """ The CFG can only store layer/group names which are unique. """
    result = {}
    # For all layer within the project
    for layer in project.mapLayers().values():
        layer: QgsMapLayer
        name = layer.name()
        if name not in result.keys():
            result[name] = 1
        else:
            result[name] += 1

    # For all groups with a recursive function
    result = _duplicated_layer_name_or_group(project.layerTreeRoot(), result)
    return result


def _split_layer_uri(provider: str, source: str) -> Tuple[str, Optional[str]]:
    """ Split the base URI from the filter part. """
    uri = QgsDataSourceUri(source)
    uri_filter = uri.sql()
    uri.setSql('')
    base_uri_string = uri.uri(True)

    if not uri_filter:
        # The layer is not based on a RDBMS, try on a file
        components = QgsProviderRegistry.instance().decodeUri(provider, source)
        if components.get('path'):
            # Layers based on files
            base_uri_string = components.get('path')

        if components.get('subset'):
            uri_filter = components.get('subset')
        else:
            return base_uri_string, None

    return base_uri_string, uri_filter


def duplicated_layer_with_filter(project: QgsProject) -> Optional[Dict[str, Dict[str, str]]]:
    """ Check for duplicated layers with the same datasource but with filters. """
    # Function not used anymore, temporary replaced by the function below
    unique_datasource = {}
    for layer in project.mapLayers().values():
        base_uri, uri_filter = _split_layer_uri(layer.dataProvider().name(), layer.source())
        if not uri_filter:
            continue

        if base_uri not in unique_datasource.keys():
            # First time we meet this datasource, we append
            unique_datasource[base_uri] = {}

        if uri_filter not in unique_datasource[base_uri]:
            # We add the filter with the layer name
            unique_datasource[base_uri][uri_filter] = layer.name()

    if len(unique_datasource.keys()) == 0:
        return None

    data = {k: v for k, v in unique_datasource.items() if len(v.values()) >= 2}
    return data


def duplicated_layer_with_filter_legend(project: QgsProject) -> List:
    """ Check for duplicated layers with the same datasource but with filters when layers are next to each other. """
    root = project.layerTreeRoot()
    return _recursive_duplicated_layer_with_filter_legend(root, project)


def _recursive_duplicated_layer_with_filter_legend(
        layer_tree: QgsLayerTreeNode, project: QgsProject) -> List:
    """ Recursive function for the function above. """
    output = []
    tmp_list = {}
    previous_uri = None
    for child in layer_tree.children():
        # noinspection PyArgumentList
        if QgsLayerTree.isLayer(child):
            child = cast_to_layer(child)
            layer = project.mapLayer(child.layerId())
            if layer.customProperty("lizmap-plugin-skip-duplicated-layer") == "yes":
                # Layers from the Cadastre plugin
                continue

            # Split base uri and filter
            base_uri, uri_filter = _split_layer_uri(layer.dataProvider().name(), layer.source())

            if previous_uri and previous_uri != base_uri:
                # New layer, we reinit the temporary data
                # Need to save the current after checking values >= 2 (+1 for the symbol)
                tmp_list = {k: v for k, v in tmp_list.items() if len(v.values()) >= 3}
                if tmp_list:
                    output.append(tmp_list)
                tmp_list = {}
                previous_uri = None

            if not uri_filter:
                # Not filter, we can skip
                continue

            if not previous_uri:
                # Saving the current URI
                previous_uri = base_uri

            if base_uri not in tmp_list.keys():
                # First time we meet this datasource, we append
                tmp_list[base_uri] = {
                    '_wkb_type': layer.wkbType(),
                }

            if uri_filter not in tmp_list[base_uri]:
                # We add the filter with the layer name
                tmp_list[base_uri][uri_filter] = layer.name()

        else:
            # New group, we reinit the temporary data
            # Need to save the current after checking values >= 2 (+1 for the symbol)
            tmp_list = {k: v for k, v in tmp_list.items() if len(v.values()) >= 3}
            if tmp_list:
                output.append(tmp_list)

            tmp_list = {}
            previous_uri = None

            tmp_output = _recursive_duplicated_layer_with_filter_legend(cast_to_group(child), project)
            if tmp_output:
                output.extend(tmp_output)

    # Need to save the current after checking values >= 2 (+1 for the symbol)
    tmp_list = {k: v for k, v in tmp_list.items() if len(v.values()) >= 3}
    if tmp_list:
        output.append(tmp_list)
    return output


def simplify_provider_side(project: QgsProject, fix=False) -> List[SourceLayer]:
    """ Return the list of layer name which can be simplified on the server side. """
    results = []
    for layer in project.mapLayers().values():
        if not is_vector_pg(layer, geometry_check=True):
            continue

        if layer.geometryType() == QgsWkbTypes.GeometryType.PointGeometry:
            continue

        has_simplification = layer.simplifyMethod().simplifyHints() != QgsVectorSimplifyMethod.SimplifyHint.NoSimplification
        provider_simplification = not layer.simplifyMethod().forceLocalOptimization()
        if has_simplification and provider_simplification:
            continue

        results.append(SourceLayer(layer.name(), layer.id()))

        if fix:
            simplify = layer.simplifyMethod()
            simplify.setSimplifyHints(QgsVectorSimplifyMethod.SimplifyHint.GeometrySimplification)
            simplify.setForceLocalOptimization(False)
            layer.setSimplifyMethod(simplify)

    return results


def use_estimated_metadata(project: QgsProject, fix: bool = False) -> List[SourceLayer]:
    """ Return the list of layer name which can use estimated metadata. """
    results = []
    for layer in project.mapLayers().values():
        if not is_vector_pg(layer, geometry_check=True):
            continue

        uri = layer.dataProvider().uri()
        if not uri.useEstimatedMetadata():
            results.append(SourceLayer(layer.name(), layer.id()))

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


def count_legend_items(layer_tree: QgsLayerTreeNode, project, list_qgs: list) -> list:
    """ Count all items in the project legend. """
    for child in layer_tree.children():
        # noinspection PyArgumentList
        if QgsLayerTree.isLayer(child):
            list_qgs.append(child.name())
        else:
            child = cast_to_group(child)
            list_qgs.append(child.name())
            # Recursive call
            list_qgs = count_legend_items(child, project, list_qgs)

    return list_qgs


def trailing_layer_group_name(layer_tree: QgsLayerTreeNode, project, results: List) -> List:
    """ Check for a trailing space in layer or group name. """
    for child in layer_tree.children():
        # noinspection PyArgumentList
        if QgsLayerTree.isLayer(child):
            child = cast_to_layer(child)
            layer = project.mapLayer(child.layerId())
            if layer.name().strip() != layer.name():
                results.append(
                    Error(layer.name(), Checks().LeadingTrailingSpaceLayerGroupName, SourceLayer(layer.name(), layer.id())))
        else:
            child = cast_to_group(child)
            if child.name().strip() != child.name():
                results.append(
                    Error(child.name(), Checks().LeadingTrailingSpaceLayerGroupName, SourceGroup))

            # Recursive call
            results = trailing_layer_group_name(child, project, results)

    return results


def authcfg_url_parameters(datasource: str) -> bool:
    """ Check for authcfg in a datasource, using a plain string.

    This function is not using QgsDataSourceUri::authConfigId()
    """
    url_param = QUrlQuery(html.unescape(datasource))
    for param in url_param.queryItems():
        if param[0].lower() == 'authcfg' and param[1] != '':
            return True

    return False


def french_geopf_authcfg_url_parameters(datasource: str) -> bool:
    """ Check for authcfg in a datasource, using a plain string.

    This function is not using QgsDataSourceUri::authConfigId()
    """
    if 'data.geopf.fr' not in datasource.lower():
        return False
    # if param[0].lower().startswith("http-header:"):
    #     return True
    return authcfg_url_parameters(datasource)


def duplicated_rule_key_legend(project: QgsProject, filter_data: bool = True) -> Dict[str, Dict[str, int]]:
    """ Check for all duplicated rule keys in the legend. """
    results = {}
    for layer in project.mapLayers().values():
        if not layer.isSpatial():
            continue

        renderer = layer.renderer()
        if not renderer:
            # https://github.com/3liz/lizmap-plugin/issues/591
            # A vector layer can be spatial but having symbology disabled
            continue

        results[layer.id()] = {}

        # From QGIS source code :
        # https://github.com/qgis/QGIS/blob/71499aacf431d3ac244c9b75c3d345bdc53572fb/src/core/symbology/qgsrendererregistry.cpp#L33
        if renderer.type() in ("categorizedSymbol", "RuleRenderer", "graduatedSymbol"):

            for item in renderer.legendSymbolItems():
                if item.ruleKey() not in results[layer.id()].keys():
                    results[layer.id()][item.ruleKey()] = 1
                else:
                    results[layer.id()][item.ruleKey()] += 1

    if not filter_data:
        # For tests only
        return results

    # Keep only duplicated keys
    return _clean_result(results)


def duplicated_label_legend(project: QgsProject, filter_data: bool = True) -> Dict[str, Dict[str, int]]:
    """ Check for all duplicated labels in the legend, per layer. """
    results = {}
    for layer in project.mapLayers().values():
        if not layer.isSpatial():
            continue

        renderer = layer.renderer()

        # From QGIS source code :
        # https://github.com/qgis/QGIS/blob/71499aacf431d3ac244c9b75c3d345bdc53572fb/src/core/symbology/qgsrendererregistry.cpp#L33
        if renderer.type() in ("RuleRenderer", ):
            results[layer.id()] = _duplicated_label_legend_layer(renderer)

    if not filter_data:
        # For tests only
        return results

    # Keep only duplicated labels within a layer
    return _clean_result(results)


def _duplicated_label_legend_layer(renderer: QgsFeatureRenderer) -> Dict[str, int]:
    """ Check at the renderer level for the check above. """
    # noinspection PyUnresolvedReferences
    root_rule = renderer.rootRule()
    labels = {}
    for rule in root_rule.children():
        if rule.label() not in labels.keys():
            labels[rule.label()] = 1
        else:
            labels[rule.label()] += 1

        # Only rule based
        for sub_rule in rule.children():
            if sub_rule.label() not in labels.keys():
                labels[sub_rule.label()] = 1
            else:
                labels[sub_rule.label()] += 1

    return labels


def _clean_result(results: dict) -> dict:
    """ Remove some lines from the dictionary if the count is less than 2. """
    data = {}
    for layer_id, labels in results.items():
        data[layer_id] = {}
        for label, count in labels.items():
            if label == "":
                # In a rule based symbology, this can be an empty string
                label = tr("(empty string)")
            else:
                # Add some quotes, to see if they are some leading trailing spaces
                label = f'"{label}"'
            if count >= 2:
                data[layer_id][label] = count

        if not data[layer_id]:
            del data[layer_id]
    return data


def table_type(layer: QgsVectorLayer) -> Optional[QgsAbstractDatabaseProviderConnection.TableFlag]:
    """ Check the vector layer if it's a view. """
    uri = layer.dataProvider().uri()

    metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
    connection = metadata.createConnection(uri.uri(), {})

    sql = (
        f"SELECT relkind "
        f"FROM pg_catalog.pg_class "
        f"WHERE oid = '\"{uri.schema()}\".\"{uri.table()}\"'::regclass;"
    )

    result = connection.executeSql(sql)
    if not result:
        return None

    if result[0][0] == 'r':
        return QgsAbstractDatabaseProviderConnection.TableFlag.Vector

    if result[0][0] == 'v':
        return QgsAbstractDatabaseProviderConnection.TableFlag.View

    if result[0][0] == 'm':
        return QgsAbstractDatabaseProviderConnection.TableFlag.MaterializedView

    return None
