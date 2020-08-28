__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'

import json

from typing import Dict

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProject,
    QgsMapLayer,
    QgsVectorLayer,
    QgsFeature,
)
from qgis.server import (
    QgsServerResponse,
)


def write_json_response(data: Dict[str, str], response: QgsServerResponse, code: int = 200) -> None:
    """ Write data as JSON response. """
    response.setStatusCode(code)
    response.setHeader("Content-Type", "application/json")
    response.write(json.dumps(data))


def find_vector_layer(layername: str, project: QgsProject) -> QgsVectorLayer:
    """ Find vector layer with name, short name or layer id. """
    for layer in project.mapLayers().values():
        # only vector layer
        if layer.type() != QgsMapLayer.VectorLayer:
            continue
        # check name
        if layer.name() == layername:
            return layer
        # check short name
        if layer.shortName() == layername:
            return layer
        # check layer id
        if layer.id() == layername:
            return layer
    return None


def get_server_fid(feature: QgsFeature, pkAttributes: []) -> str:
    """ Build server feature ID. """
    if not pkAttributes:
        return str(feature.id())

    return '@@'.join([str(feature.attribute(pk)) for pk in pkAttributes])


class ServiceError(Exception):

    def __init__(self, code: str, msg: str, responseCode: int = 500) -> None:
        super().__init__(msg)
        self.service = 'Lizmap'
        self.msg = msg
        self.code = code
        self.responseCode = responseCode
        QgsMessageLog.logMessage("{} request error {}: {}".format(self.service, code, msg), "lizmap", Qgis.Critical)

    def formatResponse(self, response: QgsServerResponse) -> None:
        """ Format error response
        """
        body = {'status': 'fail', 'code': self.code, 'message': self.msg}
        response.clear()
        write_json_response(body, response, self.responseCode)
