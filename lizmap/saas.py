import re

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from typing import List, Optional, Tuple

from qgis.core import QgsDataSourceUri, QgsProject

from lizmap.definitions.lizmap_cloud import CLOUD_DOMAIN
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.layer import is_vector_pg, update_uri
from lizmap.widgets.check_project import SourceLayer

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


def is_lizmap_cloud(metadata: dict) -> bool:
    """ Return True if the metadata is coming from Lizmap Cloud. """
    if not metadata:
        # Mainly in tests?
        return False

    return metadata.get('hosting', '') == CLOUD_DOMAIN


def webdav_properties(metadata: dict) -> dict:
    """ Check if the server has some WebDAV capabilities. """
    if not metadata:
        return {}
    return metadata.get('webdav', {})


def webdav_url(metadata: dict) -> Optional[str]:
    """ Return the WebDAV URL according to metadata. """
    webdav = webdav_properties(metadata)
    if not webdav:
        return
    return f"{webdav['url']}/{webdav['projects_path']}"


def check_project_ssl_postgis(project: QgsProject) -> Tuple[List[SourceLayer], str]:
    """ Check if the project is not using SSL on some PostGIS layers which are on a Lizmap Cloud database. """
    layer_error: List[SourceLayer] = []
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
        if not datasource.host().endswith(CLOUD_DOMAIN):
            continue

        if datasource.sslMode() in (QgsDataSourceUri.SslMode.SslDisable, QgsDataSourceUri.SslMode.SslAllow):
            layer_error.append(SourceLayer(layer.name(), layer.id()))

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

        if not datasource.host().endswith(CLOUD_DOMAIN):
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
