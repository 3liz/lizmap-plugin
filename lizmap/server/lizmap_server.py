__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

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

    def __init__(self, server_iface: QgsServerInterface) -> None:
        self.server_iface = server_iface
        self.logger = Logger()
        self.logger.info('Init server')

        reg = server_iface.serviceRegistry()
        try:
            reg.registerService(ExpressionService())
        except Exception as e:
            self.logger.critical('Error loading service "expression" : {}'.format(e))
            raise
        self.logger.info('Service "expression" loaded')

        try:
            reg.registerService(LizmapService(self.server_iface))
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
