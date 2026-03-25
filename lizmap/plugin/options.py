"""Options settings"""

from typing import (
    TYPE_CHECKING,
)

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import (
    QIcon,
)

from ..config import GlobalOptionsDefinitions, LayerOptionDefinitions, LizmapConfig
from ..toolbelt.resources import (
    resources_path,
)

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog


def global_options(dlg: "LizmapDialog", lizmap_config: LizmapConfig) -> GlobalOptionsDefinitions:
    # List of ui widget for data driven actions and checking
    global_options = lizmap_config.globalOptionDefinitions
    global_options["externalSearch"]["widget"] = dlg.liExternalSearch

    # Add widgets (not done in lizmap_var to avoid dependencies on ui)
    global_options["fixed_scale_overview_map"]["widget"] = dlg.checkbox_scale_overview_map
    # Because of the logic with LWC 3.7, we are managing manually these widgets
    # global_options['mapScales']['widget'] = dlg.list_map_scales
    # global_options['minScale']['widget'] = dlg.minimum_scale
    # global_options['maxScale']['widget'] = dlg.maximum_scale
    global_options["max_scale_points"]["widget"] = dlg.max_scale_points
    global_options["max_scale_lines_polygons"]["widget"] = dlg.max_scale_lines_polygons
    global_options["hide_numeric_scale_value"]["widget"] = dlg.hide_scale_value
    global_options["acl"]["widget"] = dlg.inAcl
    global_options["initialExtent"]["widget"] = dlg.widget_initial_extent
    global_options["googleKey"]["widget"] = dlg.inGoogleKey
    global_options["googleHybrid"]["widget"] = dlg.cbGoogleHybrid
    global_options["googleSatellite"]["widget"] = dlg.cbGoogleSatellite
    global_options["googleTerrain"]["widget"] = dlg.cbGoogleTerrain
    global_options["googleStreets"]["widget"] = dlg.cbGoogleStreets
    global_options["osmMapnik"]["widget"] = dlg.cbOsmMapnik
    global_options["openTopoMap"]["widget"] = dlg.cb_open_topo_map
    global_options["bingKey"]["widget"] = dlg.inBingKey
    global_options["bingStreets"]["widget"] = dlg.cbBingStreets
    global_options["bingSatellite"]["widget"] = dlg.cbBingSatellite
    global_options["bingHybrid"]["widget"] = dlg.cbBingHybrid
    global_options["ignKey"]["widget"] = dlg.inIgnKey
    global_options["ignStreets"]["widget"] = dlg.cbIgnStreets
    global_options["ignSatellite"]["widget"] = dlg.cbIgnSatellite
    global_options["ignTerrain"]["widget"] = dlg.cbIgnTerrain
    global_options["ignCadastral"]["widget"] = dlg.cbIgnCadastral
    global_options["hideGroupCheckbox"]["widget"] = dlg.cbHideGroupCheckbox
    global_options["activateFirstMapTheme"]["widget"] = dlg.activate_first_map_theme
    global_options["popupLocation"]["widget"] = dlg.liPopupContainer
    global_options["draw"]["widget"] = dlg.activate_drawing_tools
    global_options["dxfExportEnabled"]["widget"] = dlg.checkbox_dxf_export_enabled
    global_options["allowedGroups"]["widget"] = dlg.text_dxf_allowed_groups
    # Deprecated since LWC 3.7.0
    global_options["print"]["widget"] = dlg.cbActivatePrint
    global_options["measure"]["widget"] = dlg.cbActivateMeasure
    global_options["zoomHistory"]["widget"] = dlg.cbActivateZoomHistory
    global_options["geolocation"]["widget"] = dlg.groupbox_geolocation
    global_options["geolocationPrecision"]["widget"] = dlg.checkbox_geolocation_precision
    global_options["geolocationDirection"]["widget"] = dlg.checkbox_geolocation_direction
    global_options["pointTolerance"]["widget"] = dlg.inPointTolerance
    global_options["lineTolerance"]["widget"] = dlg.inLineTolerance
    global_options["polygonTolerance"]["widget"] = dlg.inPolygonTolerance
    global_options["hideHeader"]["widget"] = dlg.cbHideHeader
    global_options["hideMenu"]["widget"] = dlg.cbHideMenu
    global_options["hideLegend"]["widget"] = dlg.cbHideLegend
    global_options["hideOverview"]["widget"] = dlg.cbHideOverview
    global_options["hideNavbar"]["widget"] = dlg.cbHideNavbar
    global_options["hideProject"]["widget"] = dlg.cbHideProject
    global_options["automatic_permalink"]["widget"] = dlg.automatic_permalink
    global_options["wms_single_request_for_all_layers"]["widget"] = dlg.checkbox_wms_single_request_all_layers
    global_options["exclude_basemaps_from_single_wms"]["widget"] = (
        dlg.checkbox_exclude_basemaps_from_single_wms
    )

    global_options["tmTimeFrameSize"]["widget"] = dlg.inTimeFrameSize
    global_options["tmTimeFrameType"]["widget"] = dlg.liTimeFrameType
    global_options["tmAnimationFrameLength"]["widget"] = dlg.inAnimationFrameLength
    global_options["emptyBaselayer"]["widget"] = dlg.cbAddEmptyBaselayer
    global_options["startupBaselayer"]["widget"] = dlg.cbStartupBaselayer
    global_options["limitDataToBbox"]["widget"] = dlg.cbLimitDataToBbox
    global_options["datavizLocation"]["widget"] = dlg.liDatavizContainer
    global_options["datavizTemplate"]["widget"] = dlg.dataviz_html_template
    global_options["theme"]["widget"] = dlg.combo_theme
    global_options["atlasShowAtStartup"]["widget"] = dlg.atlasShowAtStartup
    global_options["atlasAutoPlay"]["widget"] = dlg.atlasAutoPlay

    return global_options


