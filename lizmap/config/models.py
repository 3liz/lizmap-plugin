from types import MappingProxyType
from typing import (
    Any,
    NotRequired,
    Sequence,
    TypedDict,
)

from qgis.core import Qgis

MappingQgisGeometryType = MappingProxyType(
    {
        Qgis.GeometryType.Point: "point",
        Qgis.GeometryType.Line: "line",
        Qgis.GeometryType.Polygon: "polygon",
        Qgis.GeometryType.Unknown: "unknown",
        Qgis.GeometryType.Null: "none",
    }
)


class _Item(TypedDict):
    wType: str
    type: str
    default: Any
    always_export: NotRequired[bool]
    use_proper_boolean: NotRequired[bool]
    list: NotRequired[Sequence]
    tooltip: NotRequired[str]
    isMetadata: NotRequired[bool]
    children: NotRequired[str]
    parent: NotRequired[str]
    comment: NotRequired[str]
    max_version: NotRequired[str]
    min_version: NotRequired[str]
    exclusive: NotRequired[bool]
    _api: NotRequired[bool]
