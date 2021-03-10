__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json

from typing import Union

from qgis.core import Qgis
from qgis.server import QgsServerApi
from qgis.utils import pluginMetadata, server_active_plugins

from lizmap.server.core import to_bool


class LizmapApi(QgsServerApi):

    def name(self):
        return "Lizmap end point"

    def rootPath(self):
        return "/lizmap/server.json"

    def executeRequest(self, request_context):
        response = request_context.response()
        response.setHeader('Content-Type', 'application/json')

        plugins = dict()
        for plugin in server_active_plugins:
            plugins[plugin] = dict()
            plugins[plugin]['version'] = pluginMetadata(plugin, 'version')

        qgis_version_split = Qgis.QGIS_VERSION.split('-')

        services_available = []
        services = ('WMS', 'WFS', 'WCS', 'WMTS', 'ATLAS', 'CADASTRE', 'EXPRESSION', 'LIZMAP')
        for service in services:
            if self.serverIface().serviceRegistry().getService(service):
                services_available.append(service)

        data = {
            'qgis_server': {
                'metadata': {
                    'version': qgis_version_split[0],  # 3.16.0
                    'name': qgis_version_split[1],  # Hannover
                    'version_int': Qgis.QGIS_VERSION_INT,  # 31600
                },
                'support_custom_headers': self.support_custom_headers(),
                'services': services_available,
                'plugins': plugins,
            },
        }
        response.write(json.dumps(data))

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
