__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from typing import Union

from qgis.core import Qgis
from qgis.PyQt.QtCore import QRegularExpression
from qgis.server import QgsServerOgcApi, QgsServerOgcApiHandler

try:
    # Py-QGIS-Server
    from pyqgisserver.plugins import plugin_list, plugin_metadata
    IS_PY_QGIS_SERVER = True
except ImportError:
    # FCGI and others
    from qgis.utils import pluginMetadata, server_active_plugins
    IS_PY_QGIS_SERVER = False

    def plugin_list() -> list:
        """ To match Py-QGIS-Server API."""
        return server_active_plugins

from lizmap.server.tools import to_bool


def plugin_version(name: str) -> str:
    """ Return the version for a given plugin. """
    if IS_PY_QGIS_SERVER:
        return plugin_metadata(name)['version']
    else:
        return pluginMetadata(name, 'version')


class ServerInfoHandler(QgsServerOgcApiHandler):

    def path(self):
        return QRegularExpression("server.json")

    def summary(self):
        return "Server information"

    def description(self):
        return "Get info about the current QGIS server"

    def operationId(self):
        return "server"

    def linkTitle(self):
        return "Handler Lizmap API server info"

    def linkType(self):
        return QgsServerOgcApi.data

    def handleRequest(self, context):
        plugins = dict()
        for plugin in plugin_list():
            plugins[plugin] = dict()
            plugins[plugin]['version'] = plugin_version(plugin)

        # expected = (
        #     'wfsOutputExtension',
        #     'cadastre',
        #     'lizmap',
        #     'atlasprint',
        #     # 'tilesForServer', waiting a little for this one
        # )

        qgis_version_split = Qgis.QGIS_VERSION.split('-')

        services_available = []
        expected_services = ('WMS', 'WFS', 'WCS', 'WMTS', 'ATLAS', 'CADASTRE', 'EXPRESSION', 'LIZMAP')
        for service in expected_services:
            if context.serverInterface().serviceRegistry().getService(service):
                services_available.append(service)

        data = {
            'qgis_server': {
                'metadata': {
                    'version': qgis_version_split[0],  # 3.16.0
                    'name': qgis_version_split[1],  # Hannover
                    'version_int': Qgis.QGIS_VERSION_INT,  # 31600
                    'py_qgis_server': IS_PY_QGIS_SERVER,  # bool
                },
                # 'support_custom_headers': self.support_custom_headers(),
                'services': services_available,
                'plugins': plugins,
            },
        }
        self.write(data, context)

    def support_custom_headers(self) -> Union[None, bool]:
        """ Check if this QGIS Server supports custom headers.

         Returns None if the check is not requested with the GET parameter CHECK_CUSTOM_HEADERS

         If requested, returns boolean if X-Check-Custom-Headers is found in headers.
         """
        handler = self.serverIface().requestHandler()

        params = handler.parameterMap()
        if not to_bool(params.get('CHECK_CUSTOM_HEADERS')):
            return None

        headers = handler.requestHeaders()
        return headers.get('X-Check-Custom-Headers') is not None

    def parameters(self, context):
        from qgis.server import QgsServerQueryStringParameter
        return [
            QgsServerQueryStringParameter(
                "CHECK_CUSTOM_HEADERS",
                False,
                QgsServerQueryStringParameter.Type.String,
                "If we check custom headers"
            ),
        ]
