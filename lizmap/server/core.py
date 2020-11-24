__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'

import json
import os

from typing import Dict, List, Union

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsMapLayer,
    QgsMessageLog,
    QgsProject,
    QgsVectorLayer,
)
from qgis.server import QgsRequestHandler, QgsServerResponse


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


def config_value_to_boolean(val: Union[str, int, float, bool]) -> bool:
    """ Convert lizmap config value to boolean """
    if type(val) == str:
        # For string, compare lower value to True string
        return val.lower() in ('yes', 'true', 't', '1')
    elif not val:
        # For value like False, 0, 0.0, None, empty list or dict returns False
        return False
    else:
        return True


def get_lizmap_config(qgis_project_path: str) -> Union[Dict, None]:
    """ Get the lizmap config based on QGIS project path """

    # Check QGIS project path
    if not os.path.exists(qgis_project_path):
        # QGIS Project path does not exist as a file
        # No Lizmap config
        return None

    # Get Lizmap config path
    config_path = qgis_project_path + '.cfg'
    if not os.path.exists(config_path):
        # Lizmap config path does not exist
        QgsMessageLog.logMessage("Lizmap config does not exist", "lizmap", Qgis.Info)
        # No Lizmap config
        return None

    # Get Lizmap config
    with open(config_path, 'r') as cfg_file:
        # noinspection PyBroadException
        try:
            cfg = json.loads(cfg_file.read())
            if not cfg:
                # Lizmap config is empty
                QgsMessageLog.logMessage("Lizmap config is empty", "lizmap", Qgis.Warning)
                return None
            return cfg
        except Exception:
            # Lizmap config is not a valid JSON file
            QgsMessageLog.logMessage("Lizmap config not well formed", "lizmap", Qgis.Critical)
            return None


def get_lizmap_layers_config(config: Dict) -> Union[Dict, None]:
    """ Get layers Lizmap config """

    if not config:
        return None

    # Check Lizmap config layers
    if 'layers' not in config or not config['layers']:
        # Lizmap config has no options
        QgsMessageLog.logMessage("Lizmap config has no layers", "lizmap", Qgis.Warning)
        return None

    # Get Lizmap config layers to check it
    cfg_layers = config['layers']

    # Check that layers lizmap config is dict
    if type(cfg_layers) != dict:
        QgsMessageLog.logMessage("Layers lizmap config is not dict", "lizmap", Qgis.Warning)
        return None

    # return Lizmap config layers
    return cfg_layers


def get_lizmap_layer_login_filter(config: Dict, layerName: str) -> Union[Dict, None]:
    """ Get loginFilteredLayers for layer """

    if not config or type(config) != dict:
        return None
    if not layerName or type(layerName) != str:
        return None

    # Check Lizmap config loginFilteredLayers
    if 'loginFilteredLayers' not in config or not config['loginFilteredLayers']:
        # Lizmap config has no options
        QgsMessageLog.logMessage("Lizmap config has no loginFilteredLayers", "lizmap", Qgis.Info)
        return None

    loginFilteredLayers = config['loginFilteredLayers']

    # Check loginFilteredLayers for layer
    if layerName not in loginFilteredLayers or not loginFilteredLayers[layerName]:
        # Lizmap config has no options
        QgsMessageLog.logMessage("Layer {} has no loginFilteredLayers".format(layerName), "lizmap", Qgis.Info)
        return None

    # get loginFilteredLayers for layer to check it
    cfg_layer_login_filter = loginFilteredLayers[layerName]

    # Check loginFilteredLayers for layer is dict
    if type(cfg_layer_login_filter) != dict:
        QgsMessageLog.logMessage(
            "loginFilteredLayers for layer {} is not dict".format(layerName), "lizmap", Qgis.Warning)
        return None

    if 'layerId' not in cfg_layer_login_filter or \
            'filterAttribute' not in cfg_layer_login_filter or \
            'filterPrivate' not in cfg_layer_login_filter:
        # loginFilteredLayers for layer not well formed
        QgsMessageLog.logMessage(
            "loginFilteredLayers for layer {} not well formed".format(layerName), "lizmap", Qgis.Warning)
        return None

    return cfg_layer_login_filter


def get_lizmap_groups(handler: 'QgsRequestHandler') -> 'List[str]':
    """ Get Lizmap user groups provided by the request """

    # Defined groups
    groups = []

    # Get Lizmap User Groups in request headers
    headers = handler.requestHeaders()
    if headers:
        QgsMessageLog.logMessage("Request headers provided", "lizmap", Qgis.Info)
        # Get Lizmap user groups defined in request headers
        user_groups = headers.get('X-Lizmap-User-Groups')
        if user_groups is not None:
            groups = [g.strip() for g in user_groups.split(',')]
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
        user_groups = params.get('LIZMAP_USER_GROUPS')
        if user_groups is not None:
            groups = [g.strip() for g in user_groups.split(',')]
            QgsMessageLog.logMessage("Lizmap user groups in parameters", "lizmap", Qgis.Info)

    return groups


def get_lizmap_user_login(handler: 'QgsRequestHandler') -> str:
    """ Get Lizmap user login provided by the request """
    # Defined login
    login = ''

    # Get Lizmap User Login in request headers
    headers = handler.requestHeaders()
    if headers:
        QgsMessageLog.logMessage("Request headers provided", "lizmap", Qgis.Info)
        # Get Lizmap user login defined in request headers
        user_login = headers.get('X-Lizmap-User')
        if user_login is not None:
            login = user_login
            QgsMessageLog.logMessage("Lizmap user login in request headers", "lizmap", Qgis.Info)
    else:
        QgsMessageLog.logMessage("No request headers provided", "lizmap", Qgis.Info)

    if login:
        return login
    else:
        QgsMessageLog.logMessage("No lizmap user login in request headers", "lizmap", Qgis.Info)

    # Get login in parameters
    params = handler.parameterMap()
    if params:
        # Get Lizmap user login defined in parameters
        user_login = params.get('LIZMAP_USER')
        if user_login is not None:
            login = user_login
            QgsMessageLog.logMessage("Lizmap user login in parameters", "lizmap", Qgis.Info)

    return login


def get_lizmap_override_filter(handler: 'QgsRequestHandler') -> bool:
    """ Get Lizmap user login provided by the request """
    # Defined override
    override = None

    # Get Lizmap User Login in request headers
    headers = handler.requestHeaders()
    if headers:
        QgsMessageLog.logMessage("Request headers provided", "lizmap", Qgis.Info)
        # Get Lizmap user login defined in request headers
        override_filter = headers.get('X-Lizmap-Override-Filter')
        if override_filter is not None:
            override = override_filter.lower() in ['true', '1', 't', 'y', 'yes']
            QgsMessageLog.logMessage("Lizmap override filter in request headers", "lizmap", Qgis.Info)
    else:
        QgsMessageLog.logMessage("No request headers provided", "lizmap", Qgis.Info)

    if override is not None:
        return override
    else:
        QgsMessageLog.logMessage("No lizmap override filter in request headers", "lizmap", Qgis.Info)

    # Get login in parameters
    params = handler.parameterMap()
    if params:
        # Get Lizmap user login defined in parameters
        override_filter = params.get('LIZMAP_OVERRIDE_FILTER')
        if override_filter is not None:
            override = override_filter.lower() in ['true', '1', 't', 'y', 'yes']
            QgsMessageLog.logMessage("Lizmap override filter in parameters", "lizmap", Qgis.Info)
        else:
            override = False
            QgsMessageLog.logMessage("No lizmap override filter in parameters", "lizmap", Qgis.Info)

    return override


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
