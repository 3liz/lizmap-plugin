"""Configure dialog depending on the LWC version"""

import json

from collections import OrderedDict
from typing import (
    TYPE_CHECKING,
    Dict,
    Protocol,
)

from qgis.core import (
    Qgis,
    QgsSettings,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import (
    QBrush,
    QColor,
    QStandardItem,
)
from qgis.PyQt.QtWidgets import QWidget

from ..definitions.definitions import LwcVersions
from ..dialogs.main import LizmapDialog
from ..qt_style_sheets import NEW_FEATURE_COLOR, NEW_FEATURE_CSS
from ..toolbelt.plugin import lizmap_user_folder

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog

from .. import logger


class LizmapProtocol(Protocol):
    dlg: "LizmapDialog"
    layers_table: Dict


class LwcVersionManager(LizmapProtocol):
    def initialize_lwc_versions(self, lwc_version: LwcVersions):
        self._version = lwc_version
        self._lwc_versions = configure_lwc_versions(self.dlg)

    def current_lwc_version(self) -> LwcVersions:
        """Return the current selected LWC version from the server."""
        if self._version:
            # For tests, return the version given in the constructor
            return self._version

        version = self.dlg.current_lwc_version()
        if version is None:
            # Fallback to latest version if no server is configured
            return LwcVersions.latest()

        return version

    def lwc_version_changed(self):
        """When the version has changed in the selector, we update features with the blue background."""
        # self.check_webdav()
        current_version = self.current_lwc_version()
        if not current_version:
            logger.info(
                "No LWC version currently defined in the combobox, skipping LWC target version changed."
            )
            self.dlg.refresh_helper_target_version(None)
            return

        logger.debug("Saving new value about the LWC target version : {}".format(current_version.value))
        QgsSettings().setValue("lizmap/lizmap_web_client_version", str(current_version.value))

        self.dlg.refresh_helper_target_version(current_version)

        # New print panel
        # The checkbox is removed since LWC 3.7.0
        self.dlg.cbActivatePrint.setVisible(current_version <= LwcVersions.Lizmap_3_6)
        self.dlg.cbActivatePrint.setEnabled(current_version <= LwcVersions.Lizmap_3_6)

        # The checkbox is removed since LWC 3.8.0
        self.dlg.cbActivateZoomHistory.setVisible(current_version <= LwcVersions.Lizmap_3_7)
        self.dlg.cbActivateZoomHistory.setEnabled(current_version <= LwcVersions.Lizmap_3_7)

        found = False
        for lwc_version, items in self._lwc_versions.items():
            if found:
                # Set some blue
                for item in items:
                    if isinstance(item, QWidget):
                        item.setStyleSheet(NEW_FEATURE_CSS)
                    elif isinstance(item, QStandardItem):
                        # QComboBox
                        brush = QBrush()
                        # noinspection PyUnresolvedReferences
                        brush.setStyle(Qt.BrushStyle.SolidPattern)
                        brush.setColor(QColor(NEW_FEATURE_COLOR))
                        item.setBackground(brush)
            else:
                # Remove some blue
                for item in items:
                    if isinstance(item, QWidget):
                        item.setStyleSheet("")
                    elif isinstance(item, QStandardItem):
                        # QComboBox
                        item.setBackground(QBrush())

            if lwc_version == current_version:
                found = True

        # Change in all table manager too
        for key in self.layers_table:
            manager = self.layers_table[key].get("manager")
            if manager:
                manager.set_lwc_version(current_version)

        # Compare the LWC version with the current QGIS Desktop version and the release JSON file
        version_file = lizmap_user_folder().joinpath("released_versions.json")
        if not version_file.exists():
            return

        with open(version_file, encoding="utf8") as json_file:
            json_content = json.loads(json_file.read())

        for lzm_version in json_content:
            if lzm_version["branch"] != current_version.value:
                continue

            # TODO: check type of returned value (int)
            qgis_min = lzm_version.get("qgis_min_version_recommended")
            qgis_max = lzm_version.get("qgis_max_version_recommended")
            if not (qgis_min or qgis_max):
                break

            if qgis_min <= Qgis.versionInt() < qgis_max:
                self.dlg.qgis_and_lwc_versions_issue.setVisible(False)
            else:
                self.dlg.qgis_and_lwc_versions_issue.setVisible(True)


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
        dlg.liPopupSource.model().item(dlg.liPopupSource.findData("form")),
        dlg.label_filter_polygon,
        dlg.filter_polygon_by_user,
        dlg.checkbox_scale_overview_map,
    ]
    lwc_versions[LwcVersions.Lizmap_3_6] = [
        dlg.checkbox_popup_allow_download,
        dlg.cb_open_topo_map,
        dlg.combo_legend_option.model().item(dlg.combo_legend_option.findData("expand_at_startup")),
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
        # Portfolio
        dlg.label_portfolios_panel,
        # Export DXF panel
        dlg.label_dxf_export_panel,
        dlg.label_dxf_export_enabled,
        dlg.checkbox_dxf_export_enabled,
        dlg.label_dxf_allowed_groups,
        dlg.text_dxf_allowed_groups,
        dlg.button_dxf_wizard_group,
        dlg.label_dxf_layers_info,
    ]
    lwc_versions[LwcVersions.Lizmap_3_11] = []

    return lwc_versions
