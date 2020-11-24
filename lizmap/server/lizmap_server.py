__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'

import os

from qgis.core import Qgis, QgsMessageLog
from qgis.server import QgsServerInterface

from .expression_service import ExpressionService
from .lizmap_accesscontrol import LizmapAccessControlFilter
from .lizmap_filter import LizmapFilter
from .lizmap_service import LizmapService


class LizmapServer:
    """Plugin for QGIS server
    this plugin loads Lizmap filter"""

    def __init__(self, server_iface: 'QgsServerInterface') -> None:
        self.server_iface = server_iface
        QgsMessageLog.logMessage('SUCCESS - init', 'Lizmap Server', Qgis.Info)

        # debug
        debug = os.getenv('QGIS_SERVER_LIZMAP_DEBUG', '').lower() in ('1', 'yes', 'y', 'true')

        # Register service
        try:
            reg = server_iface.serviceRegistry()
            reg.registerService(ExpressionService(debug=debug))
            reg.registerService(LizmapService(self.server_iface, debug=debug))
        except Exception as e:
            QgsMessageLog.logMessage('Error loading Service Lizmap : {}'.format(e), 'lizmap', Qgis.Critical)
            raise

        # Add filter
        try:
            server_iface.registerFilter(LizmapFilter(self.server_iface), 50)
        except Exception as e:
            QgsMessageLog.logMessage('Error loading filter lizmap : {}'.format(e), 'lizmap', Qgis.Critical)
            raise

        # Add Access Control
        try:
            server_iface.registerAccessControl(LizmapAccessControlFilter(self.server_iface), 100)
        except Exception as e:
            QgsMessageLog.logMessage('Error loading filter lizmap : {}'.format(e), 'lizmap', Qgis.Critical)
            raise
