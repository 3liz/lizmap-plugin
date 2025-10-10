from typing import (
    TypedDict,
)

from lizmap.definitions.definitions import LwcVersions
from lizmap.toolbelt.i18n import tr

from .models import _Item


class LayerOptionDefinitions(TypedDict):
    title: _Item
    abstract: _Item
    link: _Item
    minScale: _Item
    maxScale: _Item
    toggled: _Item
    popup: _Item
    popupFrame: _Item
    popupSource: _Item
    popupTemplate: _Item
    popupMaxFeatures: _Item
    children_lizmap_features_table: _Item
    popupDisplayChildren: _Item
    popup_allow_download: _Item
    noLegendImage: _Item
    legend_image_option: _Item
    groupAsLayer: _Item
    baseLayer: _Item
    displayInLegend: _Item
    group_visibility: _Item
    singleTile: _Item
    imageFormat: _Item
    cached: _Item
    serverFrame: _Item
    cacheExpiration: _Item
    metatileSize: _Item
    clientCacheExpiration: _Item
    externalWmsToggle: _Item
    sourceRepository: _Item
    sourceProject: _Item


layerOptionDefinitions = {
    "title": {"wType": "text", "type": "string", "default": "", "isMetadata": True},
    "abstract": {
        # Last textarea from the plugin, can be cleaned in plugin.py after it
        "wType": "textarea",
        "type": "string",
        "default": "",
        "isMetadata": True,
    },
    "link": {"wType": "text", "type": "string", "default": "", "isMetadata": False},
    "minScale": {"wType": "text", "type": "integer", "default": 1},
    "maxScale": {"wType": "text", "type": "integer", "default": 1000000000000},
    "toggled": {"wType": "checkbox", "type": "boolean", "default": True},
    "popup": {"wType": "checkbox", "type": "boolean", "default": False, "children": "popupFrame"},
    "popupFrame": {
        "comment": (
            "This is not included in the CFG, I think it is used only because of parent/children, todo clean"
        ),
        "wType": "frame",
        "type": None,
        "default": None,
        "parent": "popup",
    },
    "popupSource": {
        "wType": "list",
        "type": "string",
        "default": "auto",
        "list": [
            (
                "auto",
                tr("Automatic"),
                tr(
                    "The table is built automatically. The only way to customize it is to use alias, "
                    "attribute order and QGIS server settings about WMS."
                ),
                ":images/themes/default/mIconTableLayer.svg",
            ),
            (
                "lizmap",
                "Lizmap HTML",
                tr(
                    "Read the documentation on how to write a Lizmap popup with HTML. "
                    "The QGIS HTML popup is more powerful because it's possible to use expression."
                ),
                ":images/themes/default/mLayoutItemHtml.svg",
            ),
            (
                "qgis",
                tr("QGIS HTML maptip"),
                tr(
                    "You would need to write the maptip with HTML and QGIS expressions. "
                    "If you don't want to start from scratch, you can generate the template using the default "
                    "table or from the drag&drop form layout."
                ),
                ":images/themes/default/mActionMapTips.svg",
            ),
            (
                "form",
                tr("QGIS Drag&Drop form"),
                tr(
                    "Same as the QGIS HTML maptip, but it will use straight the drag&drop form layout. "
                    "You cannot customize the HTML in the vector layer properties."
                ),
                ":images/themes/default/mActionFormView.svg",
            ),
        ],
    },
    "popupTemplate": {"wType": "text", "type": "string", "default": ""},
    "popupMaxFeatures": {"wType": "spinbox", "type": "integer", "default": 10},
    "children_lizmap_features_table": {
        "wType": "radio",
        "type": "boolean",
        "default": True,
        "use_proper_boolean": True,
    },
    "popupDisplayChildren": {
        "wType": "radio",
        "type": "boolean",
        "default": False,
    },
    "popup_allow_download": {
        "wType": "checkbox",
        "type": "boolean",
        "default": True,
        "tooltip": tr(
            "If checked, a download button will be added in the popup to allow GPX, KML and GeoJSON export"
        ),
        "use_proper_boolean": True,
    },
    "noLegendImage": {
        "wType": "checkbox",
        "type": "boolean",
        "default": False,
        "max_version": LwcVersions.Lizmap_3_5,
    },
    "legend_image_option": {
        "wType": "list",
        "type": "string",
        "default": "hide_at_startup",
        "list": [
            (
                "hide_at_startup",
                tr("Hide legend image at startup"),
                tr("The layer legend can be displayed by clicking on the arrow button."),
                ":images/themes/default/mActionHideAllLayers.svg",
            ),
            (
                "expand_at_startup",
                tr("Show legend image at startup"),
                tr("The legend image will be displayed be default at startup."),
                ":images/themes/default/mActionShowAllLayers.svg",
            ),
            (
                "disabled",
                tr("Disable the legend image"),
                tr("The legend image won't be available for display."),
                ":images/themes/default/mTaskCancel.svg",
            ),
        ],
        "min_version": LwcVersions.Lizmap_3_6,
    },
    "groupAsLayer": {"wType": "checkbox", "type": "boolean", "default": False},
    "baseLayer": {"wType": "checkbox", "type": "boolean", "default": False},
    "displayInLegend": {"wType": "checkbox", "type": "boolean", "default": True},
    "group_visibility": {"wType": "text", "type": "list", "default": []},
    "singleTile": {
        "wType": "checkbox",
        "type": "boolean",
        "default": True,
        "children": "cached",
        "exclusive": True,
    },
    "imageFormat": {
        "wType": "list",
        "type": "string",
        "default": "image/png",
        "list": [
            (
                "image/png",
                "PNG",
                None,
                None,
            ),
            (
                "image/png; mode=16bit",
                "PNG, 16 bit",
                None,
                None,
            ),
            (
                "image/png; mode=8bit",
                "PNG, 8 bit",
                None,
                None,
            ),
            (
                "image/webp",
                "WebP",
                None,
                None,
            ),
            (
                "image/jpeg",
                "JPEG",
                None,
                None,
            ),
        ],
    },
    "cached": {
        "wType": "checkbox",
        "type": "boolean",
        "default": False,
        "children": "serverFrame",
        "parent": "singleTile",
    },
    "serverFrame": {
        "comment": (
            "This is not included in the CFG, I think it is used only because of parent/children, todo clean"
        ),
        "wType": "frame",
        "type": None,
        "default": None,
        "parent": "cached",
    },
    "cacheExpiration": {"wType": "spinbox", "type": "integer", "default": 0},
    "metatileSize": {"wType": "text", "type": "string", "default": ""},
    "clientCacheExpiration": {"wType": "spinbox", "type": "integer", "default": 300},
    "externalWmsToggle": {"wType": "checkbox", "type": "boolean", "default": False},
    "sourceRepository": {"wType": "text", "type": "string", "default": "", "_api": False},
    "sourceProject": {"wType": "text", "type": "string", "default": "", "_api": False},
}
