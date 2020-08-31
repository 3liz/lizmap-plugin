__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'

import json

from typing import Dict, Union

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


def find_vector_layer(layer_name: str, project: QgsProject) -> Union[None, QgsVectorLayer]:
    """ Find vector layer with name, short name or layer id. """
    for layer in project.mapLayers().values():
        # only vector layer
        if layer.type() != QgsMapLayer.VectorLayer:
            continue
        # check name
        if layer.name() == layer_name:
            return layer
        # check short name
        if layer.shortName() == layer_name:
            return layer
        # check layer id
        if layer.id() == layer_name:
            return layer
    return None


def get_server_fid(feature: QgsFeature, pk_attributes: []) -> str:
    """ Build server feature ID. """
    if not pk_attributes:
        return str(feature.id())

    return '@@'.join([str(feature.attribute(pk)) for pk in pk_attributes])


class ServiceError(Exception):

    def __init__(self, code: str, msg: str, response_code: int = 500) -> None:
        super().__init__(msg)
        self.service = 'Lizmap'
        self.msg = msg
        self.code = code
        self.response_code = response_code
        QgsMessageLog.logMessage("{} request error {}: {}".format(self.service, code, msg), "lizmap", Qgis.Critical)

    def formatResponse(self, response: QgsServerResponse) -> None:
        """ Format error response
        """
        body = {'status': 'fail', 'code': self.code, 'message': self.msg}
        response.clear()
        write_json_response(body, response, self.response_code)
