__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import configparser
import traceback

from os.path import dirname, join
from typing import Dict

from osgeo import gdal
from qgis.core import Qgis, QgsProject
from qgis.server import (
    QgsServerInterface,
    QgsServerRequest,
    QgsServerResponse,
    QgsService,
)

from lizmap.server.core import ServiceError, write_json_response
from lizmap.server.logger import Logger


class LizmapServiceError(ServiceError):
    # def __init__(self, code: str, msg: str, response_code: int = 500) -> None:
    #     super().__init__(code, msg, response_code)
    pass


class LizmapService(QgsService):

    def __init__(self, server_iface: 'QgsServerInterface') -> None:
        super().__init__()
        self.server_iface = server_iface
        self.logger = Logger()

    # QgsService inherited

    def name(self) -> str:
        """ Service name
        """
        return 'LIZMAP'

    def version(self) -> str:
        """ Service version
        """
        return "1.0.0"

    # def allowMethod(self, method: QgsServerRequest.Method) -> bool:
    #     """ Check supported HTTP methods
    #     """
    #     return method in (
    #         QgsServerRequest.GetMethod, QgsServerRequest.PostMethod)

    def executeRequest(self, request: QgsServerRequest, response: QgsServerResponse,
                       project: QgsProject) -> None:
        """ Execute a 'LIZMAP' request
        """

        params = request.parameters()

        # noinspection PyBroadException
        try:
            req_param = params.get('REQUEST', '').upper()

            try:
                bytes(request.data()).decode()
            except Exception:
                raise LizmapServiceError(
                    "Bad request error",
                    "Invalid POST DATA for '{}'".format(req_param),
                    400)

            if req_param == 'GETSERVERSETTINGS':
                self.getserversettings(params, response, project)
            else:
                raise LizmapServiceError(
                    "Bad request error",
                    "Invalid REQUEST parameter: must be one of GETSERVERSETTINGS, found '{}'".format(req_param),
                    400)

        except LizmapServiceError as err:
            err.formatResponse(response)
        except Exception as e:
            self.logger.critical("Unhandled exception:\n{}".format(traceback.format_exc()))
            self.logger.critical(str(e))
            err = LizmapServiceError("Internal server error", "Internal 'lizmap' service error")
            err.formatResponse(response)

    def getserversettings(self, params: Dict[str, str], response: QgsServerResponse, project: QgsProject) -> None:
        """ Get Lizmap Server settings
        """
        _ = params
        _ = project

        # create the body
        body = {
            'qgis': {},
            'gdalogr': {},
            'services': [],
            'lizmap': {},
        }

        # QGIS info
        qgis_version_split = Qgis.QGIS_VERSION.split('-')
        body['qgis']['version'] = qgis_version_split[0]
        body['qgis']['name'] = qgis_version_split[1]
        body['qgis']['version_int'] = Qgis.QGIS_VERSION_INT

        # GDAL/OGR
        body['gdalogr']['name'] = gdal.VersionInfo('NAME')
        body['gdalogr']['version_int'] = gdal.VersionInfo('VERSION_NUM')

        reg = self.server_iface.serviceRegistry()
        services = ['WMS', 'WFS', 'WCS', 'WMTS', 'ATLAS', 'CADASTRE', 'EXPRESSION', 'LIZMAP']
        for s in services:
            if reg.getService(s):
                body['services'].append(s)

        # Lizmap plugin metadata, do not use qgis_plugin_tools because of the packaging.
        file_path = join(dirname(dirname(__file__)), 'metadata.txt')
        config = configparser.ConfigParser()
        try:
            config.read(file_path, encoding='utf8')
        except UnicodeDecodeError:
            # Issue LWC https://github.com/3liz/lizmap-web-client/issues/1908
            # Maybe a locale issue ?
            self.logger.critical(
                "Error, an UnicodeDecodeError occurred while reading the metadata.txt. Is the locale "
                "correctly set on the server ?")
            version = 'NULL'
        else:
            version = config["general"]["version"]

        body['lizmap']['name'] = 'Lizmap'
        body['lizmap']['version'] = version

        write_json_response(body, response)
        return
