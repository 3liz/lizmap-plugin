from typing import Union

from qgis.core import QgsLayerTreeGroup, QgsLayerTreeLayer, QgsLayerTreeNode
from qgis.PyQt import sip

# SIP cast issues
# Related to
# https://github.com/3liz/lizmap-plugin/issues/299
# https://github.com/3liz/lizmap-plugin/issues/528


def cast_to_layer(node: QgsLayerTreeNode) -> QgsLayerTreeLayer:
    """Cast a legend node to a layer."""
    return node if isinstance(node, QgsLayerTreeLayer) else sip.cast(node, QgsLayerTreeLayer)


def cast_to_group(node: QgsLayerTreeNode) -> QgsLayerTreeGroup:
    """Cast a legend node to a group."""
    return node if isinstance(node, QgsLayerTreeGroup) else sip.cast(node, QgsLayerTreeGroup)


def as_boolean(val: Union[str, int, float, bool, None]) -> bool:
    return val.lower() in ("yes", "true", "t", "1") if isinstance(val, str) else bool(val)


# Preserve legacy compatibility
def ambiguous_to_bool(val: Union[str, int, float, bool, None], default_value: bool = True) -> bool:
    """Convert lizmap config value to boolean"""

    # XXX WTF ?
    if val is None or val == "":
        return default_value

    return as_boolean(val)
