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
    """ Write data as json response
    """
    response.setStatusCode(code)
    response.setHeader("Content-Type", "application/json")
    response.write(json.dumps(data))

def findVectorLayer(layername: str, project: QgsProject) -> QgsVectorLayer:
    """ Find vector layer with name, short name or layer id """
    for l in project.mapLayers().values():
        # only vectorlayer
        if l.type() != QgsMapLayer.VectorLayer:
            continue
        # check name
        if l.name() == layername:
            return l
        # check short name
        if l.shortName() == layername:
            return l
        # check layer id
        if l.id() == layername:
            return l
    return None

def getServerFid(feature: QgsFeature, pkAttributes: []) -> str:
    """ Build server feature id """
    if not pkAttributes:
        return str(feature.id())

    return '@@'.join([str(feature.attributes(pk)) for pk in pkAttributes])

class ServiceError(Exception):

    def __init__(self, code: str, msg: str, responseCode: int = 500) -> None:
        super().__init__(msg)
        self.service = 'Lizmap'
        self.msg = msg
        self.code = code
        self.responseCode = responseCode
        QgsMessageLog.logMessage("%s request error %s: %s" % (self.service, code, msg), "lizmap", Qgis.Critical)

    def formatResponse(self, response: QgsServerResponse) -> None:
        """ Format error response
        """
        body = {'status': 'fail', 'code': self.code, 'message': self.msg}
        response.clear()
        write_json_response(body, response, self.responseCode)