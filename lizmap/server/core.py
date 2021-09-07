__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import os

from typing import Dict, Tuple, Union

from qgis.core import (
    QgsExpression,
    QgsFeature,
    QgsFields,
    QgsMapLayer,
    QgsProject,
    QgsVectorLayer,
)
from qgis.server import QgsRequestHandler, QgsServerResponse

from lizmap.server.logger import Logger


def write_json_response(data: Dict[str, str], response: QgsServerResponse, code: int = 200) -> None:
    """ Write data as JSON response. """
    response.setStatusCode(code)
    response.setHeader("Content-Type", "application/json")
    response.write(json.dumps(data))


def find_vector_layer_from_params(params, project):
    """ Trying to find the layer in the URL in the given project. """
#         params: Dict[str, str], project: QgsProject) -> tuple[bool, Union[QgsMapLayer, None]]:
    layer_name = params.get('LAYER', params.get('layer', ''))

    if not layer_name:
        return False, None

    layer = find_vector_layer(layer_name, project)

    if not layer:
        return False, None

    return True, layer


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


def get_server_fid(feature: QgsFeature, pk_attributes: list) -> str:
    """ Build server feature ID. """
    if not pk_attributes:
        return str(feature.id())

    return '@@'.join([str(feature.attribute(pk)) for pk in pk_attributes])


def to_bool(val: Union[str, int, float, bool]) -> bool:
    """ Convert lizmap config value to boolean """
    if isinstance(val, str):
        # For string, compare lower value to True string
        return val.lower() in ('yes', 'true', 't', '1')
    elif not val:
        # For value like False, 0, 0.0, None, empty list or dict returns False
        return False
    else:
        return True


def get_lizmap_config(qgis_project_path: str) -> Union[Dict, None]:
    """ Get the lizmap config based on QGIS project path """

    logger = Logger()

    # Check QGIS project path
    if not os.path.exists(qgis_project_path):
        # QGIS Project path does not exist as a file
        # No Lizmap config
        return None

    # Get Lizmap config path
    config_path = qgis_project_path + '.cfg'
    if not os.path.exists(config_path):
        # Lizmap config path does not exist
        logger.info("Lizmap config does not exist")
        # No Lizmap config
        return None

    # Get Lizmap config
    with open(config_path, 'r') as cfg_file:
        # noinspection PyBroadException
        try:
            cfg = json.loads(cfg_file.read())
            if not cfg:
                # Lizmap config is empty
                logger.warning("Lizmap config is empty")
                return None
            return cfg
        except Exception as e:
            # Lizmap config is not a valid JSON file
            logger.critical("Lizmap config not well formed")
            logger.log_exception(e)
            return None


def get_lizmap_layers_config(config: Dict) -> Union[Dict, None]:
    """ Get layers Lizmap config """

    if not config:
        return None

    logger = Logger()

    # Check Lizmap config layers
    if 'layers' not in config or not config['layers']:
        # Lizmap config has no options
        logger.warning("Lizmap config has no layers")
        return None

    # Get Lizmap config layers to check it
    cfg_layers = config['layers']

    # Check that layers lizmap config is dict
    if not isinstance(cfg_layers, dict):
        logger.warning("Layers lizmap config is not dict")
        return None

    # return Lizmap config layers
    return cfg_layers


def get_lizmap_layer_login_filter(config: Dict, layer_name: str) -> Union[Dict, None]:
    """ Get loginFilteredLayers for layer """

    if not config or not isinstance(config, dict):
        return None
    if not layer_name or not isinstance(layer_name, str):
        return None

    logger = Logger()

    # Check Lizmap config loginFilteredLayers
    if 'loginFilteredLayers' not in config or not config['loginFilteredLayers']:
        # Lizmap config has no options
        logger.info("Lizmap config has no loginFilteredLayers")
        return None

    login_filtered_layers = config['loginFilteredLayers']

    # Check loginFilteredLayers for layer
    if layer_name not in login_filtered_layers or not login_filtered_layers[layer_name]:
        # Lizmap config has no options
        logger.info("Layer {} has no loginFilteredLayers".format(layer_name))
        return None

    # get loginFilteredLayers for layer to check it
    cfg_layer_login_filter = login_filtered_layers[layer_name]

    # Check loginFilteredLayers for layer is dict
    if not isinstance(cfg_layer_login_filter, dict):
        logger.warning("loginFilteredLayers for layer {} is not dict".format(layer_name))
        return None

    if 'layerId' not in cfg_layer_login_filter or \
            'filterAttribute' not in cfg_layer_login_filter or \
            'filterPrivate' not in cfg_layer_login_filter:
        # loginFilteredLayers for layer not well formed
        logger.warning("loginFilteredLayers for layer {} not well formed".format(layer_name))
        return None

    return cfg_layer_login_filter


