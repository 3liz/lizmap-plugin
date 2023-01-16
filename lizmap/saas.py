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
    QgsVectorLayer,
)

from lizmap.qgis_plugin_tools.tools.i18n import tr


def is_lizmap_dot_com_hosting(metadata: dict) -> bool:
    """ Return True if the metadata is coming from lizmap.com. """
    return metadata.get('hosting', '') == 'lizmap.com'


def valid_saas_lizmap_dot_com(project: QgsProject) -> Tuple[bool, Dict[str, str]]:
    """ Check the project when it's hosted on Lizmap.com hosting. """
    project_home = Path(project.homePath())
    layer_error: Dict[str, str] = {}

    for layer in project.mapLayers().values():
        if isinstance(layer, QgsVectorLayer):
            if layer.dataProvider().name() == "postgres":
                datasource = QgsDataSourceUri(layer.source())
                if datasource.authConfigId() != '':
                    layer_error[layer.name()] = tr(
                        'The layer "{}" is using the QGIS authentication database. You must either use a PostgreSQL '
                        'service or store the login and password in the layer.').format(layer.name())

                if datasource.service():
                    # We trust the user about login, password etc ...
                    continue

                # Users might be hosted on lizmap.com but using an external database
                if datasource.host().endswith("lizmap.com"):
                    if not datasource.username() or not datasource.password():
                        layer_error[layer.name()] = tr(
                            'The layer "{}" is missing credentials, either user and/or password.'
                        ).format(layer.name())

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

    return len(layer_error) != 0, layer_error
