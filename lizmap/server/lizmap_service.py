__copyright__ = "Copyright 2020, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"
__revision__ = "$Format:%H$"

import traceback

from typing import Dict

from osgeo import gdal

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
)

from qgis.server import (
    QgsService,
    QgsServerRequest,
    QgsServerResponse,
    QgsServerInterface,
)

from .core import (
    write_json_response,
    ServiceError,
)

from lizmap.qgis_plugin_tools.tools.version import version
from lizmap.qgis_plugin_tools.tools.resources import plugin_name


class LizmapServiceError(ServiceError):

    def __init__(self, code: str, msg: str, responseCode: int = 500) -> None:
        super().__init__(code, msg, responseCode)


class LizmapService(QgsService):

    def __init__(self, serverIface: 'QgsServerInterface', debug: bool = False) -> None:
        super().__init__()
        self.server_iface = serverIface
        self.debugMode = debug

    # QgsService inherited

    def name(self) -> str:
        """ Service name
        """
        return 'LIZMAP'

    def version(self) -> str:
        """ Service version
        """
        return "1.0.0"

    def allowMethod(self, method: QgsServerRequest.Method) -> bool:
        """ Check supported HTTP methods
        """
        return method in (
            QgsServerRequest.GetMethod, QgsServerRequest.PostMethod)

    def executeRequest(self, request: QgsServerRequest, response: QgsServerResponse,
                       project: QgsProject) -> None:
        """ Execute a 'LIZMAP' request
        """

        params = request.parameters()

        # noinspection PyBroadException
        try:
            reqparam = params.get('REQUEST', '').upper()

            try:
                bytes(request.data()).decode()
            except Exception:
                raise LizmapServiceError(
                    "Bad request error",
                    "Invalid POST DATA for '{}'".format(reqparam),
                    400)

            if reqparam == 'GETSERVERSETTINGS':
                self.getserversettings(params, response, project)
            else:
                raise LizmapServiceError(
                    "Bad request error",
                    "Invalid REQUEST parameter: must be one of GETSERVERSETTINGS, found '{}'".format(reqparam),
                    400)

        except LizmapServiceError as err:
            err.formatResponse(response)
        except Exception:
            QgsMessageLog.logMessage("Unhandled exception:\n{}".format(traceback.format_exc()), "lizmap", Qgis.Critical)
            err = LizmapServiceError("Internal server error", "Internal 'lizmap' service error")
            err.formatResponse(response)

    def getserversettings(self, params: Dict[str, str], response: QgsServerResponse, project: QgsProject) -> None:
        """ Get Lizmap Server settings
        """

        # create the body
        body = {
            'qgis': {},
            'gdalogr': {},
            'services': [],
            'lizmap': {},
        }

        # QGIS info
        qgis_version_splitted = Qgis.QGIS_VERSION.split('-')
        body['qgis']['version'] = qgis_version_splitted[0]
        body['qgis']['name'] = qgis_version_splitted[1]
        body['qgis']['version_int'] = Qgis.QGIS_VERSION_INT

        # GDAL/OGR
        body['gdalogr']['name'] = gdal.VersionInfo('NAME')
        body['gdalogr']['version_int'] = gdal.VersionInfo('VERSION_NUM')

        reg = self.server_iface.serviceRegistry()
        services = ['WMS', 'WFS', 'WCS', 'WMTS', 'ATLAS', 'CADASTRE', 'EXPRESSION', 'LIZMAP']
        for s in services:
            if reg.getService(s):
                body['services'].append(s)

        # Lizmap plugin metadata.
        body['lizmap']['name'] = plugin_name()
        body['lizmap']['version'] = version()

        write_json_response(body, response)
        return
