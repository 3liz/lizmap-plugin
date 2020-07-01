import os
import json
import traceback

from qgis.core import Qgis, QgsMessageLog
from qgis.server import QgsServerInterface, QgsServerException, QgsServerFilter

from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtXml import QDomDocument


class LizmapFilterException(QgsServerException):

    def __init__(self, code: str, message: str, locator: str = '', responseCode: int = 500, version: str = '1.3.0') -> None:
        super(QgsServerException, self).__init__(message, responseCode)
        self.code = code
        self.message = message
        self.locator = locator
        self.responseCode = responseCode
        self.version = version

    def formatResponse(self) -> (QByteArray, str):
        doc = QDomDocument()
        root = doc.createElement('ServiceExceptionReport')
        root.setAttribute('version', self.version)
        root.setAttribute('xmlns', 'http://www.opengis.net/ogc')
        doc.appendChild(root)

        elem = doc.createElement('ServiceException')
        elem.setAttribute('code', self.code)
        elem.appendChild(doc.createTextNode(self.message))
        root.appendChild(elem)

        if self.locator:
            elem.setAttribute('locator', self.locator)

        return doc.toByteArray(), 'text/xml; charset=utf-8'


class LizmapFilter(QgsServerFilter):

    def __init__(self, server_iface: 'QgsServerInterface') -> None:
        QgsMessageLog.logMessage('LizmapFilter.init', 'lizmap', Qgis.Info)
        super(LizmapFilter, self).__init__(server_iface)

        self.iface = server_iface

    def requestReady(self):
        try:
            config_path = self.iface.configFilePath()
            if not os.path.exists(config_path):
                return

            config_path += '.cfg'
            if not os.path.exists(config_path):
                return

            cfg = None
            with open(config_path, 'r') as cfg_file:
                try:
                    cfg = json.loads(cfg_file.read())
                except Exception:
                    return

            if not cfg:
                return

            cfg_options = cfg['options']
            if 'acl' not in cfg_options or not cfg_options['acl']:
                return

            cfg_acl = cfg_options['acl']

            handler = self.iface.requestHandler()
            headers = handler.requestHeaders()
            if not headers:
                QgsMessageLog.logMessage("No headers provided", "lizmap", Qgis.Critical)
                return

            groups = headers.get('X-Lizmap-User-Groups').split(',')
            groups = [g.strip() for g in groups]
            for g in groups:
                if g in cfg_acl:
                    return

            exc = LizmapFilterException('Forbidden', 'No ACL permissions', responseCode=403)
            # use setServiceException to be sure to stop the request
            handler.setServiceException(exc)

        except Exception:
            QgsMessageLog.logMessage("Unhandled exception:\n{}".format(traceback.format_exc()), "lizmap", Qgis.Critical)
