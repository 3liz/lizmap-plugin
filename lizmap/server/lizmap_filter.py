import os
import json
import traceback

from qgis.core import Qgis, QgsMessageLog
from qgis.server import QgsServerInterface, QgsServerException, QgsServerFilter

from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtXml import QDomDocument

from typing import List


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
        super().__init__(server_iface)

        self.iface = server_iface

    def requestReady(self):
        try:
            # Get QGIS Project path
            config_path = self.iface.configFilePath()
            if not os.path.exists(config_path):
                # QGIS Project path does not exist as a file
                # The request can be evaluated by QGIS Server
                return

            # Get Lizmap config path
            config_path += '.cfg'
            if not os.path.exists(config_path):
                # Lizmap config path does not exist
                QgsMessageLog.logMessage("Lizmap config does not exist", "lizmap", Qgis.Info)
                # The request can be evaluated by QGIS Server
                return

            # Get Lizmap user groups defined in request headers
            groups = self.getLizmapGroups()

            # If groups is empty, no Lizmap user groups provided by the request
            # The request can be evaluated by QGIS Server
            if len(groups) == 0:
                return

            # Get Lizmap config
            cfg = None
            with open(config_path, 'r') as cfg_file:
                try:
                    cfg = json.loads(cfg_file.read())
                except Exception:
                    # Lizmap config is not a valid JSON file
                    QgsMessageLog.logMessage("Lizmap config not well formed", "lizmap", Qgis.Error)
                    # The request can be evaluated by QGIS Server
                    return

            if not cfg:
                # Lizmap config is empty
                QgsMessageLog.logMessage("Lizmap config is empty", "lizmap", Qgis.Warning)
                # The request can be evaluated by QGIS Server
                return

            # Check Lizmap config options
            if 'options' not in cfg or not cfg['options']:
                # Lizmap config has no options
                QgsMessageLog.logMessage("Lizmap config has no options", "lizmap", Qgis.Warning)
                # The request can be evaluated by QGIS Server
                return

            # Check project acl option
            cfg_options = cfg['options']
            if 'acl' not in cfg_options or not cfg_options['acl']:
                # No acl defined
                QgsMessageLog.logMessage("No acl defined in Lizmap config", "lizmap", Qgis.Info)
                # The request can be evaluated by QGIS Server
                return

            # Get project acl option
            cfg_acl = cfg_options['acl']
            QgsMessageLog.logMessage("Acl defined in Lizmap config", "lizmap", Qgis.Info)
            cfg_acl = [g.strip() for g in cfg_acl.split(',')]

            # If one Lizmap user group provided in request headers is
            # defined in project acl option, the request can be evaluated
            # by QGIS Server
            for g in groups:
                if g in cfg_acl:
                    return

            # The lizmap user groups provided in request header are not
            # authorized to get access to the QGIS Project
            exc = LizmapFilterException('Forbidden', 'No ACL permissions', responseCode=403)

            # Get request handler
            handler = self.iface.requestHandler()
            # use setServiceException to be sure to stop the request
            handler.setServiceException(exc)

        except Exception:
            QgsMessageLog.logMessage("Unhandled exception:\n%s" % traceback.format_exc(), "lizmap", Qgis.Critical)

    def getLizmapGroups(self) -> 'List[str]':
        """ Get Lizmap user groups provided by the request """
        # Defined groups
        groups = []

        # Get request handler
        handler = self.iface.requestHandler()

        # Get Lizmap User Groups in request headers
        headers = handler.requestHeaders()
        if headers:
            QgsMessageLog.logMessage("Request headers provided", "lizmap", Qgis.Info)
            # Get Lizmap user groups defined in request headers
            userGroups = headers.get('X-Lizmap-User-Groups')
            if userGroups is not None:
                groups = [g.strip() for g in userGroups.split(',')]
                QgsMessageLog.logMessage("Lizmap user groups in request headers", "lizmap", Qgis.Info)
        else:
            QgsMessageLog.logMessage("No request headers provided", "lizmap", Qgis.Info)

        if len(groups) != 0:
            return groups
        else:
            QgsMessageLog.logMessage("No lizmap user groups in request headers", "lizmap", Qgis.Info)

        # Get group in parameters
        params = handler.parameterMap()
        if params:
            # Get Lizmap user groups defined in parameters
            userGroups = params.get('LIZMAP_USER_GROUPS')
            if userGroups is not None:
                groups = [g.strip() for g in userGroups.split(',')]
                QgsMessageLog.logMessage("Lizmap user groups in parameters", "lizmap", Qgis.Info)

        return groups
