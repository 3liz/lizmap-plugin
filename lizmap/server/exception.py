__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtXml import QDomDocument
from qgis.server import QgsServerException, QgsServerResponse

from lizmap.server.core import write_json_response
from lizmap.server.logger import Logger


class ServiceError(Exception):

    def __init__(self, code: str, msg: str, response_code: int = 500) -> None:
        super().__init__(msg)
        self.service = 'Lizmap'
        self.msg = msg
        self.code = code
        self.response_code = response_code
        Logger.critical("{} request error {}: {}".format(self.service, code, msg))

    def formatResponse(self, response: QgsServerResponse) -> None:
        """ Format error response
        """
        body = {'status': 'fail', 'code': self.code, 'message': self.msg}
        response.clear()
        write_json_response(body, response, self.response_code)


class ExpressionServiceError(ServiceError):

    def __init__(self, code: str, msg: str, response_code: int = 500) -> None:
        super().__init__(code, msg, response_code)
        self.service = 'Expression'


class LizmapFilterException(QgsServerException):

    def __init__(
            self,
            code: str,
            message: str, locator: str = '', response_code: int = 500, version: str = '1.3.0') -> None:
        super(QgsServerException, self).__init__(message, response_code)
        self.code = code
        self.message = message
        self.locator = locator
        self.response_code = response_code
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
