__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from os.path import relpath
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from qgis.core import (
    QgsDataSourceUri,
    QgsLayerTree,
    QgsMapLayer,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsWkbTypes,
)

from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.saas import (
    SAAS_DOMAIN,
    SAAS_NAME,
    edit_connection,
    edit_connection_title,
    right_click_step,
)
from lizmap.tools import is_vector_pg, update_uri

""" Some checks which can be done on a layer. """

# https://github.com/3liz/lizmap-web-client/issues/3692

FORCE_LOCAL_FOLDER = tr('Prevent file based layers to be in a parent folder')
ALLOW_PARENT_FOLDER = tr('Allow file based layers to be in a parent folder')
PREVENT_NETWORK_DRIVE = tr('Prevent file based layers to be stored on another network drive')
PREVENT_SERVICE = tr('Prevent PostgreSQL layers to use a service file')
PREVENT_AUTH_DB = tr('Prevent PostgreSQL layers to use the authentication database')
FORCE_PG_USER_PASS = tr(
    'PostgreSQL layers, if using a user and password, must have credentials saved in the datasource')
PREVENT_ECW = tr('Prevent from using a ECW raster')


def project_safeguards_checks(
        project: QgsProject,
        prevent_ecw: bool,
        prevent_auth_id: bool,
        prevent_service: bool,
        force_pg_user_pass: bool,
        prevent_network_drive: bool,
        allow_parent_folder: bool,
        parent_folder: str,
        lizmap_cloud: bool,
) -> Tuple[Dict[str, str], str]:
    """ Check the project about safeguards. """
    # Do not use homePath, it's not designed for this if the user has set a custom home path
    project_home = Path(project.absolutePath())
    layer_error: Dict[str, str] = {}

    connection_error = False
    for layer in project.mapLayers().values():

        if isinstance(layer, QgsRasterLayer):
            if layer.source().lower().endswith('ecw') and prevent_ecw:
                if lizmap_cloud:
                    layer_error[layer.name()] = tr(
                        'The layer "{}" is an ECW. Because of the ECW\'s licence, this format is not compatible with '
                        'QGIS server. You should switch to a COG format.'
                    ).format(layer.name())
                else:
                    layer_error[layer.name()] = tr(
                        'The layer "{}" is an ECW. You have activated a safeguard about preventing you using an ECW '
                        'layer. Either switch to a COG format or disable this safeguard.'
                    ).format(layer.name())

        if is_vector_pg(layer):
            # Make a copy by using a string, so we are sure to have user or password
            datasource = QgsDataSourceUri(layer.source())
            if datasource.authConfigId() != '' and prevent_auth_id:
                if lizmap_cloud:
                    layer_error[layer.name()] = tr(
                        'The layer "{}" is using the QGIS authentication database. You must either use a PostgreSQL '
                        'service or store the login and password in the layer.'
                    ).format(layer.name())
                else:
                    layer_error[layer.name()] = tr(
                        'The layer "{}" is using the QGIS authentication database. You have activated a safeguard '
                        'preventing you using the QGIS authentication database. Either switch to another '
                        'authentication mechanism or disable this safeguard.'
                    ).format(layer.name())
                connection_error = True

                # We can continue
                continue

            if datasource.service() != '' and prevent_service:
                layer_error[layer.name()] = tr(
                    'The layer "{}" is using the PostgreSQL service file. Using a service file can be recommended in '
                    'many cases, but it requires a configuration step. If you have done the configuration (on the '
                    'server side mainly), you can disable this safeguard.'
                ).format(layer.name())

                # We can continue
                continue

            if datasource.host().endswith(SAAS_DOMAIN) or force_pg_user_pass:
                if not datasource.username() or not datasource.password():
                    if lizmap_cloud:
                        layer_error[layer.name()] = tr(
                            'The layer "{}" is missing some credentials. Either the user and/or the password is not in '
                            'the layer datasource.'
                        ).format(layer.name())
                    else:
                        layer_error[layer.name()] = tr(
                            'The layer "{}" is missing some credentials. Either the user and/or the password is not in '
                            'the layer datasource, or disable the safeguard.'
                        ).format(layer.name())
                    connection_error = True

                # We can continue
                continue

        # Only vector/raster file based

        components = QgsProviderRegistry.instance().decodeUri(layer.dataProvider().name(), layer.source())
        if 'path' not in components.keys():
            # The layer is not file base.
            continue

        layer_path = Path(components['path'])
        if not layer_path.exists():
            # Let's skip, QGIS is already warning this layer
            continue

        try:
            relative_path = relpath(layer_path, project_home)
        except ValueError:
            # https://docs.python.org/3/library/os.path.html#os.path.relpath
            # On Windows, ValueError is raised when path and start are on different drives.
            # For instance, H: and C:
            # Lizmap Cloud message must be prioritized
            if lizmap_cloud:
                layer_error[layer.name()] = tr(
                    'The layer "{}" can not be hosted on {} because the layer is hosted on a different drive.'
                ).format(layer.name(), SAAS_NAME)
                continue
            elif prevent_network_drive:
                layer_error[layer.name()] = tr(
                    'The layer "{}" is on another drive. Either move this file based layer or disable this safeguard.'
                ).format(layer.name())
                continue

            # Not sure what to do for now...
            # We can't compute a relative path, but the user didn't enable the safety check, so we must still skip
            continue

        if parent_folder in relative_path and allow_parent_folder:
            if lizmap_cloud:
                # The layer can only be hosted the in "/qgis" directory
                layer_error[layer.name()] = tr(
                    'The layer "{}" can not be hosted on {} because the layer is located in too many '
                    'parent\'s folder. The current path from the project home path to the given layer is "{}".'
                ).format(layer.name(), SAAS_NAME, relative_path)
            else:
                layer_error[layer.name()] = tr(
                    'The layer "{}" is located in too many parent\'s folder. Either move this file based layer or '
                    'disable this safeguard. The current path from the project home path to the given layer is "{}".'
                ).format(layer.name(), relative_path)

    more = ''
    if connection_error:
        more = edit_connection_title + " "
        more += edit_connection + " "
        more += '<br>'
        more += right_click_step + " "
        more += tr(
            "When opening a QGIS project in your desktop, you mustn't have any "
            "prompt for a user&password."
        )

    return layer_error, more


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

    if primary_key not in layer.fields().names():
        # The primary key used in the datasource doesn't exist in the proper layer fields
        # We don't check, because this test is done in "auto_generated_primary_key_field"
        return False

    field = layer.fields().field(primary_key)
    return field.typeName().lower() == 'int8'


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