def layer_options(
    dlg: "LizmapDialog",
    lizmap_config: LizmapConfig,
    global_options: GlobalOptionsDefinitions,
) -> LayerOptionDefinitions:
    # List of ui widget for data driven actions and checking
    layer_options_list = lizmap_config.layerOptionDefinitions
    layer_options_list["legend_image_option"]["widget"] = dlg.combo_legend_option
    layer_options_list["popupSource"]["widget"] = dlg.liPopupSource
    layer_options_list["imageFormat"]["widget"] = dlg.liImageFormat

    # Add widget information
    layer_options_list["title"]["widget"] = dlg.inLayerTitle
    layer_options_list["abstract"]["widget"] = dlg.teLayerAbstract
    layer_options_list["link"]["widget"] = dlg.inLayerLink
    layer_options_list["minScale"]["widget"] = None
    layer_options_list["maxScale"]["widget"] = None
    layer_options_list["toggled"]["widget"] = dlg.cbToggled
    layer_options_list["group_visibility"]["widget"] = dlg.list_group_visibility
    layer_options_list["popup"]["widget"] = dlg.checkbox_popup
    layer_options_list["popupFrame"]["widget"] = dlg.frame_layer_popup
    layer_options_list["popupTemplate"]["widget"] = None
    layer_options_list["popupMaxFeatures"]["widget"] = dlg.sbPopupMaxFeatures
    layer_options_list["children_lizmap_features_table"]["widget"] = dlg.children_lizmap_features_table
    layer_options_list["popupDisplayChildren"]["widget"] = dlg.popup_display_children
    layer_options_list["popup_allow_download"]["widget"] = dlg.checkbox_popup_allow_download
    layer_options_list["groupAsLayer"]["widget"] = dlg.cbGroupAsLayer
    layer_options_list["baseLayer"]["widget"] = dlg.cbLayerIsBaseLayer
    layer_options_list["displayInLegend"]["widget"] = dlg.cbDisplayInLegend
    layer_options_list["singleTile"]["widget"] = dlg.cbSingleTile
    layer_options_list["cached"]["widget"] = dlg.checkbox_server_cache
    layer_options_list["serverFrame"]["widget"] = dlg.server_cache_frame
    layer_options_list["cacheExpiration"]["widget"] = dlg.inCacheExpiration
    layer_options_list["metatileSize"]["widget"] = dlg.inMetatileSize
    layer_options_list["clientCacheExpiration"]["widget"] = dlg.inClientCacheExpiration
    layer_options_list["externalWmsToggle"]["widget"] = dlg.cbExternalWms
    layer_options_list["sourceRepository"]["widget"] = dlg.inSourceRepository
    layer_options_list["sourceProject"]["widget"] = dlg.inSourceProject

    # Fill the combobox from the Lizmap API
    for combo_item in ("legend_image_option", "popupSource", "imageFormat", "externalSearch"):
        item_info = layer_options_list.get(combo_item)
        if not item_info:
            item_info = global_options.get(combo_item)

        if not item_info:
            # This should not happen
            raise Exception("Unknown type for item_info")

        for option in item_info["list"]:
            data, label, tooltip, icon = option
            item_info["widget"].addItem(label, data)
            index = item_info["widget"].findData(data)

            if tooltip:
                # noinspection PyUnresolvedReferences
                item_info["widget"].setItemData(index, tooltip, Qt.ItemDataRole.ToolTipRole)

            if icon:
                if isinstance(icon, str):
                    # From QGIS resources file
                    pass
                else:
                    # It's a list, from the plugin
                    icon = resources_path(*icon)
                item_info["widget"].setItemIcon(index, QIcon(icon))

    return layer_options_list
