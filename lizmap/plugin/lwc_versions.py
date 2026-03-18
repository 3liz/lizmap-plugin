""" Configure dialog depending on the LWC version
"""
from collections import OrderedDict
from typing import TYPE_CHECKING

from ..definitions.definitions import LwcVersions

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog


def configure_lwc_versions(dlg: "LizmapDialog") -> OrderedDict:
    # Manage LWC versions combo
    lwc_versions = OrderedDict()
    lwc_versions[LwcVersions.Lizmap_3_1] = []
    lwc_versions[LwcVersions.Lizmap_3_2] = [
        dlg.label_max_feature_popup,
        dlg.label_dataviz,
        dlg.label_atlas,
    ]
    lwc_versions[LwcVersions.Lizmap_3_3] = [
        dlg.label_form_filter,
        dlg.btQgisPopupFromForm,
    ]
    lwc_versions[LwcVersions.Lizmap_3_4] = [
        dlg.label_atlas_34,
        dlg.list_group_visibility,
        dlg.activate_first_map_theme,
        dlg.activate_drawing_tools,
        # Actions
        dlg.label_help_action,
    ]
    lwc_versions[LwcVersions.Lizmap_3_5] = [
        dlg.liPopupSource.model().item(
            dlg.liPopupSource.findData('form')
        ),
        dlg.label_filter_polygon,
        dlg.filter_polygon_by_user,
        dlg.checkbox_scale_overview_map,
    ]
    lwc_versions[LwcVersions.Lizmap_3_6] = [
        dlg.checkbox_popup_allow_download,
        dlg.cb_open_topo_map,
        dlg.combo_legend_option.model().item(
            dlg.combo_legend_option.findData('expand_at_startup')
        ),
        dlg.button_wizard_group_visibility_project,
        dlg.button_wizard_group_visibility_layer,
        dlg.label_helper_dataviz,
        dlg.enable_dataviz_preview,
    ]
    lwc_versions[LwcVersions.Lizmap_3_7] = [
        # Layout panel
        dlg.checkbox_default_print,
        dlg.label_layout_panel,
        dlg.label_layout_panel_description,
        dlg.edit_layout_form_button,
        dlg.up_layout_form_button,
        dlg.down_layout_form_button,
        # Drag drop dataviz designer
        dlg.label_dnd_dataviz_help,
        dlg.button_add_dd_dataviz,
        dlg.button_remove_dd_dataviz,
        dlg.button_edit_dd_dataviz,
        dlg.button_add_plot,
        dlg.combo_plots,
        # Base-layers
        dlg.add_group_empty,
        dlg.add_group_baselayers,
        dlg.predefined_baselayers,
        # New scopes in actions
        dlg.label_action_scope_layer_project,
        # Scales
        dlg.use_native_scales,
        dlg.hide_scale_value,
    ]
    lwc_versions[LwcVersions.Lizmap_3_8] = [
        # Single WMS
        dlg.checkbox_wms_single_request_all_layers,
        # Permalink, will be backported to 3.7, but wait a little before adding it to the 3.7 list
        dlg.automatic_permalink,
    ]
    lwc_versions[LwcVersions.Lizmap_3_9] = [
        dlg.group_box_max_scale_zoom,
        dlg.children_lizmap_features_table,
    ]
    lwc_versions[LwcVersions.Lizmap_3_10] = [
        dlg.checkbox_geolocation_precision,
        dlg.checkbox_geolocation_direction,
        # Exclude basemaps from single WMS
        dlg.checkbox_exclude_basemaps_from_single_wms,
        # Export DXF panel
        dlg.label_dxf_export_panel,
        dlg.label_dxf_export_enabled,
        dlg.checkbox_dxf_export_enabled,
        dlg.label_dxf_allowed_groups,
        dlg.text_dxf_allowed_groups,
        dlg.button_dxf_wizard_group,
        dlg.label_dxf_layers_info,
    ]
    lwc_versions[LwcVersions.Lizmap_3_11] = [
    ]

    return lwc_versions
