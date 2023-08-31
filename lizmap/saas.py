__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from os.path import relpath
from pathlib import Path
from typing import Dict, Tuple

from qgis.core import (
    QgsDataSourceUri,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
)

from lizmap.project_checker_tools import _is_vector_pg
from lizmap.qgis_plugin_tools.tools.i18n import tr


def is_lizmap_dot_com_hosting(metadata: dict) -> bool:
    """ Return True if the metadata is coming from lizmap.com. """
    if not metadata:
        # Mainly in tests?
        return False

    return metadata.get('hosting', '') == 'lizmap.com'


def valid_saas_lizmap_dot_com(project: QgsProject) -> Tuple[bool, Dict[str, str], str]:
    """ Check the project when it's hosted on Lizmap.com hosting. """
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

        if _is_vector_pg(layer):
            datasource = QgsDataSourceUri(layer.source())
            if datasource.authConfigId() != '':
                layer_error[layer.name()] = tr(
                    'The layer "{}" is using the QGIS authentication database. You must either use a PostgreSQL '
                    'service or store the login and password in the layer.').format(layer.name())
                connection_error = True

            if datasource.service():
                # We trust the user about login, password etc ...
                continue

            # Users might be hosted on lizmap.com but using an external database
            if datasource.host().endswith("lizmap.com"):
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

        relative_path = relpath(layer_path, project_home)
        if '../../..' in relative_path:
            # The layer can only be hosted the in "/qgis" directory
            layer_error[layer.name()] = tr(
                'The layer "{}" can not be hosted on lizmap.com because the layer is located in too many '
                'parent\'s folder. The current path from the project home path to the given layer is "{}".'
            ).format(layer.name(), relative_path)

    more = ''
    if connection_error:
        more = tr("You must edit the database connection.") + " "
        more += tr(
            "If you use a login/password, these ones must be saved by default without the QGIS authentication "
            "database. You should check in the 'Configurations' tab that there isn't "
            "any previous authentication configuration set."
        ) + " "
        more += '<br>'
        more += tr(
            "Then for each layer, you must right click in the legend and click 'Change datasource' to pick the layer "
            "again with the updated connection. When opening a QGIS project in your desktop, you mustn't have any "
            "prompt for a user&password."
        )

    return len(layer_error) != 0, layer_error, more
