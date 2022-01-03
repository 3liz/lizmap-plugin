__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import os

from qgis.core import Qgis
from qgis.server import QgsServerInterface, QgsServerOgcApi

from lizmap.server.expression_service import ExpressionService
from lizmap.server.get_feature_info import GetFeatureInfoFilter
from lizmap.server.lizmap_accesscontrol import LizmapAccessControlFilter
from lizmap.server.lizmap_filter import LizmapFilter
from lizmap.server.lizmap_service import LizmapService
from lizmap.server.logger import Logger
from lizmap.server.tools import to_bool, version

if Qgis.QGIS_VERSION_INT >= 31000:
    from lizmap.server.server_info_handler import ServerInfoHandler


class LizmapServer:
    """Plugin for QGIS server
    this plugin loads Lizmap filter"""

    def __init__(self, server_iface: QgsServerInterface) -> None:
        self.server_iface = server_iface
        self.logger = Logger()
        self.version = version()
        self.logger.info('Init server version "{}"'.format(self.version))

        service_registry = server_iface.serviceRegistry()

        # Register API
        if Qgis.QGIS_VERSION_INT < 31000:
            self.logger.warning(
                'Not possible to register the API needed for Lizmap Web Client ≥ 3.5. '
                'QGIS Server/Desktop must be 3.10 minimum.')
        else:
            variable = 'QGIS_SERVER_LIZMAP_REVEAL_SETTINGS'
            if not to_bool(os.environ.get(variable, ''), default_value=False):
                self.logger.warning(
                    'Please read the documentation how to enable the Lizmap API on QGIS server side '
                    'https://docs.lizmap.com/3.5/en/install/pre_requirements.html#lizmap-server-plugin '
                    'An environment variable must be enabled to have Lizmap Web Client ≥ 3.5.'
                )
            else:
                lizmap_api = QgsServerOgcApi(
                    self.server_iface,
                    '/lizmap',
                    'Lizmap',
                    'The Lizmap API endpoint',
                    self.version)
                service_registry.registerApi(lizmap_api)
                lizmap_api.registerHandler(ServerInfoHandler())
                self.logger.info('API "/lizmap" loaded with the server info handler')

        # Register service
        try:
            service_registry.registerService(ExpressionService())
        except Exception as e:
            self.logger.critical('Error loading service "expression" : {}'.format(e))
            raise
        self.logger.info('Service "expression" loaded')

        try:
            service_registry.registerService(LizmapService(self.server_iface))
        except Exception as e:
            self.logger.critical('Error loading service "lizmap" : {}'.format(e))
            raise
        self.logger.info('Service "lizmap" loaded')

        try:
            server_iface.registerFilter(LizmapFilter(self.server_iface), 50)
        except Exception as e:
            self.logger.critical('Error loading filter "lizmap" : {}'.format(e))
            raise
        self.logger.info('Filter "lizmap" loaded')

        try:
            server_iface.registerAccessControl(LizmapAccessControlFilter(self.server_iface), 100)
        except Exception as e:
            self.logger.critical('Error loading access control "lizmap" : {}'.format(e))
            raise
        self.logger.info('Access control "lizmap" loaded')

        try:
            server_iface.registerFilter(GetFeatureInfoFilter(self.server_iface), 150)
        except Exception as e:
            self.logger.critical('Error loading filter "get feature info" : {}'.format(e))
            raise
        self.logger.info('Filter "get feature info" loaded')
