import re

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from os.path import relpath
from pathlib import Path
from typing import Dict, List, Tuple

from qgis.core import (
    QgsDataSourceUri,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
)

from lizmap.project_checker_tools import is_vector_pg, update_uri
from lizmap.qgis_plugin_tools.tools.i18n import tr

edit_connection_title = tr("You must edit the database connection.")
edit_connection = tr(
    "If you use a login/password, these ones must be saved by default without the QGIS authentication "
    "database. You should check in the 'Configurations' tab that there isn't "
    "any previous authentication configuration set, with SSL mode 'required' (or 'preferred' at least)."
)
right_click_step = tr(
    "To make effect in the current project for already loaded layers, for each layer, you must right click in the "
    "legend and click 'Change datasource' to pick the layer again with the updated connection."
)

SAAS_DOMAIN = 'lizmap.com'
SAAS_NAME = 'Lizmap Cloud'


def is_lizmap_cloud(metadata: dict) -> bool:
    """ Return True if the metadata is coming from Lizmap Cloud. """
    if not metadata:
        # Mainly in tests?
        return False

    return metadata.get('hosting', '') == SAAS_DOMAIN


def valid_lizmap_cloud(project: QgsProject) -> Tuple[Dict[str, str], str]:
    """ Check the project when it's hosted on Lizmap Cloud. """
    # Do not use homePath, it's not designed for this if the user has set a custom home path
    project_home = Path(project.absolutePath())
    layer_error: Dict[str, str] = {}

    connection_error = False
    for layer in project.mapLayers().values():

        if isinstance(layer, QgsRasterLayer):
            if layer.source().lower().endswith('ecw'):
                layer_error[layer.name()] = tr(
                    'The layer "{}" is an ECW. Because of the ECW\'s licence, this format is not compatible with QGIS '
                    'server. You should switch to a COG format.').format(layer.name())

        if is_vector_pg(layer):
            datasource = QgsDataSourceUri(layer.source())
            if datasource.authConfigId() != '':
                layer_error[layer.name()] = tr(
                    'The layer "{}" is using the QGIS authentication database. You must either use a PostgreSQL '
                    'service or store the login and password in the layer.').format(layer.name())
                connection_error = True

            if datasource.service():
                # We trust the user about login, password etc ...
                continue

            # Users might be hosted on Lizmap Cloud but using an external database
            if datasource.host().endswith(SAAS_DOMAIN):
                if not datasource.username() or not datasource.password():
                    layer_error[layer.name()] = tr(
                        'The layer "{}" is missing some credentials. Either the user and/or the password is not in '
                        'the layer datasource.'
                    ).format(layer.name())
                    connection_error = True

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
            layer_error[layer.name()] = tr(
                'The layer "{}" can not be hosted on {} because the layer is hosted on a different drive.'
            ).format(layer.name(), SAAS_NAME)
            continue

        if '../../..' in relative_path:
            # The layer can only be hosted the in "/qgis" directory
            layer_error[layer.name()] = tr(
                'The layer "{}" can not be hosted on {} because the layer is located in too many '
                'parent\'s folder. The current path from the project home path to the given layer is "{}".'
            ).format(layer.name(), SAAS_NAME, relative_path)

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


def check_project_ssl_postgis(project: QgsProject) -> Tuple[List[str], str]:
    """ Check if the project is not using SSL on some PostGIS layers which are on a Lizmap Cloud database. """
    layer_error: List[str] = []
    for layer in project.mapLayers().values():
        if not is_vector_pg(layer):
            continue

        datasource = QgsDataSourceUri(layer.source())

        if datasource.service():
            # Not sure what to do for now.
            # Is QGIS using the SSL in the layer configuration ?
            # We are not sure about which host the layer is using, maybe not Lizmap Cloud
            continue

        # Users might be hosted on Lizmap Cloud but using an external database
        if not datasource.host().endswith(SAAS_DOMAIN):
            continue

        if datasource.sslMode() in (QgsDataSourceUri.SslMode.SslDisable, QgsDataSourceUri.SslMode.SslAllow):
            layer_error.append(layer.name())

    more = edit_connection_title + " "
    more += edit_connection + " "
    more += '<br>'
    more += right_click_step + " "
    more += tr("This right-click step in the legend is not required if use the button to fix the project.") + " "
    return layer_error, more


def fix_ssl(project: QgsProject, force: bool = True) -> int:
    """ Fix PostgreSQL layers about SSL. """
    count = 0
    for layer in project.mapLayers().values():
        if not is_vector_pg(layer):
            continue

        datasource = QgsDataSourceUri(layer.source())
        if datasource.service():
            continue

        if not datasource.host().endswith(SAAS_DOMAIN):
            continue

        if datasource.sslMode() in (QgsDataSourceUri.SslPrefer, QgsDataSourceUri.SslMode.SslRequire):
            continue

        new_uri = _update_ssl(datasource, QgsDataSourceUri.SslPrefer, force=force)
        update_uri(layer, new_uri)
        count += 1

    return count


def _update_ssl(
        uri: QgsDataSourceUri,
        mode: QgsDataSourceUri.SslMode = QgsDataSourceUri.SslPrefer,
        force: bool = False,
        ) -> QgsDataSourceUri:
    """ Update SSL connection for a given URI. """
    current_ssl = QgsDataSourceUri.encodeSslMode(uri.sslMode())
    replaced = re.sub(
        r"sslmode=({})".format(current_ssl),
        "sslmode={}".format(QgsDataSourceUri.encodeSslMode(mode)),
        uri.uri(True))

    if force and "sslmode" not in replaced:
        replaced = 'sslmode={} {}'.format(QgsDataSourceUri.encodeSslMode(mode), replaced)

    return QgsDataSourceUri(replaced)
