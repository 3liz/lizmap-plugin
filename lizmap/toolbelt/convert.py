__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from typing import Union

from qgis.core import QgsLayerTreeGroup, QgsLayerTreeLayer, QgsLayerTreeNode
from qgis.PyQt import sip

# SIP cast issues
# Related to
# https://github.com/3liz/lizmap-plugin/issues/299
# https://github.com/3liz/lizmap-plugin/issues/528


def cast_to_layer(node: QgsLayerTreeNode) -> QgsLayerTreeLayer:
    """ Cast a legend node to a layer. """
    if isinstance(node, QgsLayerTreeLayer):
        return node

    # noinspection PyTypeChecker
    return sip.cast(node, QgsLayerTreeLayer)


def cast_to_group(node: QgsLayerTreeNode) -> QgsLayerTreeGroup:
    """Cast a legend node to a group. """
    if isinstance(node, QgsLayerTreeGroup):
        return node

    # noinspection PyTypeChecker
    return sip.cast(node, QgsLayerTreeGroup)


def to_bool(val: Union[str, int, float, bool, None], default_value: bool = True) -> bool:
    """ Convert lizmap config value to boolean """
    if isinstance(val, bool):
        return val

    if val is None or val == '':
        return default_value

    if isinstance(val, str):
        # For string, compare lower value to True string
        return val.lower() in ('yes', 'true', 't', '1')

    elif not val:
        # For value like False, 0, 0.0, None, empty list or dict returns False
        return False

    return default_value
