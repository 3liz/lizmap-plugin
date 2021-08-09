__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import os

from qgis.server import QgsServerInterface

from lizmap.server.expression_service import ExpressionService
from lizmap.server.get_feature_info import GetFeatureInfoFilter
from lizmap.server.lizmap_accesscontrol import LizmapAccessControlFilter
from lizmap.server.lizmap_filter import LizmapFilter
from lizmap.server.lizmap_service import LizmapService
from lizmap.server.logger import Logger


class LizmapServer:
    """Plugin for QGIS server
    this plugin loads Lizmap filter"""

    def __init__(self, server_iface: 'QgsServerInterface') -> None:
        self.server_iface = server_iface
        self.logger = Logger()
        self.logger.info('Init server')

        # debug
        debug = os.getenv('QGIS_SERVER_LIZMAP_DEBUG', '').lower() in ('1', 'yes', 'y', 'true')

        # Register service
        reg = server_iface.serviceRegistry()
        try:
            reg.registerService(ExpressionService(debug=debug))
        except Exception as e:
            self.logger.critical('Error loading service "expression" : {}'.format(e))
            raise

        try:
            reg.registerService(LizmapService(self.server_iface, debug=debug))
        except Exception as e:
            self.logger.critical('Error loading service "lizmap" : {}'.format(e))
            raise

        # Register filter
        try:
            server_iface.registerFilter(LizmapFilter(self.server_iface), 50)
        except Exception as e:
            self.logger.critical('Error loading filter "lizmap" : {}'.format(e))
            raise

        # Register access control
        try:
            server_iface.registerAccessControl(LizmapAccessControlFilter(self.server_iface), 100)
        except Exception as e:
            self.logger.critical('Error loading access control "lizmap" : {}'.format(e))
            raise

        try:
            server_iface.registerFilter(GetFeatureInfoFilter(self.server_iface), 150)
        except Exception as e:
            self.logger.critical('Error loading filter "get feature info" : {}'.format(e))
            raise
