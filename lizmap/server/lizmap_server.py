import os

from qgis.core import Qgis, QgsMessageLog
from qgis.server import QgsServerInterface

from .expression_service import ExpressionService
from .lizmap_service import LizmapService
from .lizmap_filter import LizmapFilter

class LizmapServer:
    """Plugin for QGIS server
    this plugin loads atlasprint filter"""

    def __init__(self, serverIface: 'QgsServerInterface') -> None:
        self.server_iface = serverIface
        QgsMessageLog.logMessage('SUCCESS - init', 'Lizmap Server', Qgis.Info)

        # debug
        debug = os.getenv('QGIS_SERVER_LIZMAP_DEBUG', '').lower() in ('1', 'yes', 'y', 'true')

        # Register service
        try:
            reg = serverIface.serviceRegistry()
            reg.registerService(ExpressionService(debug=debug))
            reg.registerService(LizmapService(self.server_iface, debug=debug))
        except Exception as e:
            QgsMessageLog.logMessage('Error loading Service Lizmap : {}'.format(e), 'lizmap', Qgis.Critical)
            raise

        # Add filter
        try:
            serverIface.registerFilter(LizmapFilter(self.server_iface), 50)
        except Exception as e:
            QgsMessageLog.logMessage('Error loading filter lizmap : {}'.format(e), 'lizmap', Qgis.Critical)
            raise

