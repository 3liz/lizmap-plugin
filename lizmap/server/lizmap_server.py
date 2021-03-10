__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import os

from qgis.core import Qgis
from qgis.server import QgsServerInterface

from lizmap.server.expression_service import ExpressionService
from lizmap.server.get_feature_info import GetFeatureInfoFilter
from lizmap.server.lizmap_accesscontrol import LizmapAccessControlFilter
from lizmap.server.lizmap_api import LizmapApi
from lizmap.server.lizmap_filter import LizmapFilter
from lizmap.server.lizmap_service import LizmapService
from lizmap.server.logger import Logger


class LizmapServer:
    """Plugin for QGIS server
    this plugin loads Lizmap filter"""

    def __init__(self, server_iface: QgsServerInterface) -> None:
        self.server_iface = server_iface
        self.logger = Logger()
        self.logger.info('Init server')

        service_registry = server_iface.serviceRegistry()

        # Register API
        if Qgis.QGIS_VERSION_INT < 31000:
            self.logger.warning(
                'Not possible to register the API needed for Lizmap Web Client ≥ 3.6. '
                'QGIS Server/Desktop must be 3.10 minimum.')
        else:
            variable = 'QGIS_SERVER_LIZMAP_REVEAL_SETTINGS'
            if not os.environ.get(variable, '').lower() in ('1', 'yes', 'y', 'true'):
                self.logger.warning(
                    'The environment variable {} must be enabled to have Lizmap Web Client ≥ 3.6. '
                    'You must be ensure that this API is protected in your webserver, by IP address for '
                    'instance, allowing only the Lizmap PHP application.'.format(variable)
                )
            else:
                lizmap_api = LizmapApi(self.server_iface)
                service_registry.registerApi(lizmap_api)

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
