from typing import (
    TypedDict,
)

from lizmap.definitions.definitions import LwcVersions
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.version import format_version_integer, version

from .models import _Item


class Metadata(TypedDict):
    lizmap_plugin_version: _Item
    lizmap_web_client_target_version: _Item


class GlobalOptionsDefinitions(TypedDict):
    metadata: Metadata
    mapScales: _Item
    minScale: _Item
    max_scale_points: _Item
    max_scale_lines_polygons: _Item
    use_native_zoom_levels: _Item
    hide_numeric_scale_value: _Item
    acl: _Item
    initialExtent: _Item
    googleKey: _Item
    googleHybrid: _Item
    googleSatellite: _Item
    googleTerrain: _Item
    googleStreets: _Item
    osmMapnik: _Item
    openTopoMap: _Item
    bingKey: _Item
    bingStreets: _Item
    bingSatellite: _Item
    bingHybrid: _Item
    ignKey: _Item
    ignSatellite: _Item
    ignTerrain: _Item
    ignCadastral: _Item
    hideGroupCheckbox: _Item
    activateFirstMapTheme: _Item
    popupLocation: _Item
    draw: _Item
    # Deprecated since LWC 3.7.0
    # There is a new "print" panel
    print: _Item
    measure: _Item
    externalSearch: _Item
    # Deprecated, it has been removed in LWC 3.8
    zoomHistory: _Item
    geolocation: _Item
    pointTolerance: _Item
    lineTolerance: _Item
    polygonTolerance: _Item
    hideHeader: _Item
    hideMenu: _Item
    hideLegend: _Item
    hideOverview: _Item
    hideNavbar: _Item
    hideProject: _Item
    automatic_permalink: _Item
    wms_single_request_for_all_layers: _Item
    tmTimeFrameSize: _Item
    tmTimeFrameType: _Item
    tmAnimationFrameLength: _Item
    emptyBaselayer: _Item
    startupBaselayer: _Item
    limitDataToBbox: _Item
    datavizLocation: _Item
    datavizTemplate: _Item
    theme: _Item
    atlasShowAtStartup: _Item
    atlasAutoPlay: _Item
    fixed_scale_overview_map: _Item
    dxfExportEnabled: _Item
    allowedGroups: _Item