def get_lizmap_groups(handler: QgsRequestHandler) -> Tuple[str]:
    """ Get Lizmap user groups provided by the request """

    # Defined groups
    groups = []
    logger = Logger()

    # Get Lizmap User Groups in request headers
    headers = handler.requestHeaders()
    if headers:
        logger.info("Request headers provided")
        # Get Lizmap user groups defined in request headers
        user_groups = headers.get('X-Lizmap-User-Groups')
        if user_groups is not None:
            groups = [g.strip() for g in user_groups.split(',')]
            logger.info("Lizmap user groups in request headers")
    else:
        logger.info("No request headers provided")

    if len(groups) != 0:
        # noinspection PyTypeChecker
        return tuple(groups)

    logger.info("No lizmap user groups in request headers")

    # Get group in parameters
    params = handler.parameterMap()
    if params:
        # Get Lizmap user groups defined in parameters
        user_groups = params.get('LIZMAP_USER_GROUPS')
        if user_groups is not None:
            groups = [g.strip() for g in user_groups.split(',')]
            logger.info("Lizmap user groups in parameters")

    # noinspection PyTypeChecker
    return tuple(groups)


def get_lizmap_user_login(handler: QgsRequestHandler) -> str:
    """ Get Lizmap user login provided by the request """
    # Defined login
    login = ''

    logger = Logger()

    # Get Lizmap User Login in request headers
    headers = handler.requestHeaders()
    if headers:
        logger.info("Request headers provided")
        # Get Lizmap user login defined in request headers
        user_login = headers.get('X-Lizmap-User')
        if user_login is not None:
            login = user_login
            logger.info("Lizmap user login in request headers")
    else:
        logger.info("No request headers provided")

    if login:
        return login
    else:
        logger.info("No lizmap user login in request headers")

    # Get login in parameters
    params = handler.parameterMap()
    if params:
        # Get Lizmap user login defined in parameters
        user_login = params.get('LIZMAP_USER')
        if user_login is not None:
            login = user_login
            logger.info("Lizmap user login in parameters")

    return login


def get_lizmap_override_filter(handler: QgsRequestHandler) -> bool:
    """ Get Lizmap user login provided by the request """
    # Defined override
    override = None

    logger = Logger()

    # Get Lizmap User Login in request headers
    headers = handler.requestHeaders()
    if headers:
        logger.info("Request headers provided")
        # Get Lizmap user login defined in request headers
        override_filter = headers.get('X-Lizmap-Override-Filter')
        if override_filter is not None:
            override = to_bool(override_filter)
            logger.info("Lizmap override filter in request headers")
    else:
        logger.info("No request headers provided")

    if override is not None:
        return override

    logger.info("No lizmap override filter in request headers")

    # Get login in parameters
    params = handler.parameterMap()
    if params:
        # Get Lizmap user login defined in parameters
        override_filter = params.get('LIZMAP_OVERRIDE_FILTER')
        if override_filter is not None:
            override = to_bool(override_filter)
            logger.info("Lizmap override filter in parameters")
        else:
            override = False
            logger.info("No lizmap override filter in parameters")

    return override


def is_editing_context(handler: QgsRequestHandler) -> bool:
    """ Check if headers are defining an editing context. """
    headers = handler.requestHeaders()
    if not headers:
        return False

    return to_bool(headers.get('X-Lizmap-Edition-Context'))


def server_feature_id_expression(feature_id, pk_attributes: list, fields: QgsFields) -> str:
    """ Port of QgsServerFeatureId::getExpressionFromServerFid.

    The value "@@" is hardcoded in the CPP file.
    """
    if len(pk_attributes) == 0:
        return ""

    expression = ""
    pk_values = feature_id.split("@@")

    for i, pk_value in enumerate(pk_values):

        if i > 0:
            expression += ' AND '

        field_name = fields.at(i).name()
        expression += QgsExpression.createFieldEqualityExpression(field_name, pk_values[i])

    return expression
