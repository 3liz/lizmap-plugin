import json
import os

from typing import (
    Any,
    Dict,
    Mapping,
    Optional,
    Sequence,
)

from qgis.core import QgsMapLayer, QgsProject

from .global_options import globalOptionDefinitions
from .layer_options import layerOptionDefinitions
from .models import MappingQgisGeometryType


class LizmapConfigError(Exception):
    pass


class LizmapConfig:
    def __init__(self, project: QgsProject):
        """Configuration setup"""
        self.globalOptionDefinitions = globalOptionDefinitions
        self.layerOptionDefinitions = layerOptionDefinitions

        # We want to translate some items, do not make this variable static
        if not isinstance(project, QgsProject):
            self.project = self._load_project(project)
        else:
            self.project = project

        self._WFSLayers = self.project.readListEntry("WFSLayers", "")[0]

        self._layer_attributes: Dict = {}
        self._global_options: Dict = {}
        self._layer_options: Dict = {}

    @staticmethod
    def _load_project(path):
        """Read a qgis project from path"""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        project = QgsProject()
        if not project.read(path):
            raise LizmapConfigError("Error reading qgis project")
        return project

    def get_layer_by_name(self, name: str) -> Optional[QgsMapLayer]:
        """Return a unique layer by its name"""
        matches = self.project.mapLayersByName(name)
        if len(matches) > 0:
            return matches[0]
        return None

    def to_json(
        self,
        p_global_options: Optional[Mapping[str, Any]] = None,
        p_layer_options: Optional[Mapping[str, Any]] = None,
        p_attributes_options: Optional[Mapping[str, Any]] = None,
        sort_keys: bool = False,
        indent: int = 4,
        **kwargs,
    ) -> str:
        """Returns the lizmap JSON configuration"""
        # Set the options from the default only if overridden or not defined
        if p_global_options is not None or len(self._global_options) == 0:
            self.set_global_options(p_global_options)

        if p_layer_options is not None or len(self._layer_options) == 0:
            self.set_layer_options(p_layer_options)

        if p_attributes_options:
            self.set_layer_attributes(p_attributes_options)

        config = {
            "options": self._global_options,
            "layers": self._layer_options,
        }

        if len(self._layer_attributes):
            config["attributeLayers"] = self._layer_attributes

        # Write json to the cfg file
        return json.dumps(config, sort_keys=sort_keys, indent=indent, **kwargs)

    def set_global_options(self, options: Optional[Mapping[str, Any]] = None):
        """Set the global lizmap configuration options"""
        # set defaults
        self._global_options = {
            k: v["default"] for k, v in self.globalOptionDefinitions.items() if v.get("_api", True)
        }

        # Set custom options
        if options is not None:
            self._global_options.update(
                (k, v) for k, v in options.items() if k in self.globalOptionDefinitions
            )

        # projection
        # project projection
        project_crs = self.project.crs()
        self._global_options["projection"] = {
            "proj4": str(project_crs.toProj()),
            "ref": str(project_crs.authid()),
        }

        # wms extent
        project_wms_extent = self.project.readListEntry("WMSExtent", "")[0]
        if len(project_wms_extent) > 1:
            bbox = [float(x) for x in project_wms_extent[:4]]
        else:
            bbox = []

        self._global_options["bbox"] = bbox

        if not self._global_options["initialExtent"]:
            self._global_options["initialExtent"] = bbox

    def add_layer(self, layer: QgsMapLayer, **options) -> Mapping[str, Any]:
        """Add a layer to the configuration

        Pass options as keyword arguments
        """
        # lizmap default options for layer
        lo = {k: v["default"] for k, v in self.layerOptionDefinitions.items() if v.get("_api", True)}

        lo["title"] = layer.title() or layer.name()
        lo["abstract"] = layer.abstract()
        lo["type"] = "layer"

        geometry_type = "-1"
        # FIXME: Uses Qgis enum
        if layer.type() == 0:  # if it is a vector layer
            geometry_type = MappingQgisGeometryType[layer.geometryType()]
        if geometry_type != -1:
            lo["geometryType"] = geometry_type

        l_extent = layer.extent()
        lo["extent"] = [
            l_extent.xMinimum(),
            l_extent.yMinimum(),
            l_extent.xMaximum(),
            l_extent.yMaximum(),
        ]

        lo["crs"] = layer.crs().authid()

        # styles
        if layer and hasattr(layer, "styleManager"):
            ls = layer.styleManager().styles()
            if len(ls) > 1:
                lo["styles"] = ls

        # Override with passed p_layer_options parameter
        lo.update((k, v) for k, v in options if k in self.layerOptionDefinitions)

        # The following should not be overridden
        lo["id"] = layer.id()
        lo["name"] = layer.name()

        # Add metadata
        if layer.hasScaleBasedVisibility():
            lo["minScale"] = max_scale if (max_scale := layer.maximumScale()) >= 0 else 0
            lo["maxScale"] = min_scale if (min_scale := layer.minimumScale()) >= 0 else 0

        # set config
        lid = str(layer.name())
        self._layer_options[lid] = lo
        return lo

    def set_layer_options(self, p_layer_options: Optional[Mapping[str, Any]] = None):
        """Set the configuration options for the the project layers

        :param p_layer_options: dict of options for each layers
                if p_layer options is None, add all layers otherwise add layer for
                all layer names specified in p_layer_options
        """
        self._layer_options = {}

        if p_layer_options is None:
            for layer in self.project.mapLayers().values():
                self.add_layer(layer)
        else:
            for lname, options in p_layer_options.items():
                if layer := self.get_layer_by_name(lname):
                    self.add_layer(layer, **options)

    def hasWFSCapabilities(self, layer: QgsMapLayer) -> bool:
        """Test if layer has WFS capabilities"""
        return layer.id() in self._WFSLayers

    def publish_layer_attribute_table(
        self,
        layer: QgsMapLayer,
        primary_key: str,
        hidden_fields: Sequence[str] = (),
        pivot: bool = False,
        hide_as_child: bool = False,
        hide_layer: bool = False,
    ):
        """publish attribute table"""
        if not hidden_fields:
            hidden_fields = []

        # Check that the layer has WFS enabled
        if not self.hasWFSCapabilities(layer):
            raise LizmapConfigError("WFS Required for layer %s" % layer.name())

        lyr_name = layer.name()
        lyr_attrs = self._layer_attributes.get(lyr_name)
        if lyr_attrs is None:
            lyr_attrs = {"order": len(self._layer_attributes)}

        lyr_attrs.update(
            primaryKey=primary_key,
            hiddenFields=",".join(hidden_fields),
            pivot=pivot,
            hideAsChild=hide_as_child,
            hideLayer=hide_layer,
            layerId=layer.id(),
        )

        self._layer_attributes[lyr_name] = lyr_attrs

    def set_layer_attributes(self, p_attributes_options: Mapping[str, Any]):
        """Set the attribute options"""
        self._layer_attributes = {}
        for lname, options in p_attributes_options.items():
            layer = self.get_layer_by_name(lname)
            if layer:
                self.publish_layer_attribute_table(layer, **options)

    def set_title(self, title: str):
        """Set WMS title"""
        self.project.writeEntry("WMSServiceTitle", "/", title)

    def set_description(self, description: str):
        """Set WMS description"""
        self.project.writeEntry("WMSServiceDescription", "/", description)
        self.project.setDirty()

    def set_wmsextent(self, xmin: float, ymin: float, xmax: float, ymax: float):
        """Set WMS extent"""
        self.project.writeEntry("WMSExtent", "/", [str(xmin), str(ymin), str(xmax), str(ymax)])

    # noinspection PyPep8Naming
    def configure_server_options(
        self,
        WMSTitle: Optional[str] = None,
        WMSDescription: Optional[str] = None,
        WFSLayersPrecision: int = 6,
        WMSExtent: Optional[Sequence[int]] = None,
    ):
        """Configure server options for layers in the qgis project

        The method will set WMS/WMS publication options for the layers in the project
        """
        if WMSTitle is not None:
            self.set_title(WMSTitle)
        if WMSDescription is not None:
            self.set_description(WMSDescription)
        if WMSExtent is not None:
            self.set_wmsextent(*WMSExtent)

        prj = self.project

        prj.writeEntry(
            "WFSLayers",
            "/",
            [lid for lid, lyr in prj.mapLayers().items() if lyr.type() == QgsMapLayer.LayerType.VectorLayer],
        )
        for lid, lyr in prj.mapLayers().items():
            if lyr.type() == QgsMapLayer.LayerType.VectorLayer:
                prj.writeEntry("WFSLayersPrecision", "/" + lid, WFSLayersPrecision)
        prj.writeEntry(
            "WCSLayers",
            "/",
            [lid for lid, lyr in prj.mapLayers().items() if lyr.type() == QgsMapLayer.LayerType.RasterLayer],
        )
        prj.setDirty()

        # Update WFS layer list
        self._WFSLayers = prj.readListEntry("WFSLayers", "")[0]