globalOptionDefinitions = {
    "metadata": {
        "lizmap_plugin_version": {
            "wType": "spinbox",
            "type": "integer",
            "default": version(),
        },
        "lizmap_web_client_target_version": {
            "wType": "spinbox",
            "type": "integer",
            "default": format_version_integer("{}.0".format(LwcVersions.latest().value)),
        },
    },
    "mapScales": {
        "wType": "text",
        "type": "intlist",
        "default": [10000, 25000, 50000, 100000, 250000, 500000],
    },
    "minScale": {"wType": "text", "type": "integer", "default": 1},
    "maxScale": {"wType": "text", "type": "integer", "default": 1000000000},
    "max_scale_points": {"wType": "scale", "type": "float", "default": 5000.0},
    "max_scale_lines_polygons": {"wType": "scale", "type": "float", "default": 5000.0},
    "use_native_zoom_levels": {
        "wType": "checkbox",
        "type": "boolean",
        "default": True,
        "always_export": True,
        "use_proper_boolean": True,
    },
    "hide_numeric_scale_value": {
        "wType": "checkbox",
        "type": "boolean",
        "default": True,
        "always_export": True,
        "use_proper_boolean": True,
    },
    "acl": {"wType": "text", "type": "list", "default": []},
    "initialExtent": {"wType": "extent", "type": "floatlist", "default": []},
    "googleKey": {"wType": "text", "type": "string", "default": ""},
    "googleHybrid": {"wType": "checkbox", "type": "boolean", "default": False},
    "googleSatellite": {"wType": "checkbox", "type": "boolean", "default": False},
    "googleTerrain": {"wType": "checkbox", "type": "boolean", "default": False},
    "googleStreets": {"wType": "checkbox", "type": "boolean", "default": False},
    "osmMapnik": {"wType": "checkbox", "type": "boolean", "default": False},
    "openTopoMap": {
        "wType": "checkbox",
        "type": "boolean",
        "default": False,
        "use_proper_boolean": False,
    },
    "bingKey": {"wType": "text", "type": "string", "default": ""},
    "bingStreets": {"wType": "checkbox", "type": "boolean", "default": False},
    "bingSatellite": {"wType": "checkbox", "type": "boolean", "default": False},
    "bingHybrid": {"wType": "checkbox", "type": "boolean", "default": False},
    "ignKey": {"wType": "text", "type": "string", "default": ""},
    "ignStreets": {"wType": "checkbox", "type": "boolean", "default": False},
    "ignSatellite": {"wType": "checkbox", "type": "boolean", "default": False},
    "ignTerrain": {"wType": "checkbox", "type": "boolean", "default": False},
    "ignCadastral": {"wType": "checkbox", "type": "boolean", "default": False},
    "hideGroupCheckbox": {"wType": "checkbox", "type": "boolean", "default": False},
    "activateFirstMapTheme": {"wType": "checkbox", "type": "boolean", "default": False},
    "popupLocation": {
        "wType": "list",
        "type": "string",
        "default": "dock",
        "list": ["dock", "minidock", "map", "bottomdock", "right-dock"],
    },
    "draw": {"wType": "checkbox", "type": "boolean", "default": False},
    # Deprecated since LWC 3.7.0
    # There is a new "print" panel
    "print": {"wType": "checkbox", "type": "boolean", "default": False},
    "measure": {"wType": "checkbox", "type": "boolean", "default": False},
    "externalSearch": {
        "wType": "list",
        "type": "string",
        "default": "",
        "list": [
            (
                "",
                tr("Disabled"),
                tr("No external address provider."),
                ("icons", "disabled.svg"),
            ),
            (
                "nominatim",
                tr("Nominatim (OSM)"),
                tr("Nominatim is using OpenStreetMap data"),
                ("icons", "osm-32-32.png"),
            ),
            (
                "google",
                tr("Google"),
                tr("Google Geocoding API. A key is required."),
                ("icons", "google.png"),
            ),
            (
                "ban",
                tr("French BAN"),
                tr("The French BAN API."),
                ":images/flags/fr.svg",
            ),
            (
                "ign",
                tr("French IGN"),
                tr("The French IGN API."),
                ":images/flags/fr.svg",
            ),
        ],
    },
    # Deprecated, it has been removed in LWC 3.8
    "zoomHistory": {"wType": "checkbox", "type": "boolean", "default": False},
    "geolocation": {"wType": "checkbox", "type": "boolean", "default": False},
    "pointTolerance": {"wType": "spinbox", "type": "integer", "default": 25},
    "lineTolerance": {"wType": "spinbox", "type": "integer", "default": 10},
    "polygonTolerance": {"wType": "spinbox", "type": "integer", "default": 5},
    "hideHeader": {"wType": "checkbox", "type": "boolean", "default": False},
    "hideMenu": {"wType": "checkbox", "type": "boolean", "default": False},
    "hideLegend": {"wType": "checkbox", "type": "boolean", "default": False},
    "hideOverview": {"wType": "checkbox", "type": "boolean", "default": False},
    "hideNavbar": {"wType": "checkbox", "type": "boolean", "default": False},
    "hideProject": {"wType": "checkbox", "type": "boolean", "default": False},
    "automatic_permalink": {
        "wType": "checkbox",
        "type": "boolean",
        "default": False,
        "use_proper_boolean": True,
        "always_export": True,
    },
    "wms_single_request_for_all_layers": {
        "wType": "checkbox",
        "type": "boolean",
        "default": False,
        "use_proper_boolean": True,
    },
    "tmTimeFrameSize": {"wType": "spinbox", "type": "integer", "default": 10},
    "tmTimeFrameType": {
        "wType": "list",
        "type": "string",
        "default": "seconds",
        "list": ["seconds", "minutes", "hours", "days", "weeks", "months", "years"],
    },
    "tmAnimationFrameLength": {"wType": "spinbox", "type": "integer", "default": 1000},
    "emptyBaselayer": {"wType": "checkbox", "type": "boolean", "default": False},
    "startupBaselayer": {"wType": "list", "type": "string", "default": "", "list": [""]},
    "limitDataToBbox": {"wType": "checkbox", "type": "boolean", "default": False},
    "datavizLocation": {
        "wType": "list",
        "type": "string",
        "default": "dock",
        "list": ["dock", "bottomdock", "right-dock"],
    },
    "datavizTemplate": {"wType": "wysiwyg", "type": "string", "default": ""},
    "theme": {
        # If the default value is changed, must be changed in the definitions python file as well
        "wType": "list",
        "type": "string",
        "default": "dark",
        "list": ["dark", "light"],
    },
    "atlasShowAtStartup": {"wType": "checkbox", "type": "boolean", "default": False},
    "atlasAutoPlay": {"wType": "checkbox", "type": "boolean", "default": False},
    "fixed_scale_overview_map": {
        "wType": "checkbox",
        "type": "boolean",
        "always_export": True,
        "default": True,
        "tooltip": tr(
            "If checked, the overview map will have a fixed scale covering "
            "the Lizmap initial extent. "
            "If not checked, the overview map will follow the scale of the "
            "main map with a smaller scale."
        )
        + " "
        + tr("New in Lizmap Web Client 3.5.3"),
        "use_proper_boolean": True,
    },
    "dxfExportEnabled": {
        "wType": "checkbox",
        "type": "boolean",
        "default": False,
        "tooltip": tr("Enable or disable the DXF export functionality globally."),
        "use_proper_boolean": True,
    },
    "allowedGroups": {
        "wType": "text",
        "type": "string",
        "default": "",
        "tooltip": tr(
            "Comma-separated list of Lizmap group IDs allowed to export DXF. "
            "If empty, all users can export."
        ),
        "always_export": True,
    },
}
