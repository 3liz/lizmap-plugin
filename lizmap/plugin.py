__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import logging
import os
import re
import tempfile
import zipfile

from collections import OrderedDict
from functools import partial
from os.path import relpath
from pathlib import Path
from shutil import copyfile
from typing import Dict, List, Optional, Tuple, Union

from pyplugin_installer.version_compare import compareVersions
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsCoordinateReferenceSystem,
    QgsEditFormConfig,
    QgsExpression,
    QgsFileDownloader,
    QgsLayerTree,
    QgsLayerTreeGroup,
    QgsMapLayer,
    QgsMapLayerModel,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsSettings,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsFileWidget
from qgis.PyQt.QtCore import QEventLoop
from qgis.PyQt.QtWidgets import QApplication, QFileDialog

from lizmap.dialogs.news import NewConfigDialog
from lizmap.dialogs.server_wizard import CreateFolderWizard

if Qgis.QGIS_VERSION_INT >= 32200:
    from qgis.core import QgsIconUtils

from qgis.PyQt.QtCore import (
    QCoreApplication,
    QStorageInfo,
    Qt,
    QTranslator,
    QUrl,
)
from qgis.PyQt.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QPixmap,
    QStandardItem,
    QTextCursor,
)
from qgis.PyQt.QtWidgets import (
    QAction,
    QDialogButtonBox,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidgetItem,
    QWidget,
)
from qgis.utils import OverrideCursor
from qgis.utils import plugins as all_plugins

from lizmap.definitions.atlas import AtlasDefinitions
from lizmap.definitions.attribute_table import AttributeTableDefinitions
from lizmap.definitions.dataviz import DatavizDefinitions, Theme
from lizmap.definitions.definitions import (
    DEV_VERSION_PREFIX,
    DURATION_MESSAGE_BAR,
    DURATION_SUCCESS_BAR,
    DURATION_WARNING_BAR,
    UNSTABLE_VERSION_PREFIX,
    GroupNames,
    Html,
    IgnLayer,
    IgnLayers,
    LayerProperties,
    LwcVersions,
    PredefinedGroup,
    ReleaseStatus,
    RepositoryComboData,
    ServerComboData,
)
from lizmap.definitions.edition import EditionDefinitions
from lizmap.definitions.filter_by_form import FilterByFormDefinitions
from lizmap.definitions.filter_by_login import FilterByLoginDefinitions
from lizmap.definitions.filter_by_polygon import FilterByPolygonDefinitions
from lizmap.definitions.layouts import LayoutsDefinitions
from lizmap.definitions.lizmap_cloud import (
    CLOUD_MAX_PARENT_FOLDER,
    CLOUD_NAME,
    CLOUD_QGIS_MIN_RECOMMENDED,
    TRAINING_PROJECT,
    TRAINING_ZIP,
    WORKSHOP_DOMAINS,
    WORKSHOP_FOLDER_ID,
    WORKSHOP_FOLDER_PATH,
    WorkshopType,
)
from lizmap.definitions.locate_by_layer import LocateByLayerDefinitions
from lizmap.definitions.online_help import (
    MAPPING_INDEX_DOC,
    Panels,
    online_cloud_help,
    online_lwc_help,
)
from lizmap.definitions.qgis_settings import Settings
from lizmap.definitions.time_manager import TimeManagerDefinitions
from lizmap.definitions.tooltip import ToolTipDefinitions
from lizmap.dialogs.dock_html_preview import HtmlPreview
from lizmap.dialogs.html_editor import HtmlEditorDialog
from lizmap.dialogs.html_maptip import HtmlMapTipDialog
from lizmap.dialogs.lizmap_popup import LizmapPopupDialog
from lizmap.dialogs.main import LizmapDialog
from lizmap.dialogs.wizard_group import WizardGroupDialog
from lizmap.drag_drop_dataviz_manager import DragDropDatavizManager
from lizmap.forms.atlas_edition import AtlasEditionDialog
from lizmap.forms.attribute_table_edition import AttributeTableEditionDialog
from lizmap.forms.dataviz_edition import DatavizEditionDialog
from lizmap.forms.edition_edition import EditionLayerDialog
from lizmap.forms.filter_by_form_edition import FilterByFormEditionDialog
from lizmap.forms.filter_by_login import FilterByLoginEditionDialog
from lizmap.forms.filter_by_polygon import FilterByPolygonEditionDialog
from lizmap.forms.layout_edition import LayoutEditionDialog
from lizmap.forms.locate_layer_edition import LocateLayerEditionDialog
from lizmap.forms.time_manager_edition import TimeManagerEditionDialog
from lizmap.forms.tooltip_edition import ToolTipEditionDialog
from lizmap.lizmap_api.config import LizmapConfig
from lizmap.ogc_project_validity import OgcProjectValidity
from lizmap.project_checker_tools import (
    ALLOW_PARENT_FOLDER,
    FORCE_LOCAL_FOLDER,
    FORCE_PG_USER_PASS,
    PREVENT_AUTH_DB,
    PREVENT_ECW,
    PREVENT_OTHER_DRIVE,
    PREVENT_SERVICE,
    count_legend_items,
    duplicated_label_legend,
    duplicated_layer_name_or_group,
    duplicated_layer_with_filter_legend,
    duplicated_rule_key_legend,
    project_invalid_pk,
    project_safeguards_checks,
    project_tos_layers,
    project_trust_layer_metadata,
    simplify_provider_side,
    trailing_layer_group_name,
    use_estimated_metadata,
)
from lizmap.saas import check_project_ssl_postgis, is_lizmap_cloud, webdav_url
from lizmap.table_manager.base import TableManager
from lizmap.table_manager.dataviz import TableManagerDataviz
from lizmap.table_manager.layouts import TableManagerLayouts
from lizmap.toolbelt.convert import cast_to_group, cast_to_layer
from lizmap.widgets.check_project import Check, SourceField
from lizmap.widgets.project_tools import (
    empty_baselayers,
    is_layer_published_wfs,
    is_layer_wms_excluded,
)

try:
    from lizmap.plugin_manager import QgisPluginManager
    QGIS_PLUGIN_MANAGER = True
except ModuleNotFoundError:
    # In a standalone application
    QGIS_PLUGIN_MANAGER = False

from qgis.core import QgsProjectServerValidator

from lizmap.qt_style_sheets import NEW_FEATURE_COLOR, NEW_FEATURE_CSS
from lizmap.server_lwc import MAX_DAYS, ServerManager
from lizmap.toolbelt.convert import to_bool
from lizmap.toolbelt.custom_logging import (
    add_logging_handler_once,
    setup_logger,
)
from lizmap.toolbelt.git import current_git_hash, next_git_tag
from lizmap.toolbelt.i18n import setup_translation, tr
from lizmap.toolbelt.layer import (
    get_layer_wms_parameters,
    layer_property,
    relative_path,
    remove_all_ghost_layers,
)
from lizmap.toolbelt.lizmap import convert_lizmap_popup
from lizmap.toolbelt.plugin import lizmap_user_folder
from lizmap.toolbelt.resources import plugin_name, plugin_path, resources_path
from lizmap.toolbelt.strings import human_size, path_to_url, unaccent
from lizmap.toolbelt.version import (
    format_qgis_version,
    format_version_integer,
    qgis_version,
    version,
)
from lizmap.tooltip import Tooltip
from lizmap.version_checker import VersionChecker

if qgis_version() >= 32200:
    from lizmap.server_dav import WebDav

LOGGER = logging.getLogger(plugin_name())
VERSION_URL = 'https://raw.githubusercontent.com/3liz/lizmap-web-client/versions/versions.json'
# To try a local file
# VERSION_URL = 'file:///home/etienne/.local/share/QGIS/QGIS3/profiles/default/Lizmap/released_versions.json'


class Lizmap:

    def __init__(self, iface, lwc_version: LwcVersions = None):
        """Constructor of the Lizmap plugin."""
        LOGGER.info("Plugin starting")
        self.iface = iface
        # noinspection PyArgumentList
        self.project = QgsProject.instance()

        # Must only be used in tests
        # In production, version is coming from the UI, according to the current server selected
        self._version = lwc_version

        # Keep it for a few months
        # 2023/04/15
        QgsSettings().remove('lizmap/instance_target_repository')
        # 04/01/2022
        QgsSettings().remove('lizmap/instance_target_url_authid')

        if to_bool(os.getenv("LIZMAP_NORMAL_MODE"), default_value=False):
            QgsSettings().setValue(Settings.key(Settings.BeginnerMode), False)
            QgsSettings().setValue(Settings.key(Settings.PreventPgService), False)

        # Set some default settings when loading the plugin
        beginner_mode = QgsSettings().value(Settings.key(Settings.BeginnerMode), defaultValue=None)
        if beginner_mode is None:
            QgsSettings().setValue(Settings.key(Settings.BeginnerMode), True)

        prevent_ecw = QgsSettings().value(Settings.key(Settings.PreventEcw), defaultValue=None)
        if prevent_ecw is None:
            QgsSettings().setValue(Settings.key(Settings.PreventEcw), True)

        prevent_auth_id = QgsSettings().value(Settings.key(Settings.PreventPgAuthDb), defaultValue=None)
        if prevent_auth_id is None:
            QgsSettings().setValue(Settings.key(Settings.PreventPgAuthDb), True)

        prevent_service = QgsSettings().value(Settings.key(Settings.PreventPgService), defaultValue=None)
        if prevent_service is None:
            QgsSettings().setValue(Settings.key(Settings.PreventPgService), True)

        force_pg_user_pass = QgsSettings().value(Settings.key(Settings.ForcePgUserPass), defaultValue=None)
        if force_pg_user_pass is None:
            QgsSettings().setValue(Settings.key(Settings.ForcePgUserPass), True)

        prevent_other_drive = QgsSettings().value(Settings.key(Settings.PreventDrive), defaultValue=None)
        if prevent_other_drive is None:
            QgsSettings().setValue(Settings.key(Settings.PreventDrive), True)

        allow_parent_folder = QgsSettings().value(Settings.key(Settings.AllowParentFolder), defaultValue=None)
        if allow_parent_folder is None:
            QgsSettings().setValue(Settings.key(Settings.AllowParentFolder), False)

        parent_folder = QgsSettings().value(Settings.key(Settings.NumberParentFolder), defaultValue=None)
        if parent_folder is None:
            QgsSettings().setValue(Settings.key(Settings.NumberParentFolder), 2)

        # Connect the current project filepath
        self.current_path = None
        # noinspection PyUnresolvedReferences
        self.project.fileNameChanged.connect(self.filename_changed)
        self.project.projectSaved.connect(self.project_saved)
        self.filename_changed()
        self.update_plugin = None

        setup_logger(plugin_name())

        locale, file_path = setup_translation('lizmap_qgis_plugin_{}.qm', plugin_path('i18n'))
        LOGGER.info("Language in QGIS : {}".format(locale))

        if file_path:
            self.translator = QTranslator()
            self.translator.load(file_path)
            QCoreApplication.installTranslator(self.translator)

        lizmap_config = LizmapConfig(project=self.project)

        self.version = version()
        self.is_dev_version = any(item in self.version for item in UNSTABLE_VERSION_PREFIX)
        self.dlg = LizmapDialog(is_dev_version=self.is_dev_version, lwc_version=self._version)

        if Qgis.QGIS_VERSION_INT >= 32200:
            self.webdav = WebDav()
            # Give the dialog only the first time
            self.webdav.setup_webdav_dialog(self.dlg)
        else:
            self.webdav = None
        # self.check_webdav()

        self.dock_html_preview = None
        self.version_checker = None
        if self.is_dev_version:

            # File handler for logging
            temp_dir = Path(tempfile.gettempdir()).joinpath('QGIS_Lizmap')
            if not temp_dir.exists():
                temp_dir.mkdir()

            if not to_bool(os.getenv("CI"), default_value=False):
                file_handler = logging.FileHandler(temp_dir.joinpath("lizmap.log"))
                file_handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(formatter)
                add_logging_handler_once(LOGGER, file_handler)
                LOGGER.debug(
                    "The directory <a href='file://{0}'>{0}</a> is currently used for file logging.".format(temp_dir))

            # All logs
            def write_log_message(message, tag, level):
                """ Write all tabs from QGIS to files. """
                temp_dir_log = Path(tempfile.gettempdir()).joinpath('QGIS_Lizmap')
                with open(temp_dir_log.joinpath("all.log"), 'a') as log_file:
                    log_file.write('{tag}({level}): {message}'.format(tag=tag, level=level, message=message))

            QgsApplication.messageLog().messageReceived.connect(write_log_message)

            self.dlg.setWindowTitle('Lizmap branch {}, commit {}, next {}'.format(
                self.version, current_git_hash(), next_git_tag()))

        # Make the IGN french orthophoto visible only for dev or for French language user
        # locale can be "fr" or "fr_FR"
        french_buttons = (
            # Exception for "orthophoto" to be always displayed.
            # Useful for workshop in English or also low-scale map worldwide
            # self.dlg.button_ign_orthophoto,
            self.dlg.button_ign_plan,
            self.dlg.button_ign_cadastre,
        )
        for button in french_buttons:
            button.setVisible(locale[0:2].lower() == 'fr' or self.is_dev_version)
            button.setIcon(QIcon(':images/flags/fr.svg'))

        self.layers_table = dict()

        # List of ui widget for data driven actions and checking
        self.global_options = lizmap_config.globalOptionDefinitions
        self.global_options['externalSearch']['widget'] = self.dlg.liExternalSearch

        # List of ui widget for data driven actions and checking
        self.layer_options_list = lizmap_config.layerOptionDefinitions
        self.layer_options_list['legend_image_option']['widget'] = self.dlg.combo_legend_option
        self.layer_options_list['popupSource']['widget'] = self.dlg.liPopupSource
        self.layer_options_list['imageFormat']['widget'] = self.dlg.liImageFormat

        # Fill the combobox from the Lizmap API
        for combo_item in ('legend_image_option', 'popupSource', 'imageFormat', 'externalSearch'):

            item_info = self.layer_options_list.get(combo_item)
            if not item_info:
                item_info = self.global_options.get(combo_item)

            if not item_info:
                # This should not happen
                raise Exception('Unknown type for item_info')

            for option in item_info['list']:
                data, label, tooltip, icon = option
                item_info['widget'].addItem(label, data)
                index = item_info['widget'].findData(data)

                if tooltip:
                    # noinspection PyUnresolvedReferences
                    item_info['widget'].setItemData(index, tooltip, Qt.ToolTipRole)

                if icon:
                    if isinstance(icon, str):
                        # From QGIS resources file
                        pass
                    else:
                        # It's a list, from the plugin
                        icon = resources_path(*icon)
                    item_info['widget'].setItemIcon(index, QIcon(icon))

        # Manage LWC versions combo
        self.dlg.label_lwc_version.setStyleSheet(NEW_FEATURE_CSS)
        self.lwc_versions = OrderedDict()
        self.lwc_versions[LwcVersions.Lizmap_3_1] = []
        self.lwc_versions[LwcVersions.Lizmap_3_2] = [
            self.dlg.label_max_feature_popup,
            self.dlg.label_dataviz,
            self.dlg.label_atlas,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_3] = [
            self.dlg.label_form_filter,
            self.dlg.btQgisPopupFromForm,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_4] = [
            self.dlg.label_atlas_34,
            self.dlg.list_group_visibility,
            self.dlg.activate_first_map_theme,
            self.dlg.activate_drawing_tools,
            # Actions
            self.dlg.label_help_action,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_5] = [
            self.dlg.liPopupSource.model().item(
                self.dlg.liPopupSource.findData('form')
            ),
            self.dlg.label_filter_polygon,
            self.dlg.filter_polygon_by_user,
            self.dlg.checkbox_scale_overview_map,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_6] = [
            self.dlg.checkbox_popup_allow_download,
            self.dlg.cb_open_topo_map,
            self.dlg.combo_legend_option.model().item(
                self.dlg.combo_legend_option.findData('expand_at_startup')
            ),
            self.dlg.button_wizard_group_visibility_project,
            self.dlg.button_wizard_group_visibility_layer,
            self.dlg.label_helper_dataviz,
            self.dlg.enable_dataviz_preview,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_7] = [
            # Layout panel
            self.dlg.checkbox_default_print,
            self.dlg.label_layout_panel,
            self.dlg.label_layout_panel_description,
            self.dlg.edit_layout_form_button,
            self.dlg.up_layout_form_button,
            self.dlg.down_layout_form_button,
            # Drag drop dataviz designer
            self.dlg.label_dnd_dataviz_help,
            self.dlg.button_add_dd_dataviz,
            self.dlg.button_remove_dd_dataviz,
            self.dlg.button_edit_dd_dataviz,
            self.dlg.button_add_plot,
            self.dlg.combo_plots,
            # Base-layers
            self.dlg.add_group_empty,
            self.dlg.add_group_baselayers,
            self.dlg.predefined_baselayers,
            # New scopes in actions
            self.dlg.label_action_scope_layer_project,
            # Scales
            self.dlg.use_native_scales,
            self.dlg.hide_scale_value,
        ]
        self.lwc_versions[LwcVersions.Lizmap_3_8] = [
            # Single WMS
            self.dlg.checkbox_wms_single_request_all_layers,
            # Permalink, will be backported to 3.7, but wait a little before adding it to the 3.7 list
            self.dlg.automatic_permalink,
        ]

        self.lizmap_cloud = [
            self.dlg.label_lizmap_search_grant,
            self.dlg.label_safe_lizmap_cloud,
        ]

        # Add widgets (not done in lizmap_var to avoid dependencies on ui)
        self.global_options['fixed_scale_overview_map']['widget'] = self.dlg.checkbox_scale_overview_map
        # Because of the logic with LWC 3.7, we are managing manually these widgets
        # self.global_options['mapScales']['widget'] = self.dlg.list_map_scales
        # self.global_options['minScale']['widget'] = self.dlg.minimum_scale
        # self.global_options['maxScale']['widget'] = self.dlg.maximum_scale
        self.global_options['hide_numeric_scale_value']['widget'] = self.dlg.hide_scale_value
        self.global_options['acl']['widget'] = self.dlg.inAcl
        self.global_options['initialExtent']['widget'] = self.dlg.widget_initial_extent
        self.global_options['googleKey']['widget'] = self.dlg.inGoogleKey
        self.global_options['googleHybrid']['widget'] = self.dlg.cbGoogleHybrid
        self.global_options['googleSatellite']['widget'] = self.dlg.cbGoogleSatellite
        self.global_options['googleTerrain']['widget'] = self.dlg.cbGoogleTerrain
        self.global_options['googleStreets']['widget'] = self.dlg.cbGoogleStreets
        self.global_options['osmMapnik']['widget'] = self.dlg.cbOsmMapnik
        self.global_options['openTopoMap']['widget'] = self.dlg.cb_open_topo_map
        self.global_options['bingKey']['widget'] = self.dlg.inBingKey
        self.global_options['bingStreets']['widget'] = self.dlg.cbBingStreets
        self.global_options['bingSatellite']['widget'] = self.dlg.cbBingSatellite
        self.global_options['bingHybrid']['widget'] = self.dlg.cbBingHybrid
        self.global_options['ignKey']['widget'] = self.dlg.inIgnKey
        self.global_options['ignStreets']['widget'] = self.dlg.cbIgnStreets
        self.global_options['ignSatellite']['widget'] = self.dlg.cbIgnSatellite
        self.global_options['ignTerrain']['widget'] = self.dlg.cbIgnTerrain
        self.global_options['ignCadastral']['widget'] = self.dlg.cbIgnCadastral
        self.global_options['hideGroupCheckbox']['widget'] = self.dlg.cbHideGroupCheckbox
        self.global_options['activateFirstMapTheme']['widget'] = self.dlg.activate_first_map_theme
        self.global_options['popupLocation']['widget'] = self.dlg.liPopupContainer
        self.global_options['draw']['widget'] = self.dlg.activate_drawing_tools
        # Deprecated since LWC 3.7.0
        self.global_options['print']['widget'] = self.dlg.cbActivatePrint
        self.global_options['measure']['widget'] = self.dlg.cbActivateMeasure
        self.global_options['zoomHistory']['widget'] = self.dlg.cbActivateZoomHistory
        self.global_options['geolocation']['widget'] = self.dlg.cbActivateGeolocation
        self.global_options['pointTolerance']['widget'] = self.dlg.inPointTolerance
        self.global_options['lineTolerance']['widget'] = self.dlg.inLineTolerance
        self.global_options['polygonTolerance']['widget'] = self.dlg.inPolygonTolerance
        self.global_options['hideHeader']['widget'] = self.dlg.cbHideHeader
        self.global_options['hideMenu']['widget'] = self.dlg.cbHideMenu
        self.global_options['hideLegend']['widget'] = self.dlg.cbHideLegend
        self.global_options['hideOverview']['widget'] = self.dlg.cbHideOverview
        self.global_options['hideNavbar']['widget'] = self.dlg.cbHideNavbar
        self.global_options['hideProject']['widget'] = self.dlg.cbHideProject
        self.global_options['automatic_permalink']['widget'] = self.dlg.automatic_permalink
        self.global_options['wms_single_request_for_all_layers']['widget'] = self.dlg.checkbox_wms_single_request_all_layers
        self.global_options['tmTimeFrameSize']['widget'] = self.dlg.inTimeFrameSize
        self.global_options['tmTimeFrameType']['widget'] = self.dlg.liTimeFrameType
        self.global_options['tmAnimationFrameLength']['widget'] = self.dlg.inAnimationFrameLength
        self.global_options['emptyBaselayer']['widget'] = self.dlg.cbAddEmptyBaselayer
        self.global_options['startupBaselayer']['widget'] = self.dlg.cbStartupBaselayer
        self.global_options['limitDataToBbox']['widget'] = self.dlg.cbLimitDataToBbox
        self.global_options['datavizLocation']['widget'] = self.dlg.liDatavizContainer
        self.global_options['datavizTemplate']['widget'] = self.dlg.dataviz_html_template
        self.global_options['theme']['widget'] = self.dlg.combo_theme
        self.global_options['atlasShowAtStartup']['widget'] = self.dlg.atlasShowAtStartup
        self.global_options['atlasAutoPlay']['widget'] = self.dlg.atlasAutoPlay

        self.layer_options_list = lizmap_config.layerOptionDefinitions
        # Add widget information
        self.layer_options_list['title']['widget'] = self.dlg.inLayerTitle
        self.layer_options_list['abstract']['widget'] = self.dlg.teLayerAbstract
        self.layer_options_list['link']['widget'] = self.dlg.inLayerLink
        self.layer_options_list['minScale']['widget'] = None
        self.layer_options_list['maxScale']['widget'] = None
        self.layer_options_list['toggled']['widget'] = self.dlg.cbToggled
        self.layer_options_list['group_visibility']['widget'] = self.dlg.list_group_visibility
        self.layer_options_list['popup']['widget'] = self.dlg.checkbox_popup
        self.layer_options_list['popupFrame']['widget'] = self.dlg.frame_layer_popup
        self.layer_options_list['popupTemplate']['widget'] = None
        self.layer_options_list['popupMaxFeatures']['widget'] = self.dlg.sbPopupMaxFeatures
        self.layer_options_list['popupDisplayChildren']['widget'] = self.dlg.cbPopupDisplayChildren
        self.layer_options_list['popup_allow_download']['widget'] = self.dlg.checkbox_popup_allow_download
        self.layer_options_list['groupAsLayer']['widget'] = self.dlg.cbGroupAsLayer
        self.layer_options_list['baseLayer']['widget'] = self.dlg.cbLayerIsBaseLayer
        self.layer_options_list['displayInLegend']['widget'] = self.dlg.cbDisplayInLegend
        self.layer_options_list['singleTile']['widget'] = self.dlg.cbSingleTile
        self.layer_options_list['cached']['widget'] = self.dlg.checkbox_server_cache
        self.layer_options_list['serverFrame']['widget'] = self.dlg.server_cache_frame
        self.layer_options_list['cacheExpiration']['widget'] = self.dlg.inCacheExpiration
        self.layer_options_list['metatileSize']['widget'] = self.dlg.inMetatileSize
        self.layer_options_list['clientCacheExpiration']['widget'] = self.dlg.inClientCacheExpiration
        self.layer_options_list['externalWmsToggle']['widget'] = self.dlg.cbExternalWms
        self.layer_options_list['sourceRepository']['widget'] = self.dlg.inSourceRepository
        self.layer_options_list['sourceProject']['widget'] = self.dlg.inSourceProject

        # Disabled because done earlier
        # self.layer_options_list['legend_image_option']['widget'] = self.dlg.combo_legend_option
        # self.layer_options_list['popupSource']['widget'] = self.dlg.liPopupSource
        # self.layer_options_list['imageFormat']['widget'] = self.dlg.liImageFormat
        # self.global_options['externalSearch']['widget'] = self.dlg.liExternalSearch

        # map QGIS geometry type
        # TODO lizmap 4, to remove
        self.mapQgisGeometryType = {
            0: 'point',
            1: 'line',
            2: 'polygon',
            3: 'unknown',
            4: 'none'
        }

        # Disable checkboxes on the layer tab
        self.enable_check_box_in_layer_tab(False)

        # Catch user interaction on layer tree and inputs
        self.dlg.layer_tree.itemSelectionChanged.connect(self.from_data_to_ui_for_layer_group)

        self.dlg.scales_warning.set_text(tr(
            "The map is in EPSG:3857 (Google Mercator), only the minimum and maximum scales will be used for the map."
        ))
        self.dlg.scales_warning.setVisible(False)

        # Scales
        self.dlg.min_scale_pic.setPixmap(QPixmap(":images/themes/default/mActionZoomOut.svg"))
        self.dlg.min_scale_pic.setText('')
        self.dlg.max_scale_pic.setPixmap(QPixmap(":images/themes/default/mActionZoomIn.svg"))
        self.dlg.max_scale_pic.setText('')
        ui_items = (
            self.dlg.label_min_scale, self.dlg.label_max_scale,
            self.dlg.min_scale_pic, self.dlg.max_scale_pic,
            self.dlg.minimum_scale, self.dlg.maximum_scale,
        )
        for item in ui_items:
            item.setToolTip(tr("The minimum and maximum scales are defined by your minimum and maximum values above."))

        remove_buttons = (
            self.dlg.button_remove_qgs,
            self.dlg.button_remove_cfg,
            self.dlg.button_remove_thumbnail,
            self.dlg.button_remove_action,
        )
        for button in remove_buttons:
            button.setText('')
            button.setIcon(QIcon(":/images/themes/default/mActionDeleteSelected.svg"))
            button.clicked.connect(partial(self.remove_remote_file, button))
        self.dlg.table_files.val_Changed.connect(self.remove_remote_layer_index)
        self.dlg.button_send_all_layers.clicked.connect(self.send_all_layers)
        self.dlg.button_check_all_layers.clicked.connect(self.refresh_all_layers)
        self.dlg.button_refresh_all.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.dlg.button_refresh_all.setText('')
        self.dlg.button_refresh_all.setToolTip('Refresh all dates from the server.')
        self.dlg.button_refresh_all.clicked.connect(self.check_all_dates_dav)
        self.dlg.button_refresh_date_webdav.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.dlg.button_refresh_date_webdav.setText('')
        self.dlg.button_refresh_date_webdav.setToolTip('The date time of the file on the server.')
        self.dlg.button_refresh_date_webdav.clicked.connect(self.check_latest_update_webdav)
        self.dlg.button_check_capabilities.setToolTip(
            'If the server selected in this dropdown menu has not the correct version displayed under, or if some '
            'server capabilities is missing.'
        )
        self.dlg.button_check_capabilities.setText('')
        self.dlg.button_check_capabilities.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.dlg.button_check_capabilities.clicked.connect(self.check_server_capabilities)
        # self.dlg.button_open_project.clicked.connect(self.open_web_browser_project)
        self.dlg.button_create_repository.clicked.connect(self.create_new_repository)
        self.dlg.button_create_repository.setIcon(QIcon(":/images/themes/default/mActionNewFolder.svg"))
        self.dlg.button_create_media_remote.setIcon(QIcon(":/images/themes/default/mActionNewFolder.svg"))
        self.dlg.button_create_media_local.setIcon(QIcon(":/images/themes/default/mActionNewFolder.svg"))
        buttons = (
            self.dlg.button_upload_thumbnail, self.dlg.button_upload_action, self.dlg.button_upload_webdav,
            self.dlg.button_upload_media,
        )
        for button in buttons:
            button.setIcon(QIcon(resources_path('icons', 'upload.svg')))
            button.setText('')
            self.dlg.set_tooltip_webdav(button)
        self.dlg.button_upload_thumbnail.clicked.connect(self.upload_thumbnail)
        self.dlg.button_upload_action.clicked.connect(self.upload_action)
        self.dlg.button_upload_webdav.clicked.connect(self.send_files)
        self.dlg.button_upload_media.clicked.connect(self.upload_media)
        self.dlg.button_create_media_remote.clicked.connect(self.create_media_dir_remote)
        self.dlg.button_create_media_local.clicked.connect(self.create_media_dir_local)

        # Group helper
        self.dlg.add_group_hidden.setToolTip(tr(
            'Add a group which will be hidden by default on Lizmap Web Client. Some tables might be needed in the '
            'QGIS projet but not needed for display on the map and in the legend.'
        ))
        self.dlg.add_group_baselayers.setToolTip(tr(
            'Add a group called "baselayers", you can organize your layers inside, it will be displayed in a dropdown '
            'menu.'
        ))
        self.dlg.add_group_empty.setToolTip(tr(
            'Add a group which must stay empty. It will add an option in the base layer dropdown menu and allow '
            'the default background color defined in the project properties to be displayed.'
        ))
        self.dlg.add_group_overview.setToolTip(tr(
            'Add some layers in this group to make an overview map at a lower scale.'
        ))
        self.dlg.add_group_hidden.clicked.connect(self.add_group_hidden)
        self.dlg.add_group_baselayers.clicked.connect(self.add_group_baselayers)
        self.dlg.add_group_empty.clicked.connect(self.add_group_empty)
        self.dlg.add_group_overview.clicked.connect(self.add_group_overview)

        osm_icon = QIcon(resources_path('icons', 'osm-32-32.png'))
        self.dlg.button_osm_mapnik.clicked.connect(self.add_osm_mapnik)
        self.dlg.button_osm_mapnik.setIcon(osm_icon)
        self.dlg.button_osm_opentopomap.clicked.connect(self.add_osm_opentopomap)
        self.dlg.button_osm_opentopomap.setIcon(osm_icon)
        self.dlg.button_ign_orthophoto.clicked.connect(
            partial(self.add_french_ign_layer, IgnLayers.IgnOrthophoto))
        self.dlg.button_ign_plan.clicked.connect(
            partial(self.add_french_ign_layer, IgnLayers.IgnPlan))
        self.dlg.button_ign_cadastre.clicked.connect(
            partial(self.add_french_ign_layer, IgnLayers.IgnCadastre))

        self.dlg.button_run_checks.clicked.connect(self.check_project_clicked)
        self.dlg.button_copy.clicked.connect(self.copy_versions_clicked)
        self.dlg.button_copy.setVisible(False)

        self.dlg.label_lizmap_search_grant.setText(tr(
            "About \"lizmap_search\", for an instance hosted on lizmap.com cloud solution, you must do the \"GRANT\" "
            "command according to the <a href=\"{}\">documentation</a>."
        ).format(online_cloud_help("postgresql.html").url()))
        self.dlg.label_lizmap_search_grant.setOpenExternalLinks(True)

        widget_source_popup = self.layer_options_list['popupSource']['widget']
        widget_source_popup.currentIndexChanged.connect(self.enable_popup_source_button)

        index = widget_source_popup.findData('form')
        form_popup = widget_source_popup.model().item(index)

        font = form_popup.font()
        font.setUnderline(True)
        form_popup.setFont(font)

        # Connect widget signals to setLayerProperty method depending on widget type
        for key, item in self.layer_options_list.items():
            if item.get('widget'):
                control = item['widget']
                slot = partial(self.save_value_layer_group_data, key)
                if item['wType'] in ('text', 'spinbox'):
                    control.editingFinished.connect(slot)
                elif item['wType'] == 'textarea':
                    control.textChanged.connect(slot)
                elif item['wType'] == 'checkbox':
                    control.stateChanged.connect(slot)
                elif item['wType'] == 'list':
                    control.currentIndexChanged.connect(slot)
                elif item['wType'] == 'layers':
                    control.layerChanged.connect(slot)
                elif item['wType'] == 'fields':
                    control.fieldChanged.connect(slot)

        self.crs_3857_base_layers_list = {
            'osm-mapnik': self.dlg.cbOsmMapnik,
            'opentopomap': self.dlg.cb_open_topo_map,
            'google-street': self.dlg.cbGoogleStreets,
            'google-satellite': self.dlg.cbGoogleSatellite,
            'google-hybrid': self.dlg.cbGoogleHybrid,
            'google-terrain': self.dlg.cbGoogleTerrain,
            'bing-road': self.dlg.cbBingStreets,
            'bing-aerial': self.dlg.cbBingSatellite,
            'bing-hybrid': self.dlg.cbBingHybrid,
            'ign-plan': self.dlg.cbIgnStreets,
            'ign-photo': self.dlg.cbIgnSatellite,
            'ign-scan': self.dlg.cbIgnTerrain,
            'ign-cadastral': self.dlg.cbIgnCadastral,
        }
        for item in self.crs_3857_base_layers_list.values():
            slot = self.check_visibility_crs_3857
            item.stateChanged.connect(slot)
        self.check_visibility_crs_3857()

        # Connect base-layer checkboxes
        self.base_layer_widget_list = {
            'layer': self.dlg.cbLayerIsBaseLayer,
            'empty': self.dlg.cbAddEmptyBaselayer
        }
        self.base_layer_widget_list.update(self.crs_3857_base_layers_list)
        for item in self.base_layer_widget_list.values():
            slot = self.on_baselayer_checkbox_change
            item.stateChanged.connect(slot)

        self.server_manager = ServerManager(
            self.dlg,
            self.dlg.table_server,
            self.dlg.add_server_button,
            self.dlg.add_first_server,
            self.dlg.remove_server_button,
            self.dlg.edit_server_button,
            self.dlg.refresh_versions_button,
            self.dlg.move_up_server_button,
            self.dlg.move_down_server_button,
            self.check_dialog_validity,
        )
        # Debug
        # self.server_manager.clean_cache(True)

        current = format_qgis_version(qgis_version())
        current = '{}.{}'.format(current[0], current[1])
        self.dlg.label_current_qgis.setText('<b>{}</b>'.format(current))
        text = self.dlg.qgis_and_lwc_versions_issue.text()
        self.dlg.qgis_and_lwc_versions_issue.setText(text.format(version=current))
        self.dlg.qgis_and_lwc_versions_issue.setVisible(False)

        # tables of layers
        # Todo Lizmap 3.4, remove dict init here
        self.layers_table = {
            'atlas': {
                'panel': Panels.Atlas,
                'tableWidget': self.dlg.table_atlas,
                'removeButton': self.dlg.button_atlas_remove,
                'addButton': self.dlg.button_atlas_add,
                'editButton': self.dlg.button_atlas_edit,
                'upButton': self.dlg.button_atlas_up,
                'downButton': self.dlg.button_atlas_down,
                'manager': None,
            },
            'locateByLayer': {
                'panel': Panels.LocateByLayer,
                'tableWidget': self.dlg.table_locate_by_layer,
                'removeButton': self.dlg.remove_locate_layer_button,
                'addButton': self.dlg.add_locate_layer_button,
                'editButton': self.dlg.edit_locate_layer_button,
                'upButton': self.dlg.up_locate_layer_button,
                'downButton': self.dlg.down_locate_layer_button,
                'manager': None,
            },
            'attributeLayers': {
                'panel': Panels.AttributeTable,
                'tableWidget': self.dlg.table_attribute_table,
                'removeButton': self.dlg.remove_attribute_table_button,
                'addButton': self.dlg.add_attribute_table_button,
                'editButton': self.dlg.edit_attribute_table_button,
                'upButton': self.dlg.up_attribute_table_button,
                'downButton': self.dlg.down_attribute_table_button,
                'manager': None,
            },
            'tooltipLayers': {
                'panel': Panels.ToolTip,
                'tableWidget': self.dlg.table_tooltip,
                'removeButton': self.dlg.remove_tooltip_button,
                'addButton': self.dlg.add_tooltip_button,
                'editButton': self.dlg.edit_tooltip_button,
                'upButton': self.dlg.up_tooltip_button,
                'downButton': self.dlg.down_tooltip_button,
                'manager': None,
            },
            'editionLayers': {
                'panel': Panels.Editing,
                'tableWidget': self.dlg.edition_table,
                'removeButton': self.dlg.remove_edition_layer,
                'addButton': self.dlg.add_edition_layer,
                'editButton': self.dlg.edit_edition_layer,
                'upButton': self.dlg.up_edition_layer,
                'downButton': self.dlg.down_edition_layer,
                'manager': None,
            },
            'layouts': {
                'panel': Panels.Layouts,
                'tableWidget': self.dlg.table_layout,
                'editButton': self.dlg.edit_layout_form_button,
                'upButton': self.dlg.up_layout_form_button,
                'downButton': self.dlg.down_layout_form_button,
                'manager': None,
            },
            'loginFilteredLayers': {
                'panel': Panels.FilteredLayers,
                'tableWidget': self.dlg.table_login_filter,
                'removeButton': self.dlg.remove_filter_login_layer_button,
                'addButton': self.dlg.add_filter_login_layer_button,
                'editButton': self.dlg.edit_filter_login_layer_button,
                'manager': None,
            },
            'timemanagerLayers': {
                'panel': Panels.TimeManager,
                'tableWidget': self.dlg.time_manager_table,
                'removeButton': self.dlg.remove_time_manager_layer,
                'addButton': self.dlg.add_time_manager_layer,
                'editButton': self.dlg.edit_time_manager_layer,
                'upButton': self.dlg.up_time_manager_layer,
                'downButton': self.dlg.down_time_manager_layer,
                'manager': None,
            },
            'datavizLayers': {
                'panel': Panels.Dataviz,
                'tableWidget': self.dlg.table_dataviz,
                'removeButton': self.dlg.remove_dataviz_layer,
                'addButton': self.dlg.add_dataviz_layer,
                'editButton': self.dlg.edit_dataviz_layer,
                'upButton': self.dlg.up_dataviz_layer,
                'downButton': self.dlg.down_dataviz_layer,
                'manager': None,
            },
            'filter_by_polygon': {
                'panel': Panels.FilteredLayers,
                'tableWidget': self.dlg.table_filter_polygon,
                'removeButton': self.dlg.remove_filter_polygon_button,
                'addButton': self.dlg.add_filter_polygon_button,
                'editButton': self.dlg.edit_filter_polygon_button,
                'manager': None,
            },
            'formFilterLayers': {
                'panel': Panels.FormFiltering,
                'tableWidget': self.dlg.table_form_filter,
                'removeButton': self.dlg.remove_filter_form_button,
                'addButton': self.dlg.add_filter_form_button,
                'editButton': self.dlg.edit_filter_form_button,
                'upButton': self.dlg.up_filter_form_button,
                'downButton': self.dlg.down_filter_form_button,
                'manager': None,
            }
        }

        # Set some tooltips
        tooltip = tr(
            'By default the layer is visible for all groups in Lizmap.\n'
            'If a comma separated list of groups IDs is defined,\n'
            'the layer will be visible only for these groups.\n'
            'Use Lizmap Web Client group IDs and not labels.')
        self.dlg.label_group_visibility.setToolTip(tooltip)
        self.dlg.list_group_visibility.setToolTip(tooltip)

        self.dlg.button_generate_html_table.setToolTip(tr(
            "A default HTML table will be generated in the layer maptip. The layout will be very similar to the auto "
            "popup, except that the display of a media must still be managed manually using HTML &lt;a&gt; or "
            "&lt;img&gt; for instance."
        ))

        # Filter by polygon
        self.dlg.layer_filter_polygon.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.layer_filter_polygon.layerChanged.connect(self.dlg.field_filter_polygon.setLayer)
        self.dlg.field_filter_polygon.setLayer(self.dlg.layer_filter_polygon.currentLayer())

        # Server combo
        server = QgsSettings().value('lizmap/instance_target_url', '')
        if server:
            index = self.dlg.server_combo.findData(server, ServerComboData.ServerUrl.value)
            if index:
                self.dlg.server_combo.setCurrentIndex(index)
                # self.check_webdav()
        self.dlg.server_combo.currentIndexChanged.connect(self.target_server_changed)
        self.dlg.repository_combo.currentIndexChanged.connect(self.target_repository_changed)
        self.target_server_changed()
        self.lwc_version_changed()
        self.dlg.refresh_combo_repositories()

        self.dlg.tab_dataviz.setCurrentIndex(0)

        self.dlg.name_training_folder.setPlaceholderText(self.current_login())

        # When a ZIP is provided for the training
        self.dlg.path_training_folder_zip.setStorageMode(QgsFileWidget.GetDirectory)
        self.dlg.path_training_folder_zip.setDialogTitle(tr("Choose a folder to store the your data about the training"))
        self.dlg.download_training_data_zip.clicked.connect(partial(self.download_training_data_clicked, WorkshopType.ZipFile))
        self.dlg.open_training_project_zip.clicked.connect(partial(self.open_training_project_clicked, WorkshopType.ZipFile))
        self.dlg.open_training_folder_zip.clicked.connect(partial(self.open_training_folder_clicked, WorkshopType.ZipFile))

        # When an individual QGS file is provided for the training
        self.dlg.path_training_folder_qgs.setStorageMode(QgsFileWidget.GetDirectory)
        self.dlg.path_training_folder_qgs.setDialogTitle(tr("Choose a folder to store the your data about the training"))
        self.dlg.download_training_data_qgs.clicked.connect(partial(self.download_training_data_clicked, WorkshopType.IndividualQgsFile))
        self.dlg.open_training_project_qgs.clicked.connect(partial(self.open_training_project_clicked, WorkshopType.IndividualQgsFile))
        self.dlg.open_training_folder_qgs.clicked.connect(partial(self.open_training_folder_clicked, WorkshopType.IndividualQgsFile))

        self.dlg.button_quick_start.clicked.connect(self.dlg.open_lizmap_how_to)
        self.dlg.workshop_edition.clicked.connect(self.dlg.open_workshop_edition)

        self.drag_drop_dataviz = None
        self.layerList = None
        self.action = None
        self.embeddedGroups = None
        self.myDic = None
        self.help_action = None
        self.help_action_cloud = None

    def project_saved(self):
        """ When the project is saved. """
        if not self.dlg.check_cfg_file_exists():
            return

        try:
            if not self.layerList:
                # The user didn't open the plugin since QGIS has started
                # Sorry, we don't know if the user added/removed layers, maybe nothing
                return
        except AttributeError:
            # self.attributeError is defined in __init__ but not found
            return

        # Check the number of layers between the project and the Lizmap configuration file.
        list_cfg = list(self.layerList.keys())
        list_qgs = count_legend_items(self.project.layerTreeRoot(), self.project, [])
        if len(list_cfg) != len(list_qgs):
            # self.iface.messageBar().pushMessage(
            #     'Lizmap',
            #     tr(
            #         'The project has {count_qgs} items in the legend, while the Lizmap configuration has {count_cfg} '
            #         'items. Please open the plugin to sync the "{layer_tab}" tab.'
            #     ).format(
            #         count_qgs=len(list_qgs),
            #         count_cfg=len(list_cfg),
            #         layer_tab=self.dlg.mOptionsListWidget.item(Panels.Layers).text()
            #     ),
            #     Qgis.Warning,
            #     duration=DURATION_WARNING_BAR,
            # )qt
            LOGGER.debug(
                "Difference in counts between CFG and QGS\n\nList in CFG : {}\nList in QGS : {}".format(
                    ','.join(list_cfg), ','.join(list_qgs)))

    def filename_changed(self):
        """ When the current project has been renamed. """
        if os.getenv("QGIS_PLUGIN_AUTO_SAVING"):
            # Special variable set from QGIS autoSaver plugin
            return

        if not self.project.absoluteFilePath():
            return

        new_path = Path(self.project.absoluteFilePath())
        if str(new_path).endswith('.bak'):
            # We skip, it's from the QGIS plugin autoSaver
            return

        if 'autoSaver' in all_plugins:
            # Until https://github.com/enricofer/autoSaver/pull/22 is merged
            return

        if self.current_path and new_path != self.current_path and not to_bool(os.getenv("CI"), default_value=False):
            old_cfg = self.current_path.with_suffix('.qgs.cfg')
            if old_cfg.exists():
                box = QMessageBox(self.dlg)
                box.setIcon(QMessageBox.Question)
                box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )
                box.setWindowTitle(tr('Project has been renamed'))
                box.setText(tr(
                    'The previous project located at "{}" was associated to a Lizmap configuration. '
                    'Do you want to copy the previous Lizmap configuration file to this new project ?'
                ).format(self.current_path))
                box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                box.setDefaultButton(QMessageBox.No)
                result = box.exec_()
                if result == QMessageBox.No:
                    return

                copyfile(str(old_cfg), str(new_path.with_suffix('.qgs.cfg')))
                LOGGER.info("Project has been renamed and Lizmap configuration file has been copied as well.")

        self.current_path = new_path

    @staticmethod
    def current_login() -> str:
        """ Current login on the OS. """
        try:
            return os.getlogin()
        except OSError:
            return 'repository'

    def current_lwc_version(self) -> LwcVersions:
        """ Return the current selected LWC version from the server. """
        if self._version:
            # For tests, return the version given in the constructor
            return self._version

        return self.dlg.current_lwc_version()

    def target_server_changed(self):
        """ When the server destination has changed in the selector. """
        current_authid = self.dlg.server_combo.currentData(ServerComboData.AuthId.value)
        current_url = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        current_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        QgsSettings().setValue('lizmap/instance_target_url', current_url)
        QgsSettings().setValue('lizmap/instance_target_url_authid', current_authid)
        self.check_dialog_validity()
        self.dlg.refresh_combo_repositories()
        self.check_training_panel()
        if self.webdav:
            self.check_webdav()

        if current_metadata:
            current_version = LwcVersions.find_from_metadata(current_metadata)
            self.dlg.refresh_helper_target_version(current_version)

        current_version = self.current_lwc_version()
        old_version = QgsSettings().value('lizmap/lizmap_web_client_version', type=str)
        if current_version != old_version:
            self.lwc_version_changed()
        self.dlg.check_qgis_version(widget=True)
        # self.check_webdav()

        if self.dock_html_preview:
            # Change the URL for the CSS
            self.dock_html_preview: HtmlPreview
            self.dock_html_preview.set_server_url(self.dlg.current_server_info(ServerComboData.ServerUrl.value))

        lizmap_cloud = is_lizmap_cloud(current_metadata)
        for item in self.lizmap_cloud:
            item.setVisible(lizmap_cloud)

        self.dlg.helper_list_group.setReadOnly(True)
        if current_metadata:
            acl = current_metadata.get('acl')
            if not acl:
                # Running a version < 3.6.1
                tooltip = tr("Your server does not support this feature, please upgrade.")
                self.dlg.helper_list_group.setText("")
            else:
                self.dlg.helper_list_group.setText(','.join(list(acl['groups'].keys())))
                tooltip = (
                    tr("It cannot be edited. Existing groups on the server : ") + self.dlg.server_combo.currentText()
                )

            self.dlg.helper_list_group.setToolTip(tooltip)
            self.dlg.label_helper_list_group.setToolTip(tooltip)

        # For deprecated features in LWC 3.7 about base layers
        self.check_visibility_crs_3857()

        if not current_metadata:
            # In CI, to make tests happy
            return

        repositories = current_metadata.get('repositories')
        if not repositories:
            return

        # How-to is for server with less than 3 projects in total :)
        qgis_projects = 0
        for repo in repositories.values():
            qgis_projects += len(repo['projects'])
        self.dlg.publish_first_map.setVisible(qgis_projects < 3)

    def target_repository_changed(self):
        """ When the repository destination has changed in the selector. """
        # self.check_webdav()
        # The new repository is only set when we save the CFG file
        # Otherwise, it will make a mess with the signals about the last repository used and the server refreshed list
        if self.dlg.page_dataviz.isVisible():
            self.layers_table['datavizLayers'].get('manager').preview_dataviz_dialog()

    def lwc_version_changed(self):
        """ When the version has changed in the selector, we update features with the blue background. """
        # self.check_webdav()
        current_version = self.current_lwc_version()
        if not current_version:
            LOGGER.info("No LWC version currently defined in the combobox, skipping LWC target version changed.")
            self.dlg.refresh_helper_target_version(None)
            return

        LOGGER.debug("Saving new value about the LWC target version : {}".format(current_version.value))
        QgsSettings().setValue('lizmap/lizmap_web_client_version', str(current_version.value))

        self.dlg.refresh_helper_target_version(current_version)

        # New print panel
        # The checkbox is removed since LWC 3.7.0
        self.dlg.cbActivatePrint.setVisible(current_version <= LwcVersions.Lizmap_3_6)
        self.dlg.cbActivatePrint.setEnabled(current_version <= LwcVersions.Lizmap_3_6)

        # The checkbox is removed since LWC 3.8.0
        self.dlg.cbActivateZoomHistory.setVisible(current_version <= LwcVersions.Lizmap_3_7)
        self.dlg.cbActivateZoomHistory.setEnabled(current_version <= LwcVersions.Lizmap_3_7)

        found = False
        for lwc_version, items in self.lwc_versions.items():
            if found:
                # Set some blue
                for item in items:
                    if isinstance(item, QWidget):
                        item.setStyleSheet(NEW_FEATURE_CSS)
                    elif isinstance(item, QStandardItem):
                        # QComboBox
                        brush = QBrush()
                        # noinspection PyUnresolvedReferences
                        brush.setStyle(Qt.SolidPattern)
                        brush.setColor(QColor(NEW_FEATURE_COLOR))
                        item.setBackground(brush)
            else:
                # Remove some blue
                for item in items:
                    if isinstance(item, QWidget):
                        item.setStyleSheet('')
                    elif isinstance(item, QStandardItem):
                        # QComboBox
                        item.setBackground(QBrush())

            if lwc_version == current_version:
                found = True

        # Change in all table manager too
        for key in self.layers_table.keys():
            manager = self.layers_table[key].get('manager')
            if manager:
                manager.set_lwc_version(current_version)

        # Compare the LWC version with the current QGIS Desktop version and the release JSON file
        version_file = lizmap_user_folder().joinpath('released_versions.json')
        if not version_file.exists():
            return

        with open(version_file, encoding='utf8') as json_file:
            json_content = json.loads(json_file.read())

        for lzm_version in json_content:
            if lzm_version['branch'] != current_version.value:
                continue

            qgis_min = lzm_version.get('qgis_min_version_recommended')
            qgis_max = lzm_version.get('qgis_max_version_recommended')
            if not (qgis_min or qgis_max):
                break

            if qgis_min <= qgis_version() < qgis_max:
                self.dlg.qgis_and_lwc_versions_issue.setVisible(False)
            else:
                self.dlg.qgis_and_lwc_versions_issue.setVisible(True)

    def check_webdav(self):
        """ Check if we can enable or the webdav, according to the current selected server. """
        # I hope temporary, to force the version displayed
        self.dlg.refresh_helper_target_version(self.current_lwc_version())

        def disable_upload_panel():
            self.dlg.mOptionsListWidget.item(Panels.Upload).setHidden(True)
            if self.dlg.mOptionsListWidget.currentRow() == Panels.Upload:
                self.dlg.mOptionsListWidget.setCurrentRow(Panels.Information)

        if not self.webdav:
            # QGIS <= 3.22
            # self.dlg.group_upload.setVisible(False)
            # self.dlg.send_webdav.setChecked(False)
            # self.dlg.send_webdav.setEnabled(False)
            # self.dlg.send_webdav.setVisible(False)
            self.dlg.webdav_frame.setVisible(False)
            self.dlg.button_upload_thumbnail.setVisible(False)
            self.dlg.button_upload_action.setVisible(False)
            self.dlg.button_upload_media.setVisible(False)
            self.dlg.button_create_media_remote.setVisible(False)
            disable_upload_panel()
            # LOGGER.critical("RETURN 1")
            return

        self.webdav.config_project()

        # The dialog is already given.
        # We can check if WebDAV is supported.
        # LOGGER.critical("Second check : {}".format(self.webdav.setup_webdav_dialog()))
        if self.webdav.setup_webdav_dialog():
            # self.dlg.group_upload.setVisible(True)
            # self.dlg.send_webdav.setEnabled(True)
            # self.dlg.send_webdav.setVisible(True)
            self.dlg.webdav_frame.setVisible(True)
            self.dlg.button_upload_thumbnail.setVisible(True)
            self.dlg.button_upload_action.setVisible(True)
            self.dlg.button_upload_media.setVisible(True)
            self.dlg.button_create_media_remote.setVisible(True)
            self.dlg.mOptionsListWidget.item(Panels.Upload).setHidden(False)
        else:
            # self.dlg.group_upload.setVisible(False)
            # self.dlg.send_webdav.setChecked(False)
            # self.dlg.send_webdav.setEnabled(False)
            # self.dlg.send_webdav.setVisible(False)
            self.dlg.webdav_frame.setVisible(False)
            self.dlg.button_upload_thumbnail.setVisible(False)
            self.dlg.button_upload_action.setVisible(False)
            self.dlg.button_upload_media.setVisible(False)
            self.dlg.button_create_media_remote.setVisible(False)
            disable_upload_panel()

    # noinspection PyPep8Naming
    def initGui(self):
        """Create action that will start plugin configuration"""
        LOGGER.debug("Plugin starting in the initGui")

        icon = QIcon(resources_path('icons', 'icon.png'))
        self.action = QAction(icon, 'Lizmap', self.iface.mainWindow())

        # connect the action to the run method
        # noinspection PyUnresolvedReferences
        self.action.triggered.connect(self.run)

        self.dock_html_preview = HtmlPreview(None)
        self.dock_html_preview.set_server_url(self.dlg.current_server_info(ServerComboData.ServerUrl.value))
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_html_preview)
        self.dock_html_preview.setVisible(False)
        self.dlg.button_maptip_preview.setText('')
        self.dlg.button_maptip_preview.setToolTip(tr('Open the HTML Lizmap maptip popup preview dock'))
        self.dlg.button_maptip_preview.setIcon(QIcon(":images/themes/default/mActionShowAllLayers.svg"))
        self.dlg.button_maptip_preview.clicked.connect(self.open_dock_preview_maptip)

        # Open the online help
        self.help_action = QAction(icon, 'Lizmap', self.iface.mainWindow())
        self.iface.pluginHelpMenu().addAction(self.help_action)
        # noinspection PyUnresolvedReferences
        self.help_action.triggered.connect(self.show_help)

        self.help_action_cloud = QAction(icon, CLOUD_NAME, self.iface.mainWindow())
        self.iface.pluginHelpMenu().addAction(self.help_action_cloud)
        # noinspection PyUnresolvedReferences
        self.help_action.triggered.connect(self.show_help_cloud)

        # connect Lizmap signals and functions

        self.dlg.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.dlg.close)
        self.dlg.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(partial(self.save_cfg_file_cursor, False))
        self.dlg.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(partial(self.save_cfg_file_cursor, True))
        self.dlg.buttonBox.button(QDialogButtonBox.Help).clicked.connect(self.show_help_question)

        # Connect the left menu to the right panel
        self.dlg.mOptionsListWidget.currentRowChanged.connect(self.dlg.mOptionsStackedWidget.setCurrentIndex)

        # Abstract HTML editor
        self.dlg.button_abstract_html.setIcon(QIcon(":images/themes/default/mActionEditHtml.svg"))
        self.dlg.button_abstract_html.clicked.connect(self.configure_html_abstract)

        # Group wizard
        icon = QIcon(resources_path('icons', 'user_group.svg'))
        self.dlg.button_wizard_group_visibility_project.setText('')
        self.dlg.button_wizard_group_visibility_layer.setText('')
        self.dlg.button_wizard_group_visibility_project.setIcon(icon)
        self.dlg.button_wizard_group_visibility_layer.setIcon(icon)
        self.dlg.button_wizard_group_visibility_project.clicked.connect(self.open_wizard_group_project)
        self.dlg.button_wizard_group_visibility_layer.clicked.connect(self.open_wizard_group_layer)
        tooltip = tr("Open the group wizard")
        self.dlg.button_wizard_group_visibility_project.setToolTip(tooltip)
        self.dlg.button_wizard_group_visibility_layer.setToolTip(tooltip)

        # configure popup button
        self.dlg.btConfigurePopup.setText('')
        self.dlg.btConfigurePopup.setIcon(QIcon(":images/themes/default/console/iconSettingsConsole.svg"))
        self.dlg.btConfigurePopup.clicked.connect(self.configure_html_popup)
        self.dlg.convert_html_maptip.clicked.connect(self.convert_html_maptip)
        self.dlg.btQgisPopupFromForm.clicked.connect(self.maptip_from_form)
        self.dlg.button_generate_html_table.clicked.connect(self.html_table_from_layer)
        self.dlg.widget_deprecated_lizmap_popup.setVisible(False)

        # Link button
        self.dlg.button_refresh_link.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.dlg.button_refresh_link.setText('')
        self.dlg.button_refresh_link.setToolTip(tr('Set the link from the dataUrl property in the layer properties'))
        self.dlg.button_refresh_link.clicked.connect(self.link_from_properties)
        self.dlg.button_browse_media.setToolTip(tr('Open the file browser'))
        self.dlg.button_browse_media.clicked.connect(self.open_media_file_browser)

        # detect project closed
        self.iface.projectRead.connect(self.on_project_read)
        self.iface.newProjectCreated.connect(self.on_project_read)

        # initial extent
        self.dlg.btSetExtentFromProject.clicked.connect(self.set_initial_extent_from_project)
        self.dlg.btSetExtentFromProject.setIcon(QIcon(":images/themes/default/propertyicons/overlay.svg"))

        # Dataviz options
        for item in Theme:
            self.global_options['theme']['widget'].addItem(item.value["label"], item.value["data"])
        index = self.global_options['theme']['widget'].findData(Theme.Light.value["data"])
        self.global_options['theme']['widget'].setCurrentIndex(index)

        # Manage "delete line" button
        for key, item in self.layers_table.items():
            control = item.get('removeButton')
            if control:
                slot = partial(self.remove_selected_layer_from_table, key)
                control.clicked.connect(slot)
                # noinspection PyCallByClass,PyArgumentList
                control.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
                control.setText('')
                control.setToolTip(tr('Remove the selected layer from the list'))

            control = item.get('addButton')
            if control:
                control.setText('')
                # noinspection PyCallByClass,PyArgumentList
                control.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
                control.setToolTip(tr('Add a new layer in the list'))

            control = item.get('editButton')
            if control:
                # If there is an edit button, it's the new generation of form
                slot = partial(self.edit_layer, key)
                control.clicked.connect(slot)
                control.setText('')
                # noinspection PyCallByClass,PyArgumentList
                control.setIcon(QIcon(QgsApplication.iconPath('symbologyEdit.svg')))
                control.setToolTip(tr('Edit the current layer configuration'))

                slot = partial(self.add_new_layer, key)
                add_button = item.get('addButton')
                if add_button:
                    add_button.clicked.connect(slot)
                if key == 'atlas':
                    definition = AtlasDefinitions()
                    dialog = AtlasEditionDialog
                elif key == 'attributeLayers':
                    definition = AttributeTableDefinitions()
                    dialog = AttributeTableEditionDialog
                elif key == 'editionLayers':
                    definition = EditionDefinitions()
                    dialog = EditionLayerDialog
                elif key == 'datavizLayers':
                    definition = DatavizDefinitions()
                    dialog = DatavizEditionDialog
                elif key == 'layouts':
                    definition = LayoutsDefinitions()
                    dialog = LayoutEditionDialog
                elif key == 'locateByLayer':
                    definition = LocateByLayerDefinitions()
                    dialog = LocateLayerEditionDialog
                elif key == 'loginFilteredLayers':
                    definition = FilterByLoginDefinitions()
                    dialog = FilterByLoginEditionDialog
                elif key == 'timemanagerLayers':
                    definition = TimeManagerDefinitions()
                    dialog = TimeManagerEditionDialog
                elif key == 'tooltipLayers':
                    definition = ToolTipDefinitions()
                    dialog = ToolTipEditionDialog
                elif key == 'formFilterLayers':
                    definition = FilterByFormDefinitions()
                    dialog = FilterByFormEditionDialog
                elif key == 'filter_by_polygon':
                    definition = FilterByPolygonDefinitions()
                    dialog = FilterByPolygonEditionDialog
                else:
                    raise Exception('Unknown panel.')

                item['tableWidget'].horizontalHeader().setStretchLastSection(True)

                if key == 'datavizLayers':
                    # noinspection PyTypeChecker
                    item['manager'] = TableManagerDataviz(
                        self.dlg,
                        definition,
                        dialog,
                        item['tableWidget'],
                        item['editButton'],
                        item.get('upButton'),
                        item.get('downButton'),
                    )
                    # The drag&drop dataviz HTML layout
                    self.drag_drop_dataviz = DragDropDatavizManager(
                        self.dlg,
                        definition,
                        item['tableWidget'],
                        self.dlg.tree_dd_plots,
                        self.dlg.combo_plots,
                    )
                elif key == 'layouts':
                    # noinspection PyTypeChecker
                    item['manager'] = TableManagerLayouts(
                        self.dlg,
                        definition,
                        dialog,
                        item['tableWidget'],
                        item['editButton'],
                        item.get('upButton'),
                        item.get('downButton'),
                    )
                else:
                    # noinspection PyTypeChecker
                    item['manager'] = TableManager(
                        self.dlg,
                        definition,
                        dialog,
                        item['tableWidget'],
                        item['removeButton'],
                        item['editButton'],
                        item.get('upButton'),
                        item.get('downButton'),
                    )

                control = item.get('upButton')
                if control:
                    slot = partial(self.move_layer_up, key)
                    control.clicked.connect(slot)
                    control.setText('')
                    # noinspection PyCallByClass,PyArgumentList
                    control.setIcon(QIcon(QgsApplication.iconPath('mActionArrowUp.svg')))
                    control.setToolTip(tr('Move the layer up in the table'))

                control = item.get('downButton')
                if control:
                    slot = partial(self.move_layer_down, key)
                    control.clicked.connect(slot)
                    control.setText('')
                    # noinspection PyCallByClass,PyArgumentList
                    control.setIcon(QIcon(QgsApplication.iconPath('mActionArrowDown.svg')))
                    control.setToolTip(tr('Move the layer down in the table'))

        # Delete layers from table when deleted from registry
        # noinspection PyUnresolvedReferences
        self.project.layersRemoved.connect(self.remove_layer_from_table_by_layer_ids)

        self.project.layersAdded.connect(self.new_added_layers)
        self.project.layerTreeRoot().nameChanged.connect(self.layer_renamed)

        # Dataviz
        self.dlg.button_add_dd_dataviz.setText('')
        # noinspection PyCallByClass,PyArgumentList
        self.dlg.button_add_dd_dataviz.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.dlg.button_add_dd_dataviz.setToolTip(tr('Add a new container in the layout'))
        self.dlg.button_add_dd_dataviz.clicked.connect(self.drag_drop_dataviz.add_container)

        self.dlg.button_remove_dd_dataviz.setText('')
        # noinspection PyCallByClass,PyArgumentList
        self.dlg.button_remove_dd_dataviz.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
        self.dlg.button_remove_dd_dataviz.setToolTip(tr('Remove a container or a plot from the layout'))
        self.dlg.button_remove_dd_dataviz.clicked.connect(self.drag_drop_dataviz.remove_item)

        self.dlg.button_add_plot.setText('')
        self.dlg.button_add_plot.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.dlg.button_add_plot.setToolTip(tr('Add the plot in the layout'))
        self.dlg.button_add_plot.clicked.connect(self.drag_drop_dataviz.add_current_plot_from_combo)

        self.dlg.button_edit_dd_dataviz.setText('')
        self.dlg.button_edit_dd_dataviz.setIcon(QIcon(QgsApplication.iconPath('symbologyEdit.svg')))
        self.dlg.button_edit_dd_dataviz.setToolTip(tr('Edit the selected container/group'))
        self.dlg.button_edit_dd_dataviz.clicked.connect(self.drag_drop_dataviz.edit_row_container)

        # Layouts
        # Not connecting the "layoutAdded" signal, it's done when opening the Lizmap plugin
        # noinspection PyUnresolvedReferences
        self.project.layoutManager().layoutRenamed.connect(self.layout_renamed)
        # noinspection PyUnresolvedReferences
        self.project.layoutManager().layoutRemoved.connect(self.layout_removed)

        # Atlas
        self.dlg.label_atlas_34.setVisible(self.is_dev_version)

        self.iface.addPluginToWebMenu(None, self.action)
        self.iface.addWebToolBarIcon(self.action)

        self.dlg.button_reset_scales.clicked.connect(self.reset_scales)
        self.dlg.button_reset_scales.setIcon(QIcon(':/images/themes/default/console/iconClearConsole.svg'))

        server_side = tr(
            "This value will be replaced on the server side when evaluating the expression thanks to "
            "the QGIS server Lizmap plugin.")
        # Register variable helps
        if qgis_version() >= 32200:
            QgsExpression.addVariableHelpText(
                "lizmap_user",
                "{}<br/><br/>{}<br/><br/>{}".format(
                    tr("The current Lizmap login as a string."),
                    tr("It might be an empty string if the user is not connected."),
                    server_side,
                )
            )
            QgsExpression.addVariableHelpText(
                "lizmap_user_groups",
                "{}<br/><br/>{}<br/><br/>{}<br/><br/>{}".format(
                    tr("The current groups of the logged user as an <strong>array</strong>."),
                    tr("It might be an empty array if the user is not connected."),
                    tr(
                        "You might need to use functions in the <strong>Array</strong> expression category, such as "
                        "<pre>array_to_string</pre> to convert it to a string."),
                    server_side,
                )
            )
            QgsExpression.addVariableHelpText("lizmap_repository", tr("The current repository ID on the server."))

        # Let's fix the dialog to the first panel
        self.dlg.mOptionsListWidget.setCurrentRow(Panels.Information)
        # self.check_webdav()

    def check_dialog_validity(self) -> bool:
        """ Check the global dialog validity if we have :
         * at least one server
         * all servers with a login associated
         * LWC 3.5 doesn't check the status of QGIS server
         * LWC 3.6 must have a valid QGIS server setup
         * a QGS project

        Only the first tab is always allowed.
        All other tabs must have these conditions.

        Returns True if all tabs are available.
        """
        # self.check_webdav()
        # Check the current selected server in the combobox
        if not self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value):
            msg = tr('Please add your Lizmap server in the table below.')
            self.dlg.allow_navigation(False, msg)
            return False

        valid, msg = self.check_global_project_options()
        if not valid:
            self.dlg.allow_navigation(False, msg)
            return False

        # Project is valid, now check the server table validity
        # Somehow in tests, we don't have the variable
        if hasattr(self, 'server_manager') and not self.server_manager.check_validity_servers():
            msg = tr(
                'You must have all Lizmap servers with a valid URL and a login provided before using the plugin.'
            )
            self.dlg.allow_navigation(False, msg)
            return False

        metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        if not metadata:
            msg = tr(
                'The selected server in the combobox must be reachable. The server has not been reachable for {number} '
                'days.'
            ).format(number=MAX_DAYS)
            self.dlg.allow_navigation(False, msg)
            return False

        if self.update_plugin:
            msg = tr('Your plugin is outdated, please visit your QGIS plugin manager.')
            self.dlg.allow_navigation(False, msg)
            return False

        # self.check_webdav()
        self.dlg.allow_navigation(True)
        return True

    def add_new_layer(self, key):
        self.layers_table[key]['manager'].add_new_row()

    def move_layer_up(self, key):
        self.layers_table[key]['manager'].move_layer_up()

    def move_layer_down(self, key):
        self.layers_table[key]['manager'].move_layer_down()

    def edit_layer(self, key):
        self.layers_table[key]['manager'].edit_existing_row()

    def unload(self):
        """Remove the plugin menu item and icon."""
        self.iface.webMenu().removeAction(self.action)
        self.iface.removeWebToolBarIcon(self.action)

        if self.dock_html_preview:
            self.iface.removeDockWidget(self.dock_html_preview)
            del self.dock_html_preview

        if self.help_action:
            self.iface.pluginHelpMenu().removeAction(self.help_action)
            del self.help_action

        if self.help_action_cloud:
            self.iface.pluginHelpMenu().removeAction(self.help_action_cloud)
            del self.help_action_cloud

    def enable_popup_source_button(self):
        """Enable or not the "Configure" button according to the popup source."""
        data = self.layer_options_list['popupSource']['widget'].currentData()
        self.dlg.btConfigurePopup.setVisible(data in ('lizmap', 'qgis'))
        self.dlg.widget_qgis_maptip.setVisible(data == 'qgis')
        self.dlg.button_maptip_preview.setVisible(data == 'qgis')

        if data == 'lizmap':
            layer = self._current_selected_layer()
            self.dlg.widget_deprecated_lizmap_popup.setVisible(isinstance(layer, QgsVectorLayer))
        else:
            self.dlg.widget_deprecated_lizmap_popup.setVisible(False)

    def open_wizard_group_layer(self):
        """ Open the group wizard for the group/layer visibility. """
        current_item = self._current_selected_item_in_config()
        # The current selected item in the tree can be a layer or a group
        # https://github.com/3liz/lizmap-plugin/issues/437#issuecomment-1883485185
        if not current_item:
            return
        helper = tr("Setting groups visibility for the legend item '{}'").format(current_item)
        self._open_wizard_group(self.dlg.list_group_visibility, helper)
        # Trigger saving of the new value
        self.save_value_layer_group_data('group_visibility')

    def open_wizard_group_project(self):
        """ Open the group wizard for the project visibility. """
        helper = tr("Setting groups for the project visibility.")
        self._open_wizard_group(self.dlg.inAcl, helper)

    def _open_wizard_group(self, line_edit: QLineEdit, helper: str) -> Optional[str]:
        """ Open the group wizard and set the output in the line edit. """
        # Duplicated in base_edition_dialog.py, open_wizard_dialog()
        json_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        acl = json_metadata.get('acl')
        if not acl:
            QMessageBox.critical(
                self.dlg,
                tr('Upgrade your Lizmap instance'),
                tr(
                    "Your current Lizmap instance, running version {}, is not providing the needed information. "
                    "You should upgrade your Lizmap instance to at least 3.6.1 to use this wizard."
                ).format(json_metadata["info"]["version"]),
                QMessageBox.Ok
            )
            return None
        # End of duplicated

        current_acl = line_edit.text()
        wizard_dialog = WizardGroupDialog(helper, current_acl, acl['groups'])
        if not wizard_dialog.exec_():
            return None

        text = wizard_dialog.preview.text()
        if not text:
            return

        line_edit.setText(text)

    def show_help_question(self):
        """ According to the Lizmap server, ask the user which online help to open. """
        index = self.dlg.mOptionsListWidget.currentRow()
        page = MAPPING_INDEX_DOC.get(index)
        current_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        if not is_lizmap_cloud(current_metadata) and not page:
            self.show_help()
            return

        box = QMessageBox(self.dlg)
        box.setIcon(QMessageBox.Question)
        box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )
        box.setWindowTitle(tr('Online documentation'))
        box.setText(tr(
            'Different documentations are possible. Which online documentation would you like to open ?'
        ))

        if is_lizmap_cloud(current_metadata):
            cloud_help = QPushButton("Lizmap Hosting")
            box.addButton(cloud_help, QMessageBox.NoRole)

        if page:
            text = self.dlg.mOptionsListWidget.item(index).text()
            current_page = QPushButton(tr("Page '{}' in the plugin").format(text))
            box.addButton(current_page, QMessageBox.NoRole)
        else:
            current_page = None

        lwc_help = QPushButton("Lizmap Web Client")
        box.addButton(lwc_help, QMessageBox.YesRole)
        box.setStandardButtons(QMessageBox.Cancel)

        result = box.exec_()

        if result == QMessageBox.Cancel:
            return

        if box.clickedButton() == lwc_help:
            self.show_help()
        elif box.clickedButton() == current_page:
            self.show_help(page)
        else:
            self.show_help_cloud()

    @staticmethod
    def show_help(page=None):
        """ Opens the HTML online help with default browser and language. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(online_lwc_help(page))

    @staticmethod
    def show_help_cloud():
        """ Opens the HTML online cloud help with default browser and language. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(online_cloud_help())

    def enable_check_box_in_layer_tab(self, value: bool):
        """Enable/Disable checkboxes and fields of the Layer tab."""
        for key, item in self.layer_options_list.items():
            if item.get('widget') and key != 'sourceProject':
                item['widget'].setEnabled(value)
        self.dlg.btConfigurePopup.setEnabled(value)
        self.dlg.btQgisPopupFromForm.setEnabled(value)
        self.dlg.button_generate_html_table.setEnabled(value)

    def reset_scales(self):
        """ Reset scales in the line edit. """
        scales = ', '.join([str(i) for i in self.global_options['mapScales']['default']])
        if self.dlg.list_map_scales.text() != '':
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Question)
            box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.No)
            box.setWindowTitle(tr('Reset the scales'))
            box.setText(tr(
                'You have some scales predefined. Are you sure you want to reset with "{}" ?'
            ).format(scales))

            result = box.exec_()
            if result == QMessageBox.No:
                return

        self.dlg.list_map_scales.setText(scales)
        self.get_min_max_scales()

    def get_min_max_scales(self):
        """ Get minimum/maximum scales from scales input field. """
        LOGGER.info('Getting min/max scales')
        in_map_scales = self.dlg.list_map_scales.text()

        map_scales = [int(a.strip(' \t')) for a in in_map_scales.split(',') if str(a.strip(' \t')).isdigit()]
        # Remove scales which are lower or equal to 0
        map_scales = [i for i in map_scales if int(i) > 0]
        map_scales.sort()
        if len(map_scales) < 2:
            QMessageBox.critical(
                self.dlg,
                tr('Lizmap Error'),
                tr(
                    'Map scales: Write down integer scales separated by comma. '
                    'You must enter at least 2 min and max values.'),
                QMessageBox.Ok)
            min_scale = 1
            max_scale = 1000000000
        else:
            min_scale = min(map_scales)
            max_scale = max(map_scales)

        cleaned = ', '.join([str(i) for i in map_scales])

        self.dlg.list_map_scales.setText(cleaned)
        self.dlg.minimum_scale.setValue(min_scale)
        self.dlg.maximum_scale.setValue(max_scale)

    def read_cfg_file(self, skip_tables=False) -> dict:
        """Get the saved configuration from the project.qgs.cfg config file.

        Populate the gui fields accordingly

        skip_tables is only used in tests, as we don't have "table managers". It's only for testing the "layer" panel.
        """
        json_options = {}
        json_file = self.dlg.cfg_file()
        if json_file.exists():
            with open(json_file, encoding='utf-8') as f:
                json_file_reader = f.read()

            # noinspection PyBroadException
            try:
                sjson = json.loads(json_file_reader)
                json_options = sjson['options']
                for key in self.layers_table.keys():
                    if key in sjson:
                        self.layers_table[key]['jsonConfig'] = sjson[key]
                    else:
                        self.layers_table[key]['jsonConfig'] = {}

                    manager = self.layers_table[key].get('manager')
                    if manager:

                        manager.truncate()

                        if key == 'layouts':
                            manager.load_qgis_layouts(sjson.get(key, {}))
                            continue

                        if key in sjson:
                            manager.from_json(sjson[key])
                        else:
                            # get a subset of the data to give to the table form
                            data = {k: json_options[k] for k in json_options if k.startswith(manager.definitions.key())}
                            if data:
                                manager.from_json(data)

                        if key == 'datavizLayers':
                            # The drag&drop dataviz HTML layout
                            # First load plots into the combobox, because the main dataviz table has been loaded a few
                            # lines before
                            self.drag_drop_dataviz.load_dataviz_list_from_main_table()
                            # Then populate the tree. Icons and titles will use the combobox.
                            self.drag_drop_dataviz.load_tree_from_cfg(sjson['options'].get('dataviz_drag_drop', []))

            except Exception as e:
                if self.is_dev_version:
                    raise
                LOGGER.critical(e)
                copyfile(json_file, '{}.back'.format(json_file))
                message = tr(
                    'Errors encountered while reading the last layer tree state. '
                    'Please re-configure the options in the Layers tab completely. '
                    'The previous .cfg has been saved as .cfg.back')
                QMessageBox.critical(
                    self.dlg, tr('Lizmap Error'), message, QMessageBox.Ok)
                self.dlg.log_panel.append(message, abort=True, style=Html.P)
                LOGGER.critical('Error while reading the Lizmap configuration file')

        else:
            LOGGER.info('Lizmap CFG does not exist for this project.')
            for key in self.layers_table.keys():
                manager = self.layers_table[key].get('manager')
                if manager:
                    manager.truncate()

        # Set the global options (map, tools, etc.)
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item.get('tooltip'):
                    item['widget'].setToolTip(item.get('tooltip'))

                if item['wType'] == 'checkbox':
                    item['widget'].setChecked(item['default'])
                    if key in json_options:
                        item['widget'].setChecked(to_bool(json_options[key]))

                if item['wType'] in ('text', 'textarea'):
                    if isinstance(item['default'], (list, tuple)):
                        item['widget'].setText(", ".join(map(str, item['default'])))
                    else:
                        item['widget'].setText(str(item['default']))
                    if key in json_options:
                        if isinstance(json_options[key], (list, tuple)):
                            item['widget'].setText(", ".join(map(str, json_options[key])))
                        else:
                            item['widget'].setText(str(json_options[key]))

                if item['wType'] == 'extent':
                    if key in json_options:
                        extent = QgsRectangle(
                            json_options[key][0],
                            json_options[key][1],
                            json_options[key][2],
                            json_options[key][3]
                        )
                        item['widget'].setOriginalExtent(extent, self.project.crs())
                        item['widget'].setOutputExtentFromOriginal()

                if item['wType'] == 'wysiwyg':
                    item['widget'].set_html_content(str(item['default']))
                    if key in json_options:
                        item['widget'].set_html_content(json_options[key])

                if item['wType'] == 'spinbox':
                    item['widget'].setValue(int(item['default']))
                    if key in json_options:
                        item['widget'].setValue(int(json_options[key]))

                if item['wType'] == 'list':
                    if isinstance(item['list'][0], (list, tuple)):
                        # New way with icon, tooltip, translated label
                        pass
                    else:
                        # Legacy way
                        for i, item_config in enumerate(item['list']):
                            item['widget'].setItemData(i, item_config)

                        if item['default'] in item['list']:
                            index = item['widget'].findData(item['default'])
                            item['widget'].setCurrentIndex(index)

                    if key in json_options:
                        index = item['widget'].findData(json_options[key])
                        if index:
                            item['widget'].setCurrentIndex(index)

            map_scales = json_options.get('mapScales', self.global_options['mapScales']['default'])
            min_scale = json_options.get('minScale', self.global_options['minScale']['default'])
            max_scale = json_options.get('maxScale', self.global_options['maxScale']['default'])
            use_native = json_options.get('use_native_zoom_levels')
            project_crs = json_options.get('projection')
            if project_crs:
                project_crs = project_crs.get('ref')
            self.set_map_scales_in_ui(map_scales, min_scale, max_scale, use_native, project_crs)

        # Set layer combobox
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item['wType'] == 'layers':
                    if key in json_options:
                        for lyr in self.project.mapLayers().values():
                            if lyr.id() == json_options[key]:
                                item['widget'].setLayer(lyr)
                                break

        # Then set field combobox
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item['wType'] == 'fields':
                    if key in json_options:
                        item['widget'].setField(str(json_options[key]))

        self.dlg.check_ign_french_free_key()
        self.dlg.follow_map_theme_toggled()
        out = '' if json_file.exists() else 'out'
        LOGGER.info(f'Dialog has been loaded successful, with{out} Lizmap configuration file')

        if self.project.fileName().lower().endswith('qgs'):
            # Manage lizmap_user project variable
            variables = self.project.customVariables()
            if 'lizmap_user' in variables.keys() and not self.dlg.check_cfg_file_exists() and not skip_tables:
                # The variable 'lizmap_user' exists in the project as a variable
                # But no CFG was found, maybe the project has been renamed.
                message = tr(
                    'We have detected that this QGIS project has been used before with the Lizmap plugin (due to the '
                    'variable "lizmap_user" in your project properties dialog).'
                )
                message += '\n\n'
                message += tr(
                    "However, we couldn't detect the Lizmap configuration file '{}' anymore. A new "
                    "configuration from scratch is used."
                ).format(self.dlg.cfg_file())
                message += '\n\n'
                message += tr(
                    'Did you rename this QGIS project file ? If you want to keep your previous configuration, you '
                    'should find your previous Lizmap configuration file and use the path above. Lizmap will load it.'
                )
                QMessageBox.warning(
                    self.dlg, tr('New Lizmap configuration'), message, QMessageBox.Ok)

            # Add default variables in the project
            if not variables.get('lizmap_user'):
                variables['lizmap_user'] = ''
            if not variables.get('lizmap_user_groups'):
                variables['lizmap_user_groups'] = list()
            self.project.setCustomVariables(variables)

        self.layerList = dict()

        # Get embedded groups
        self.embeddedGroups = None

        # Fill the layer tree
        data = self.populate_layer_tree()

        # Fill base-layer startup
        self.on_baselayer_checkbox_change()
        self.set_startup_baselayer_from_config()
        self.dlg.default_lizmap_folder()

        # The return is used in tests
        return data

    def get_qgis_layer_by_id(self, my_id: str) -> Optional[QgsMapLayer]:
        """ Get a QgsMapLayer by its ID. """
        return self.project.mapLayers().get(my_id, None)

    def set_initial_extent_from_project(self):
        """ Set extent from QGIS server properties with the WMS advertised extent. """
        # The default extent widget does not have an input : QGIS server WMS properties
        wms_extent = self.project.readListEntry('WMSExtent', '')[0]
        if len(wms_extent) < 1:
            return

        wms_extent = [float(i) for i in wms_extent]
        extent = QgsRectangle(wms_extent[0], wms_extent[1], wms_extent[2], wms_extent[3])
        self.dlg.widget_initial_extent.setOutputExtentFromUser(
            extent, self.iface.mapCanvas().mapSettings().destinationCrs())
        LOGGER.info('Setting extent from the project')

    def remove_selected_layer_from_table(self, key):
        """
        Remove a layer from the list of layers
        for which to have the "locate by layer" tool
        """
        tw = self.layers_table[key]['tableWidget']
        tw.removeRow(tw.currentRow())
        LOGGER.info('Removing one row in table "{}"'.format(key))

    def new_added_layers(self, layers: List[QgsMapLayer]):
        """ Reminder to open the plugin to update the CFG file. """
        if not self.dlg.check_cfg_file_exists():
            # Not a Lizmap project
            return

        # Get layer IDs already in the CFG file
        layer_ids = [f['id'] for f in self.layers_config_file().values()]
        names = []
        for layer in layers:
            if layer.id() not in layer_ids:
                names.append(layer.name())

        if len(names) <= 0:
            # The new loaded layer was in the CFG already
            # It happens when we load the project
            return

        if len(names) >= 2:
            msg = tr("Some new layers have been detected into this Lizmap project.")
            prefix = tr("Layers")
        else:
            msg = tr("A new layer has been detected into this Lizmap project.")
            prefix = tr("Layer")

        LOGGER.info("New layer(s) detected : {}".format(','.join(names)))
        msg += ' ' + tr("Please open the plugin to update the Lizmap configuration file.") + ' '
        msg += prefix + ' : '
        msg += ','.join(names)
        self.iface.messageBar().pushMessage('Lizmap', msg, level=Qgis.Warning, duration=DURATION_WARNING_BAR)

    def layer_renamed(self, node, name: str):
        """ When a layer/group is renamed in the legend. """
        _ = node
        if not self.dlg.check_cfg_file_exists():
            # Not a Lizmap project
            return

        # Temporary workaround for
        # https://github.com/3liz/lizmap-plugin/issues/498
        msg = tr(
            "The layer '{}' has been renamed. The configuration in the Lizmap <b>Layers</b> tab only must be checked."
        ).format(name)
        self.iface.messageBar().pushMessage('Lizmap', msg, level=Qgis.Warning, duration=DURATION_WARNING_BAR)

    def remove_layer_from_table_by_layer_ids(self, layer_ids: list):
        """
        Remove layers from tables when deleted from layer registry
        """
        if not self.dlg.check_cfg_file_exists():
            return

        for key, item in self.layers_table.items():

            manager = self.layers_table[key].get('manager')
            if manager:
                manager.layers_has_been_deleted(layer_ids)
                continue

            tw = self.layers_table[key]['tableWidget']

            # Count lines
            tw_row_count = tw.rowCount()
            if not tw_row_count:
                continue

            # Get index of layerId column
            if 'layerId' not in self.layers_table[key]['cols']:
                continue
            idx = self.layers_table[key]['cols'].index('layerId') + 1

            # Remove layer if layerId match
            for row in range(tw_row_count):
                if tw.item(row, idx):
                    item_layer_id = str(tw.item(row, idx).text())
                    if item_layer_id in layer_ids:
                        tw.removeRow(row)

        LOGGER.info('Layer ID "{}" has been removed from the project'.format(layer_ids))

    def layout_renamed(self, layout, new_name: str):
        """ When a layout has been renamed in the project. """
        if not self.dlg.check_cfg_file_exists():
            return

        self.layers_table['layouts']['manager'].layout_renamed(layout, new_name)

    def layout_removed(self, name: str):
        """ When a layout has been removed from the project. """
        if not self.dlg.check_cfg_file_exists():
            return

        self.layers_table['layouts']['manager'].layout_removed(name)

    def check_wfs_is_checked(self, layer: QgsVectorLayer):
        """ Check if the layer is published as WFS. """
        if not is_layer_published_wfs(self.project, layer.id()):
            self.display_error(tr(
                'The layers you have chosen for this tool must be checked in the "WFS Capabilities" option of the '
                'QGIS Server tab in the "Project Properties" dialog.'))
            return False
        return True

    def display_error(self, message):
        QMessageBox.critical(
            self.dlg,
            tr('Lizmap Error'),
            message,
            QMessageBox.Ok)

    def set_tree_item_data(self, item_type, item_key, json_layers):
        """Define default data or data from previous configuration for one item (layer or group)
        Used in the method populateLayerTree
        """
        # Type : group or layer
        self.myDic[item_key]['type'] = item_type

        # DEFAULT VALUES : generic default values for layers and group
        self.myDic[item_key]['name'] = item_key
        for key, item in self.layer_options_list.items():
            self.myDic[item_key][key] = item['default']
        self.myDic[item_key]['title'] = self.myDic[item_key]['name']

        if item_type == 'group':
            # embedded group ?
            if self.embeddedGroups and item_key in self.embeddedGroups:
                p_name = self.embeddedGroups[item_key]['project']
                p_name = os.path.splitext(os.path.basename(p_name))[0]
                self.myDic[item_key]['sourceProject'] = p_name

        # DEFAULT VALUES : layers have got more precise data
        keep_metadata = False
        if item_type == 'layer':

            # layer name
            layer = self.get_qgis_layer_by_id(item_key)
            self.myDic[item_key]['name'] = layer.name()
            # title and abstract
            self.myDic[item_key]['title'] = layer.name()
            if layer.title():
                self.myDic[item_key]['title'] = layer.title()
                keep_metadata = True
            if layer.abstract():
                self.myDic[item_key]['abstract'] = layer.abstract()
                keep_metadata = True

            if not self.myDic[item_key]['link']:
                self.myDic[item_key]['link'] = layer_property(layer, LayerProperties.DataUrl)

            # hide non geo layers (csv, etc.)
            # if layer.type() == 0:
            #    if layer.geometryType() == 4:
            #        self.l display = False

            # layer scale visibility
            if layer.hasScaleBasedVisibility():
                self.myDic[item_key]['minScale'] = layer.maximumScale()
                self.myDic[item_key]['maxScale'] = layer.minimumScale()
            # toggled : check if layer is toggled in qgis legend
            # self.myDic[itemKey]['toggled'] = layer.self.iface.legendInterface().isLayerVisible(layer)
            self.myDic[item_key]['toggled'] = False
            # group as layer : always False obviously because it is already a layer
            self.myDic[item_key]['groupAsLayer'] = False
            # embedded layer ?
            from_project = self.project.layerIsEmbedded(item_key)
            if os.path.exists(from_project):
                p_name = os.path.splitext(os.path.basename(from_project))[0]
                self.myDic[item_key]['sourceProject'] = p_name

        # OVERRIDE DEFAULT FROM CONFIGURATION FILE
        if self.myDic[item_key]['name'] in json_layers:
            json_key = self.myDic[item_key]['name']
            LOGGER.info('Reading configuration from dictionary for layer {}'.format(json_key))
            # loop through layer options to override
            for key, item in self.layer_options_list.items():
                # override only for ui widgets
                if item.get('widget'):
                    if key in json_layers[json_key]:

                        if key == 'legend_image_option' and 'noLegendImage' in json_layers[json_key]:
                            if self.myDic[item_key].get('legend_image_option'):
                                # The key is already set before with noLegendImage
                                LOGGER.info(
                                    "Skip key legend_image_option because it has been set previously with noLegendImage"
                                )
                                continue

                        # checkboxes
                        if item['wType'] == 'checkbox':
                            self.myDic[item_key][key] = to_bool(json_layers[json_key][key], False)
                        # spin box
                        elif item['wType'] == 'spinbox':
                            if json_layers[json_key][key] != '':
                                self.myDic[item_key][key] = json_layers[json_key][key]
                        # text inputs
                        elif item['wType'] in ('text', 'textarea'):
                            if json_layers[json_key][key] != '':
                                if item.get('isMetadata'):  # title and abstract
                                    if not keep_metadata:
                                        self.myDic[item_key][key] = json_layers[json_key][key]
                                else:
                                    self.myDic[item_key][key] = json_layers[json_key][key]
                        # lists
                        elif item['wType'] == 'list':
                            # New way with data, label, tooltip and icon
                            datas = [j[0] for j in item['list']]
                            if json_layers[json_key][key] in datas:
                                self.myDic[item_key][key] = json_layers[json_key][key]

                else:
                    if key == 'noLegendImage' and 'noLegendImage' in json_layers.get(json_key):
                        tmp = 'hide_at_startup'  # Default value
                        if to_bool(json_layers[json_key].get('noLegendImage')):
                            tmp = 'disabled'
                        self.myDic[item_key]['legend_image_option'] = tmp

                    # LOGGER.info('Skip key {} because no UI widget'.format(key))

                # popupContent
                if key == 'popupTemplate':
                    if key in json_layers[json_key]:
                        self.myDic[item_key][key] = json_layers[json_key][key]

    def process_node(self, node, parent_node, json_layers):
        """
        Process a single node of the QGIS layer tree and adds it to Lizmap layer tree.

        Recursive function when it's a group in the legend.
        """
        for child in node.children():
            if QgsLayerTree.isGroup(child):
                child = cast_to_group(child)
                child_id = child.name()
                child_type = 'group'
                # noinspection PyCallByClass,PyArgumentList
                child_icon = QIcon(QgsApplication.iconPath('mActionFolder.svg'))
            elif QgsLayerTree.isLayer(child):
                child = cast_to_layer(child)
                child_id = child.layerId()
                child_type = 'layer'
                # noinspection PyArgumentList
                child_icon = QgsMapLayerModel.iconForLayer(child.layer())
            else:
                raise Exception('Unknown child type')

            # Select an existing item, select the header item or create the item
            if child_id in self.myDic:
                # If the item already exists in self.myDic, select it
                item = self.myDic[child_id]['item']

            elif child_id == '':
                # If the id is empty string, this is a root layer, select the headerItem
                item = self.dlg.layer_tree.headerItem()

            else:
                # else create the item and add it to the header item
                # add the item to the dictionary
                self.myDic[child_id] = {'id': child_id}
                if child_type == 'group':
                    # it is a group
                    self.set_tree_item_data('group', child_id, json_layers)
                else:
                    # it is a layer
                    self.set_tree_item_data('layer', child_id, json_layers)

                predefined_group = PredefinedGroup.No.value
                if parent_node is None:
                    if self.myDic[child_id]['name'] == 'hidden':
                        predefined_group = PredefinedGroup.Hidden.value
                    if self.myDic[child_id]['name'] == 'baselayers':
                        predefined_group = PredefinedGroup.Baselayers.value
                    if self.myDic[child_id]['name'].lower() == 'overview':
                        predefined_group = PredefinedGroup.Overview.value

                elif parent_node.data(0, Qt.UserRole + 1) == PredefinedGroup.Baselayers.value:
                    # Parent is "baselayers", children will be an item in the dropdown menu
                    predefined_group = PredefinedGroup.BaselayerItem.value
                elif parent_node.data(0, Qt.UserRole + 1) != PredefinedGroup.No.value:
                    # Others will be in "hidden" or "overview".
                    # TODO fixme maybe ?
                    predefined_group = PredefinedGroup.Hidden.value

                item = QTreeWidgetItem(
                    [
                        str(self.myDic[child_id]['name']),
                        str(self.myDic[child_id]['id']),
                        self.myDic[child_id]['type']
                    ]
                )
                if predefined_group != PredefinedGroup.No.value:
                    text = tr('Special group for Lizmap Web Client')
                    if self.is_dev_version:
                        # For debug purpose only about groups
                        text += f'. Data group ID {Qt.UserRole} : {predefined_group}'  # NOQA E203
                    item.setToolTip(0, self.myDic[child_id]['name'] + ' - ' + text)
                elif is_layer_wms_excluded(self.project, self.myDic[child_id]['name']):
                    text = tr(
                        'The layer is excluded from WMS service, in the '
                        '"Project Properties" → "QGIS Server" → "WMS" → "Excluded Layers"'
                    )
                    item.setToolTip(0, self.myDic[child_id]['name'] + ' - ' + text)
                else:
                    item.setToolTip(0, self.myDic[child_id]['name'])
                item.setIcon(0, child_icon)
                item.setData(0, Qt.UserRole + 1, predefined_group)
                self.myDic[child_id]['item'] = item

                # Move group or layer to its parent node
                if not parent_node:
                    self.dlg.layer_tree.addTopLevelItem(item)
                else:
                    parent_node.addChild(item)

            if child_type == 'group':
                self.process_node(child, item, json_layers)

    def layers_config_file(self) -> dict:
        """ Read the CFG file and returns the JSON content about 'layers'. """
        if not self.dlg.check_cfg_file_exists():
            return {}

        with open(self.dlg.cfg_file(), encoding='utf8') as f:
            json_file_reader = f.read()

        # noinspection PyBroadException
        try:
            sjson = json.loads(json_file_reader)
            return sjson['layers']
        except Exception:
            if self.is_dev_version:
                raise
            message = tr(
                'Errors encountered while reading the last layer tree state. '
                'Please re-configure the options in the Layers tab completely'
            )
            QMessageBox.critical(self.dlg, tr('Lizmap Error'), '', QMessageBox.Ok)
            self.dlg.log_panel.append(message, abort=True, style=Html.P)
            return {}

    def populate_layer_tree(self) -> dict:
        """Populate the layer tree of the Layers tab from QGIS legend interface.

        Needs to be refactored.
        """
        self.dlg.layer_tree.clear()
        self.myDic = {}

        json_layers = self.layers_config_file()
        root = self.project.layerTreeRoot()

        # Recursively process layer tree nodes
        self.process_node(root, None, json_layers)
        self.dlg.layer_tree.expandAll()

        # Add the self.myDic to the global layerList dictionary
        self.layerList = self.myDic

        self.enable_check_box_in_layer_tab(False)

        # The return is used in tests
        return json_layers

    def from_data_to_ui_for_layer_group(self):
        """ Restore layer/group values into each field when selecting a layer in the tree. """
        # At the beginning, enable all widgets.
        self.dlg.panel_layer_all_settings.setEnabled(True)
        self.dlg.group_layer_metadata.setEnabled(True)
        self.dlg.group_layer_tree_options.setEnabled(True)
        self.dlg.checkbox_popup.setEnabled(True)
        self.dlg.frame_layer_popup.setEnabled(True)
        self.dlg.group_layer_embedded.setEnabled(True)
        # for key, val in self.layer_options_list.items():
        #     if val.get('widget'):
        #         val.get('widget').setEnabled(True)

        i_key = self._current_selected_item_in_config()
        if i_key:
            self.enable_check_box_in_layer_tab(True)
        else:
            self.enable_check_box_in_layer_tab(False)

        # i_key can be either a layer name or a group name
        if i_key:
            # get information about the layer or the group from the layerList dictionary
            selected_item = self.layerList[i_key]

            # set options
            for key, val in self.layer_options_list.items():
                if val.get('widget'):

                    if val.get('tooltip'):
                        val['widget'].setToolTip(val.get('tooltip'))

                    if val['wType'] in ('text', 'textarea'):
                        if val['type'] == 'list':
                            data = selected_item[key]
                            if isinstance(data, str):
                                # It should be a list, but it has been temporary a string during the dev process
                                data = [data]
                            text = ','.join(data)
                        else:
                            text = selected_item[key]
                        if val['wType'] == 'text':
                            val['widget'].setText(text)
                        else:
                            # Abstract is the only textarea
                            val['widget'].setPlainText(text)
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(int(selected_item[key]))
                    elif val['wType'] == 'checkbox':
                        val['widget'].setChecked(selected_item[key])
                        children = val.get('children')
                        if children:
                            exclusive = val.get('exclusive', False)
                            if exclusive:
                                is_enabled = not selected_item[key]
                            else:
                                is_enabled = selected_item[key]
                            self.layer_options_list[children]['widget'].setEnabled(is_enabled)
                            if self.layer_options_list[children]['wType'] == 'checkbox' and not is_enabled:
                                if self.layer_options_list[children]['widget'].isChecked():
                                    self.layer_options_list[children]['widget'].setChecked(False)

                    elif val['wType'] == 'list':
                        # New way with data, label, tooltip and icon
                        index = val['widget'].findData(selected_item[key])

                        if index < 0 and val.get('default'):
                            # Get back to default
                            index = val['widget'].findData(val['default'])

                        val['widget'].setCurrentIndex(index)

                    # deactivate wms checkbox if not needed
                    if key == 'externalWmsToggle':
                        wms_enabled = self.get_item_wms_capability(selected_item)
                        if wms_enabled is not None:
                            self.dlg.cbExternalWms.setEnabled(wms_enabled)
                            if wms_enabled:
                                self.dlg.cbExternalWms.toggled.connect(self.external_wms_toggled)
                                self.external_wms_toggled()
                            else:
                                self.dlg.cbExternalWms.setChecked(False)
                                try:
                                    self.dlg.cbExternalWms.toggled.disconnect(self.external_wms_toggled)
                                except TypeError:
                                    # The object was not connected
                                    pass

            layer = self._current_selected_layer()  # It can be a layer or a group

            # Disable popup configuration for groups and raster
            # Disable QGIS popup for layer without geom
            is_vector = isinstance(layer, QgsVectorLayer)
            # noinspection PyUnresolvedReferences
            has_geom = is_vector and layer.wkbType() != QgsWkbTypes.NoGeometry
            self.dlg.btConfigurePopup.setEnabled(has_geom)
            self.dlg.btQgisPopupFromForm.setEnabled(is_vector)
            self.dlg.button_generate_html_table.setEnabled(is_vector)
            self.layer_options_list['popupSource']['widget'].setEnabled(is_vector)

            if self.current_lwc_version() >= LwcVersions.Lizmap_3_7 and not self.dlg.cbLayerIsBaseLayer.isChecked():
                # Starting from LWC 3.7, this checkbox is deprecated
                self.dlg.cbLayerIsBaseLayer.setEnabled(False)

            # For a group, there isn't the toggle option, #298, TEMPORARY DISABLED
            tooltip = tr(
                "If the layer is displayed by default. On a layer, if the map theme is used, this checkbox does not "
                "have any effect.")
            self.layer_options_list['toggled']['widget'].setToolTip(tooltip)
            # try:
            #     # We always disconnect everything
            #     self.layer_options_list['groupAsLayer']['widget'].disconnect()
            # except TypeError:
            #     pass
            #
            # if isinstance(layer, QgsMapLayer):
            #     # Always enabled
            #     self.layer_options_list['toggled']['widget'].setEnabled(True)
            #     tooltip = tr("If the layer is displayed by default")
            #     self.layer_options_list['toggled']['widget'].setToolTip(tooltip)
            # else:
            #     # It depends on the "Group as layer" checked or not, so it has a signal
            #     self.layer_options_list['groupAsLayer']['widget'].stateChanged.connect(
            #         self.enable_or_not_toggle_checkbox)
            #     self.enable_or_not_toggle_checkbox()

            # Checkbox display children features
            self.dlg.relation_stacked_widget.setCurrentWidget(self.dlg.page_no_relation)
            if is_vector:
                if len(self.project.relationManager().referencedRelations(layer)) >= 1:
                    # We display options
                    self.dlg.relation_stacked_widget.setCurrentWidget(self.dlg.page_display_relation)

        else:
            # set default values for this layer/group
            for key, val in self.layer_options_list.items():
                if val.get('widget'):
                    if val['wType'] in ('text', 'textarea'):
                        if isinstance(val['default'], (list, tuple)):
                            text = ','.join(val['default'])
                        else:
                            text = val['default']
                        if val['wType'] == 'text':
                            val['widget'].setText(text)
                        else:
                            # Abstract is the only textarea for now
                            # We shouldn't have any default value, but let's support it
                            val['widget'].setPlainText(text)
                    elif val['wType'] == 'spinbox':
                        val['widget'].setValue(val['default'])
                    elif val['wType'] == 'checkbox':
                        val['widget'].setChecked(val['default'])
                    elif val['wType'] == 'list':

                        # New way with data, label, tooltip and icon
                        index = val['widget'].findData(val['default'])
                        val['widget'].setCurrentIndex(index)

        self.enable_popup_source_button()
        self.dlg.follow_map_theme_toggled()

        if self.current_lwc_version() >= LwcVersions.Lizmap_3_7:
            if self._current_item_predefined_group() == PredefinedGroup.BaselayerItem.value:
                self.dlg.group_layer_tree_options.setEnabled(False)
                self.dlg.checkbox_popup.setEnabled(False)
                self.dlg.frame_layer_popup.setEnabled(False)
                self.dlg.group_layer_embedded.setEnabled(False)

            elif self._current_item_predefined_group() in (
                    PredefinedGroup.Overview.value,
                    PredefinedGroup.Baselayers.value,
                    PredefinedGroup.BackgroundColor.value,
                    PredefinedGroup.Hidden.value,
            ):
                self.dlg.panel_layer_all_settings.setEnabled(False)

        layer = self._current_selected_layer()
        if isinstance(layer, QgsMapLayer):
            if is_layer_wms_excluded(self.project, layer.name()):
                self.dlg.panel_layer_all_settings.setEnabled(False)

    # def enable_or_not_toggle_checkbox(self):
    #     """ Only for groups, to determine the state of the "toggled" option. """
    #     if self.layer_options_list['groupAsLayer']['widget'].isChecked():
    #         self.layer_options_list['toggled']['widget'].setEnabled(True)
    #         tooltip = tr(
    #             "All layers in this group are considered as a unique layer. This new layer can be displayed "
    #             "or not.")
    #     else:
    #         self.layer_options_list['toggled']['widget'].setEnabled(False)
    #         self.layer_options_list['toggled']['widget'].setChecked(False)
    #         tooltip = tr("For a group, it depends on layers inside the group")
    #     self.layer_options_list['toggled']['widget'].setToolTip(tooltip)

    def external_wms_toggled(self):
        """ Disable the format combobox is the checkbox third party WMS is checked. """
        self.dlg.liImageFormat.setEnabled(not self.dlg.cbExternalWms.isChecked())

    def get_item_wms_capability(self, selected_item) -> Optional[bool]:
        """
        Check if an item in the tree is a layer
        and if it is a WMS layer
        """
        wms_enabled = False
        is_layer = selected_item['type'] == 'layer'
        if is_layer:
            layer = self.get_qgis_layer_by_id(selected_item['id'])
            if not layer:
                return
            if layer.providerType() in ['wms']:
                if get_layer_wms_parameters(layer):
                    wms_enabled = True
        return wms_enabled

    @staticmethod
    def existing_group(
            root_group: QgsLayerTree, label: str, index: bool = False) -> Optional[Union[QgsLayerTreeGroup, int]]:
        """ Return the existing group in the legend if existing.

        It will either return the group itself if found, or its index.
        """
        if not root_group:
            return None

        # Iterate over all child (layers and groups)
        children = root_group.children()
        i = -1
        for child in children:
            if not QgsLayerTree.isGroup(child):
                i += 1
                continue

            qgis_group = cast_to_group(child)
            qgis_group: QgsLayerTreeGroup
            count_children = len(qgis_group.children())
            if count_children >= 1 or qgis_group.name() == label:
                # We do not want to count empty groups
                # Except for the one we are looking for
                i += 1

            if qgis_group.name() == label:
                return i if index else qgis_group

        return None

    def _add_group_legend(
            self, label: str, exclusive: bool = False, parent: QgsLayerTreeGroup = None,
            project: QgsProject = None) -> QgsLayerTreeGroup:
        """ Add a group in the legend. """
        if project is None:
            project = self.project

        if parent:
            root_group = parent
        else:
            root_group = project.layerTreeRoot()

        qgis_group = self.existing_group(root_group, label)
        if qgis_group:
            return qgis_group

        new_group = root_group.addGroup(label)
        if exclusive:
            new_group.setIsMutuallyExclusive(True, -1)
        return new_group

    def disable_legacy_empty_base_layer(self):
        """ Legacy checkbox until it's removed. """
        # We suppose we are in LWC >= 3.7 otherwise the button is blue
        if self.current_lwc_version() >= LwcVersions.Lizmap_3_7:
            self.dlg.cbAddEmptyBaselayer.setChecked(False)

    def add_group_hidden(self):
        """ Add the hidden group. """
        self._add_group_legend(GroupNames.Hidden)

    def add_group_baselayers(self):
        """ Add the baselayers group. """
        self._add_group_legend(GroupNames.BaseLayers)
        self.disable_legacy_empty_base_layer()

    def add_group_empty(self):
        """ Add the default background color. """
        baselayers = self._add_group_legend(GroupNames.BaseLayers)
        self._add_group_legend(GroupNames.BackgroundColor, parent=baselayers)
        self.disable_legacy_empty_base_layer()

    def add_group_overview(self):
        """ Add the overview group. """
        label = 'overview'
        if self.current_lwc_version() < LwcVersions.Lizmap_3_7:
            label = 'Overview'
        self._add_group_legend(label, exclusive=False)

    def add_osm_mapnik(self):
        """ Add the OSM mapnik base layer. """
        source = 'type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png'
        self._add_base_layer(
            source,
            'OpenStreetMap',
            'https://openstreetmap.org',
            '© ' + tr('OpenStreetMap contributors'))

    def add_osm_opentopomap(self):
        """ Add the OSM OpenTopoMap base layer. """
        source = 'type=xyz&url=https://tile.opentopomap.org/{z}/{x}/{y}.png'
        self._add_base_layer(
            source,
            'OpenTopoMap',
            'https://openstreetmap.org',
            '© ' + tr('OpenStreetMap contributors') + ', SRTM, © OpenTopoMap (CC-BY-SA)')

    def add_french_ign_layer(self, layer: IgnLayer):
        """ Add some French IGN layers. """
        params = {
            'crs': 'EPSG:3857',
            'dpiMode': 7,
            'format': layer.format,
            'layers': layer.name,
            'styles': 'normal',
            'tileMatrixSet': 'PM',
            'url': 'https://data.geopf.fr/wmts?SERVICE%3DWMTS%26VERSION%3D1.0.0%26REQUEST%3DGetCapabilities',
        }
        # Do not use urlencode
        source = '&'.join(['{}={}'.format(k, v) for k, v in params.items()])
        self._add_base_layer(source, layer.title, 'https://www.ign.fr/', 'IGN France')

    def _add_base_layer(self, source: str, name: str, attribution_url: str = None, attribution_name: str = None):
        """ Add a base layer to the "baselayers" group. """
        self.add_group_baselayers()
        raster = QgsRasterLayer(source, name, 'wms')
        self.project.addMapLayer(raster, False)  # False to not add it in the legend, only in the project

        if attribution_url:
            raster.setAttributionUrl(attribution_url)
        if attribution_name:
            raster.setAttribution(attribution_name)
        root_group = self.project.layerTreeRoot()

        groups = root_group.findGroups()
        for qgis_group in groups:
            qgis_group: QgsLayerTreeGroup
            if qgis_group.name() == 'baselayers':
                node = qgis_group.addLayer(raster)
                node.setExpanded(False)
                break

        self.dlg.display_message_bar(
            tr('New layer'),
            tr('Please close and reopen the dialog to display your layer in the tab "{tab_name}".').format(
                tab_name=self.dlg.mOptionsListWidget.item(Panels.Layers).text()
            ),
            Qgis.Warning,
        )

    @staticmethod
    def string_to_list(text):
        """ Format a string to a list. """
        data = text.split(',') if len(text) > 0 else []
        data = [item.strip() for item in data]
        return data

    def save_value_layer_group_data(self, key: str):
        """ Save the new value from the UI in the global layer property self.layerList.

        Function called the corresponding UI widget has sent changed signal.
        """
        key = str(key)
        layer_or_group_text = self._current_selected_item_in_config()
        if not layer_or_group_text:
            return

        # get the definition for this property
        layer_option = self.layer_options_list[key]
        # modify the property for the selected item
        if layer_option['wType'] == 'text':
            text = layer_option['widget'].text()
            if layer_option['type'] == 'list':
                text = self.string_to_list(text)
            self.layerList[layer_or_group_text][key] = text
            self.set_layer_metadata(layer_or_group_text, key)
        elif layer_option['wType'] == 'textarea':
            self.layerList[layer_or_group_text][key] = layer_option['widget'].toPlainText()
            self.set_layer_metadata(layer_or_group_text, key)
        elif layer_option['wType'] == 'spinbox':
            self.layerList[layer_or_group_text][key] = layer_option['widget'].value()
        elif layer_option['wType'] == 'checkbox':
            checked = layer_option['widget'].isChecked()
            self.layerList[layer_or_group_text][key] = checked
            children = layer_option.get('children')
            if children:
                exclusive = layer_option.get('exclusive', False)
                if exclusive:
                    is_enabled = not checked
                else:
                    is_enabled = checked
                self.layer_options_list[children]['widget'].setEnabled(is_enabled)
                if self.layer_options_list[children]['wType'] == 'checkbox' and not is_enabled:
                    if self.layer_options_list[children]['widget'].isChecked():
                        self.layer_options_list[children]['widget'].setChecked(False)
        elif layer_option['wType'] == 'list':
            # New way with data, label, tooltip and icon
            datas = [j[0] for j in layer_option['list']]
            self.layerList[layer_or_group_text][key] = datas[layer_option['widget'].currentIndex()]

        # Deactivate the "exclude" widget if necessary
        if 'exclude' in layer_option \
                and layer_option['wType'] == 'checkbox' \
                and layer_option['widget'].isChecked() \
                and layer_option['exclude']['widget'].isChecked():
            layer_option['exclude']['widget'].setChecked(False)
            self.layerList[layer_or_group_text][layer_option['exclude']['key']] = False

    def set_layer_metadata(self, layer_or_group: str, key: str):
        """Set the title/abstract/link QGIS metadata when the corresponding item is changed
        Used in setLayerProperty"""
        if 'isMetadata' not in self.layer_options_list[key]:
            return

        # modify the layer.title|abstract|link() if possible
        if self.layerList[layer_or_group]['type'] != 'layer':
            return

        layer = self.get_qgis_layer_by_id(layer_or_group)
        if not isinstance(layer, QgsMapLayer):
            return

        if key == 'title':
            layer.setTitle(self.layerList[layer_or_group][key])

        if key == 'abstract':
            layer.setAbstract(self.layerList[layer_or_group][key])

    def convert_html_maptip(self):
        """ Trying to convert a Lizmap popup to HTML popup. """
        layer_or_group = self._current_selected_item_in_config()
        if not layer_or_group:
            return

        if 'popupTemplate' not in self.layerList[layer_or_group]:
            return

        self.layerList[layer_or_group]['popup'] = True
        text = self.layerList[layer_or_group]['popupTemplate']

        layer = self._current_selected_layer()
        html, errors = convert_lizmap_popup(text, layer)
        if errors:
            QMessageBox.warning(
                self.dlg,
                tr('Lizmap - Warning'),
                tr(
                    'Some fields or alias could not be found in the layer. You must check the result manually '
                    'about these values below :'
                ) + '<br><br>' + ','.join(errors),
                QMessageBox.Ok)

        flag = self._set_maptip(layer, html)
        if flag:
            index = self.layer_options_list['popupSource']['widget'].findData('qgis')
            self.layer_options_list['popupSource']['widget'].setCurrentIndex(index)

    def configure_html_abstract(self):
        """ Open the dialog for setting HTML for the abstract. """
        if not self._current_selected_item_in_config():
            return

        html_editor = HtmlEditorDialog()
        html_editor.editor.set_html_content(self.dlg.teLayerAbstract.toPlainText())
        if not html_editor.exec_():
            return

        self.dlg.teLayerAbstract.setPlainText(html_editor.editor.html_content())

    def configure_html_popup(self):
        """Open the dialog with a text field to store the popup template for one layer/group"""
        # get the selected item in the layer tree
        layer_or_group = self._current_selected_item_in_config()
        if not layer_or_group:
            return

        # do nothing if no popup configured for this layer/group
        if not to_bool(self.layerList[layer_or_group]['popup']):
            return

        # Set the content of the QTextEdit if needed
        if 'popupTemplate' in self.layerList[layer_or_group]:
            self.layerList[layer_or_group]['popup'] = True
            text = self.layerList[layer_or_group]['popupTemplate']
        else:
            text = ''

        LOGGER.info('Opening the popup configuration')

        layer = self._current_selected_layer()
        data = self.layer_options_list['popupSource']['widget'].currentData()
        if data == 'lizmap':
            # Legacy
            # Lizmap HTML popup
            if isinstance(layer, QgsVectorLayer):
                LOGGER.warning("The 'lizmap' popup is deprecated for vector layer. This will be removed soon.")

            popup_dialog = LizmapPopupDialog(text)
            if not popup_dialog.exec_():
                return

            content = popup_dialog.txtPopup.text()

            # Get the selected item in the layer tree
            layer_or_group = self._current_selected_item_in_config()
            if not layer_or_group:
                return
            # Write the content into the global object
            self.layerList[layer_or_group]['popupTemplate'] = content
            if isinstance(layer, QgsVectorLayer):
                LOGGER.warning("The 'lizmap' popup is deprecated for vector layer. This will be removed soon.")

        else:
            # QGIS HTML maptip
            layer: QgsVectorLayer
            html_editor = HtmlEditorDialog()
            html_editor.set_layer(layer)
            html_editor.editor.set_html_content(layer.mapTipTemplate())
            if not html_editor.exec_():
                return

            self._set_maptip(layer, html_editor.editor.html_content(), False)

    def _current_item_predefined_group(self) -> Optional[PredefinedGroup]:
        """ Get the current group type. """
        item = self.dlg.layer_tree.currentItem()
        if not item:
            return None

        text = item.text(1)
        if text not in self.layerList:
            return None

        return item.data(0, Qt.UserRole + 1)

    def _current_selected_item_in_config(self) -> Optional[str]:
        """ Either a group or a layer name. """
        item = self.dlg.layer_tree.currentItem()
        if not item:
            return

        text = item.text(1)
        if text not in self.layerList:
            return

        return text

    def _current_selected_layer(self) -> Optional[QgsMapLayer]:
        """ Current selected map layer in the tree. """
        lid = self._current_selected_item_in_config()
        if not lid:
            LOGGER.warning('No item selected in the Lizmap layer tree.')
            return

        layers = [layer for layer in self.project.mapLayers().values() if layer.id() == lid]
        if not layers:
            LOGGER.warning('Layers not found with searched text from the tree : {}'.format(lid))
            return

        layer = layers[0]
        return layer

    def link_from_properties(self):
        """ Button set link from layer in the Lizmap configuration. """
        layer = self._current_selected_layer()
        value = layer_property(layer, LayerProperties.DataUrl)
        self.layer_options_list['link']['widget'].setText(value)

    def open_media_file_browser(self):
        """ Open the file picker for media. """
        data_path, _ = QFileDialog.getOpenFileName(None, tr('Open media'), self.project.absolutePath())
        if not data_path:
            return
        # TODO check
        # Maximum allowed parent folder
        # ../media or media/
        media_path = relpath(data_path, self.project.absolutePath())
        self.layer_options_list['link']['widget'].setText(media_path)

    def _set_maptip(self, layer: QgsVectorLayer, html_content: str, check: bool = True) -> bool:
        """ Internal function to set the maptip on a layer. """
        if check and layer.mapTipTemplate() != '':
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Question)
            box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')),)
            box.setWindowTitle(tr('Existing maptip for layer {}').format(layer.title()))
            box.setText(tr(
                'A maptip already exists for this layer. This is going to override it. '
                'Are you sure you want to continue ?'))
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.No)
            result = box.exec_()
            if result == QMessageBox.No:
                return False

        layer.setMapTipTemplate(html_content)
        QMessageBox.information(
            self.dlg,
            tr('Maptip'),
            tr('The maptip has been set in the layer "{}".').format(layer.name()),
            QMessageBox.Ok
        )
        self.dock_html_preview.update_html()
        return True

    def html_table_from_layer(self):
        """ Button set popup maptip from layer in the Lizmap configuration. """
        layer = self._current_selected_layer()
        if not isinstance(layer, QgsVectorLayer):
            return

        html_maptip_dialog = HtmlMapTipDialog(layer)
        if not html_maptip_dialog.exec_():
            return

        result = html_maptip_dialog.map_tip()
        self._set_maptip(layer, result, False)

    def maptip_from_form(self):
        """ Button set popup maptip from DND form in the Lizmap configuration. """
        layer = self._current_selected_layer()
        if not isinstance(layer, QgsVectorLayer):
            return

        config = layer.editFormConfig()
        # noinspection PyUnresolvedReferences
        if config.layout() != QgsEditFormConfig.TabLayout:
            LOGGER.warning('Maptip : the layer is not using a drag and drop form.')
            QMessageBox.warning(
                self.dlg,
                tr('Lizmap - Warning'),
                tr('The form for this layer is not a drag and drop layout.'),
                QMessageBox.Ok)
            return

        root = config.invisibleRootContainer()
        relation_manager = self.project.relationManager()
        html_content = Tooltip.create_popup_node_item_from_form(layer, root, 0, [], '', relation_manager)
        html_content = Tooltip.create_popup(html_content)
        html_content += Tooltip.css()
        self._set_maptip(layer, html_content)

    def write_project_config_file(self, lwc_version: LwcVersions, with_gui: bool = True) -> bool:
        """ Write a Lizmap configuration to the file. """
        liz2json = self.project_config_file(lwc_version, with_gui)
        if not liz2json:
            return False

        json_file_content = json.dumps(
            liz2json,
            sort_keys=False,
            indent=4
        )
        json_file_content += '\n'

        # Get the project data
        json_file = self.dlg.cfg_file()
        with open(json_file, 'w', encoding='utf8') as cfg_file:
            cfg_file.write(json_file_content)

        LOGGER.info(
            'The Lizmap configuration file has been written to <a href="file://{path}">"{path}"</a>'.format(
                path=json_file.absolute(),
            ))
        self.clean_project()
        return True

    def copy_versions_clicked(self):
        """ Copy all data in clipboard. """
        data = self.dlg.current_server_info(ServerComboData.MarkDown.value)
        data += '\n' + self.dlg.safeguards_to_markdown()
        data += '\n' + self.dlg.check_results.to_markdown_summarized()
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(data)
        self.dlg.display_message_bar(
            tr('Copied'), tr('Your versions have been copied in your clipboard.'), level=Qgis.Success)

    def check_project_clicked(self):
        """ Launch the check on the current project. """
        lwc_version = self.current_lwc_version()
        # Let's trigger UI refresh according to latest releases, if it wasn't available on startup
        self.lwc_version_changed()
        with OverrideCursor(Qt.WaitCursor):
            self.check_project(lwc_version)

    def check_project(
            self, lwc_version: LwcVersions, with_gui: bool = True, check_server=True, ignore_error=False
    ) -> bool:
        """ Check the project against all rules defined. """
        # Import must be done after QTranslator
        from lizmap.widgets.check_project import (
            Checks,
            Error,
            Severities,
            SourceLayer,
        )
        server_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        lizmap_cloud = is_lizmap_cloud(server_metadata)
        beginner_mode = QgsSettings().value(Settings.key(Settings.BeginnerMode), True, bool)
        severities = Severities()

        self.dlg.check_results.truncate()
        checks = Checks()

        # Fill the HTML table with all rules
        self.dlg.html_help.setHtml(
            checks.html(
                severity=severities.blocking if beginner_mode else severities.important,
                lizmap_cloud=lizmap_cloud
            )
        )

        validator = QgsProjectServerValidator()
        valid, results = validator.validate(self.project)
        LOGGER.info(f"Project has been detected : {'VALID' if valid else 'NOT valid'} according to OGC validation.")  # NOQA E203
        if not valid:
            self.dlg.check_results.add_error(
                Error(
                    Path(self.project.fileName()).name,
                    Checks().OgcValid,
                )
            )

        self.dlg.check_api_key_address()

        if with_gui:
            self.dlg.enable_all_fixer_buttons(False)

        duplicated_in_cfg = duplicated_layer_name_or_group(self.project)
        for name, count in duplicated_in_cfg.items():
            if count >= 2:
                source = '"{}" → "'.format(name) + tr("count {} layers").format(count)
                self.dlg.check_results.add_error(Error(source, checks.DuplicatedLayerNameOrGroup))

        # Layer ID as short name
        if lwc_version >= LwcVersions.Lizmap_3_6:
            use_layer_id, _ = self.project.readEntry('WMSUseLayerIDs', '/')
            if to_bool(use_layer_id, False):
                self.dlg.check_results.add_error(Error(Path(self.project.fileName()).name, checks.WmsUseLayerIds))

        if lwc_version >= LwcVersions.Lizmap_3_7 and with_gui:
            # To remove soon, after a few versions of LWC 3.7
            json_meta = self.dlg.current_server_info(ServerComboData.JsonMetadata.value)
            impacted_versions = ('3.7.0', '3.7.1', '3.7.2', '3.7.3')
            crs_inverted = self.project.crs().hasAxisInverted()
            is_not_4326 = self.project.crs() != QgsCoordinateReferenceSystem('4326')
            if json_meta and crs_inverted and is_not_4326 and json_meta['info']['version'] in impacted_versions:
                # https://github.com/3liz/lizmap-web-client/issues/4191
                self.dlg.check_results.add_error(Error(Path(self.project.fileName()).name, checks.CrsInvertedAxis))

            results = duplicated_rule_key_legend(self.project)
            if results:
                self.dlg.log_panel.append(tr("Duplicated rule key in the legend"), Html.H2)
                self.dlg.log_panel.append("<br>")
                self.dlg.log_panel.start_table()
                self.dlg.log_panel.append(
                    "<tr><th>{}</th><th>{}</th><th>{}</th></tr>".format(tr('Layer'), tr('Key'), tr('Count'))
                )

                i = 0
                for layer_id, rules in results.items():
                    layer = self.project.mapLayer(layer_id)
                    # Add one error per layer is enough
                    self.dlg.check_results.add_error(
                        Error(
                            layer.name(),
                            checks.DuplicatedRuleKeyLegend,
                            source_type=SourceLayer(layer.name(), layer.id()),
                        )
                    )

                    # But explain inside each layer which keys are duplicated
                    for rule, count in rules.items():
                        self.dlg.log_panel.add_row(i)
                        self.dlg.log_panel.append(layer.name(), Html.Td)
                        self.dlg.log_panel.append(rule, Html.Td)
                        self.dlg.log_panel.append(count, Html.Td)
                        self.dlg.log_panel.end_row()
                        i += 1

                self.dlg.log_panel.end_table()

            results = duplicated_label_legend(self.project)
            if results:
                self.dlg.log_panel.append(tr("Duplicated labels in the legend"), Html.H2)
                self.dlg.log_panel.append("<br>")
                self.dlg.log_panel.start_table()
                self.dlg.log_panel.append(
                    "<tr><th>{}</th><th>{}</th><th>{}</th></tr>".format(tr('Layer'), tr('Label'), tr('Count'))
                )

                i = 0
                for layer_id, rules in results.items():
                    layer = self.project.mapLayer(layer_id)
                    # Add one error per layer is enough
                    self.dlg.check_results.add_error(
                        Error(
                            layer.name(),
                            checks.DuplicatedRuleKeyLabelLegend,
                            source_type=SourceLayer(layer.name(), layer.id()),
                        )
                    )

                    # But explain inside each layer which keys are duplicated
                    for label, count in rules.items():
                        self.dlg.log_panel.add_row(i)
                        self.dlg.log_panel.append(layer.name(), Html.Td)
                        self.dlg.log_panel.append(label, Html.Td)
                        self.dlg.log_panel.append(count, Html.Td)
                        self.dlg.log_panel.end_row()
                        i += 1

                self.dlg.log_panel.end_table()

        if check_server:

            # Global safeguards in the QGIS profile
            prevent_ecw = QgsSettings().value(Settings.key(Settings.PreventEcw), True, bool)
            prevent_auth_id = QgsSettings().value(Settings.key(Settings.PreventPgAuthDb), True, bool)
            prevent_service = QgsSettings().value(Settings.key(Settings.PreventPgService), True, bool)
            force_pg_user_pass = QgsSettings().value(Settings.key(Settings.ForcePgUserPass), True, bool)
            prevent_other_drive = QgsSettings().value(Settings.key(Settings.PreventDrive), True, bool)
            allow_parent_folder = QgsSettings().value(Settings.key(Settings.AllowParentFolder), False, bool)
            count_parent_folder = QgsSettings().value(Settings.key(Settings.NumberParentFolder), 2, int)

            # Override safeguards by Lizmap Cloud
            lizmap_cloud = is_lizmap_cloud(server_metadata)
            if lizmap_cloud:
                prevent_ecw = True
                prevent_auth_id = True
                force_pg_user_pass = True
                prevent_other_drive = True
                if count_parent_folder > CLOUD_MAX_PARENT_FOLDER:
                    count_parent_folder = CLOUD_MAX_PARENT_FOLDER
                # prevent_service = False  We encourage service
                # allow_parent_folder = False Of course we can

            # Override safeguards by beginner mode
            if beginner_mode:
                prevent_ecw = True
                prevent_auth_id = True
                force_pg_user_pass = True
                prevent_other_drive = True
                count_parent_folder = 0
                prevent_service = True
                allow_parent_folder = False

            # List of safeguards are now defined
            summary = []
            if prevent_ecw:
                summary.append(PREVENT_ECW)
            if prevent_auth_id:
                summary.append(PREVENT_AUTH_DB)
            if prevent_service:
                summary.append(PREVENT_SERVICE)
            if force_pg_user_pass:
                summary.append(FORCE_PG_USER_PASS)
            if prevent_other_drive:
                summary.append(PREVENT_OTHER_DRIVE)
            if allow_parent_folder:
                summary.append(ALLOW_PARENT_FOLDER + " : " + tr("{} folder(s)").format(count_parent_folder))
            else:
                summary.append(FORCE_LOCAL_FOLDER)

            parent_folder = relative_path(count_parent_folder)

            results = project_safeguards_checks(
                self.project,
                prevent_ecw=prevent_ecw,
                prevent_auth_id=prevent_auth_id,
                prevent_service=prevent_service,
                force_pg_user_pass=force_pg_user_pass,
                prevent_other_drive=prevent_other_drive,
                allow_parent_folder=allow_parent_folder,
                parent_folder=parent_folder,
                lizmap_cloud=lizmap_cloud,
            )
            # Let's show a summary
            self.dlg.log_panel.append(tr("Safeguards"), Html.H2)
            if lizmap_cloud:
                self.dlg.log_panel.append(
                    tr("According to global settings, overridden then by {} :").format(CLOUD_NAME), Html.P)
            else:
                self.dlg.log_panel.append(tr("According to global settings"), Html.P)

            self.dlg.log_panel.start_table()
            for i, rule in enumerate(summary):
                self.dlg.log_panel.add_row(i)
                self.dlg.log_panel.append(rule, Html.Td)
                self.dlg.log_panel.end_row()
            self.dlg.log_panel.end_table()

            self.dlg.log_panel.append("<br>")

            # Severity depends on beginner mode
            severity = severities.blocking if beginner_mode else severities.important
            # But override severities for Lizmap Cloud
            # Because even with a 'normal' user, it won't work
            override = (
                checks.PreventEcw.data,
                checks.PgForceUserPass.data,
                checks.AuthenticationDb.data,
                checks.PreventDrive.data,
            )

            for layer, error in results.items():
                error: Check

                if error.data in override:
                    severity = severities.blocking

                self.dlg.check_results.add_error(
                    Error(
                        layer.name,
                        error,
                        source_type=SourceLayer(layer.name, layer.layer_id),
                    ),
                    lizmap_cloud=lizmap_cloud,
                    severity=severity,
                )

            if results:
                if beginner_mode:
                    self.dlg.log_panel.append(tr(
                        "The process is stopping, the Lizmap configuration file is not going to be generated because "
                        "some safeguards are not compatible and you are using the 'Beginner' mode. Either fix these "
                        "issues or switch to a 'Normal' mode if you know what you are doing."
                    ), Html.P, level=Qgis.Critical)
                else:
                    self.dlg.log_panel.append(tr(
                        "The process is continuing but these layers might be invisible if the server is not well "
                        "configured or if the project is not correctly uploaded to the server."
                    ), Html.P)

        if check_server:

            if lizmap_cloud:
                error, message = check_project_ssl_postgis(self.project)
                for layer in error:
                    self.dlg.check_results.add_error(
                        Error(
                            layer.name,
                            checks.SSLConnection,
                            source_type=SourceLayer(layer.name, layer.layer_id),
                        )
                    )
                    self.dlg.enabled_ssl_button(True)

            autogenerated_keys, int8, varchar = project_invalid_pk(self.project)
            for layer in autogenerated_keys:
                self.dlg.check_results.add_error(
                    Error(
                        layer.name,
                        checks.MissingPk,
                        source_type=SourceLayer(layer.name, layer.layer_id),
                    )
                )
            for layer in int8:
                self.dlg.check_results.add_error(
                    Error(
                        layer.name,
                        checks.PkInt8,
                        source_type=SourceLayer(layer.name, layer.layer_id),
                    )
                )
            for layer in varchar:
                self.dlg.check_results.add_error(
                    Error(
                        layer.name,
                        checks.PkVarchar,
                        source_type=SourceLayer(layer.name, layer.layer_id),
                    )
                )

            results = trailing_layer_group_name(self.project.layerTreeRoot(), self.project, [])
            for result in results:
                self.dlg.check_results.add_error(result)

            # TOS checks from the server
            # These checks are only done if we find the server configuration below, starting with version 2.9.4
            tos_checks = server_metadata.get("qgis_server_info").get("external_providers_tos_checks")
            if tos_checks is not None:
                # Server configuration, if set to True, it means an API key is required, the default behavior
                google = tos_checks.get('google', False)
                bing = tos_checks.get('bing', False)

                # If an API key is provided, we do not report these layers
                if self.dlg.inGoogleKey.text() != '':
                    google = False

                if self.dlg.inBingKey.text() != '':
                    bing = False

                if google or bing:
                    for layer in project_tos_layers(self.project, google, bing):
                        self.dlg.check_results.add_error(
                            Error(
                                layer.name,
                                checks.LayerMissingApiKey,
                                source_type=SourceLayer(layer.name, layer.layer_id),
                            ),
                            lizmap_cloud=lizmap_cloud,
                        )

            if lwc_version >= LwcVersions.Lizmap_3_7:
                results = duplicated_layer_with_filter_legend(self.project)
                if results:
                    self.dlg.log_panel.append(checks.DuplicatedLayerFilterLegend.title, Html.H2)
                    self.dlg.log_panel.start_table()
                    self.dlg.log_panel.append(
                        "<tr><th>{}</th><th>{}</th><th>{}</th></tr>".format(
                            tr('Datasource'), tr('Filters'), tr('Layers'))
                    )
                    for i, result in enumerate(results):
                        for uri, filters in result.items():
                            self.dlg.log_panel.add_row(i)
                            self.dlg.log_panel.append(uri, Html.Td)

                            # Icon
                            for k, v in filters.items():
                                if k == "_wkb_type" and Qgis.QGIS_VERSION_INT >= 32000:
                                    icon = QgsIconUtils.iconForWkbType(v)
                                    break
                            else:
                                icon = QIcon(':/images/themes/default/algorithms/mAlgorithmMergeLayers.svg')

                            del filters["_wkb_type"]

                            uri_filter = '<ul>' + ''.join([f"<li>{k}</li>" for k in filters.keys()]) + '</ul>'
                            self.dlg.log_panel.append(uri_filter, Html.Td)

                            layer_names = '<ul>' + ''.join([f"<li>{k}</li>" for k in filters.values()]) + '</ul>'
                            self.dlg.log_panel.append(layer_names, Html.Td)

                            self.dlg.log_panel.end_row()

                            self.dlg.check_results.add_error(
                                Error(
                                    uri,
                                    checks.DuplicatedLayerFilterLegend,
                                ),
                                icon=icon,
                            )

                    self.dlg.log_panel.end_table()

                    self.dlg.log_panel.append(tr(
                        'Checkboxes are supported natively in the legend. Using filters for the same '
                        'datasource are highly discouraged.'
                    ), style=Html.P)

        results = simplify_provider_side(self.project)
        for layer in results:
            self.dlg.check_results.add_error(
                Error(
                    layer.name,
                    checks.SimplifyGeometry,
                    source_type=SourceLayer(layer.name, layer.layer_id),
                )
            )
            self.dlg.enabled_simplify_geom(True)

        data = {}
        for key in self.layers_table.keys():
            manager: TableManager = self.layers_table[key].get('manager')
            if manager:
                for layer_id, fields in manager.wfs_fields_used().items():
                    if layer_id not in data.keys():
                        data[layer_id] = []
                    for f in fields:
                        if f not in data[layer_id]:
                            data[layer_id].append(f)

        for layer_id, fields in data.items():
            layer = self.project.mapLayer(layer_id)
            if not layer:
                # Fixme, the layer has been removed from QGIS Desktop, but was still in the CFG file.
                # :func:clean_project()
                continue

            if not is_layer_published_wfs(self.project, layer.id()):
                self.dlg.check_results.add_error(
                    Error(
                        layer.name(),
                        checks.MissingWfsLayer,
                        source_type=SourceLayer(layer.name(), layer.id()),
                    )
                )

            for field in fields:
                if field in layer.excludeAttributesWfs():
                    self.dlg.check_results.add_error(
                        Error(
                            field,
                            checks.MissingWfsField,
                            source_type=SourceField(field, layer.id()),
                        )
                    )

        results = use_estimated_metadata(self.project)
        for layer in results:
            self.dlg.check_results.add_error(
                Error(
                    layer.name,
                    checks.EstimatedMetadata,
                    source_type=SourceLayer(layer.name, layer.layer_id),
                )
            )
            self.dlg.enabled_estimated_md_button(True)

        if not project_trust_layer_metadata(self.project):
            self.dlg.check_results.add_error(Error(Path(self.project.fileName()).name, checks.TrustProject))
            self.dlg.enabled_trust_project(True)

        if empty_baselayers(self.project):
            self.dlg.check_results.add_error(
                Error(Path(self.project.fileName()).name, checks.EmptyBaseLayersGroup)
            )

        if self.dlg.check_qgis_version(message_bar=True):
            self.dlg.check_results.add_error(Error(tr('Global'), checks.ServerVersion))

        if server_metadata:
            min_required_version = server_metadata.get('lizmap_desktop_plugin_version')
            if min_required_version:
                current_version = version()
                if current_version in DEV_VERSION_PREFIX:
                    current_version = next_git_tag()
                min_required_version = format_qgis_version(min_required_version, increase_odd_number=False)
                min_required_version = '.'.join([str(i) for i in min_required_version])
                if compareVersions(current_version, min_required_version) == 2:
                    self.dlg.check_results.add_error(Error(tr('Global'), checks.PluginDesktopVersion))

        # Not blocking, we change it in the background
        if self.project.readNumEntry("WMSMaxAtlasFeatures", '')[0] <= 0:
            LOGGER.info("The maximum atlas features was less than '1'. We set it to '1' to at least have a value.")
            self.project.writeEntry("WMSMaxAtlasFeatures", "/", 1)

        self.dlg.check_results.sort()

        if with_gui and self.dlg.check_results.has_rows():
            self.dlg.mOptionsListWidget.setCurrentRow(Panels.Checks)
            self.dlg.tab_log.setCurrentIndex(0)
            self.dlg.out_log.moveCursor(QTextCursor.Start)
            self.dlg.out_log.ensureCursorVisible()

        beginner_mode = QgsSettings().value(Settings.key(Settings.BeginnerMode), True, bool)
        mode = tr('beginner') if beginner_mode else tr('normal')
        if self.dlg.check_results.has_blocking():
            msg = tr(
                'You are using the "{mode}" mode and you have some <strong>blocking</strong> checks.').format(mode=mode)
        else:
            msg = tr('You are using the "{mode}" mode.').format(mode=mode)
        self.dlg.label_check_resume.setText(msg)

        self.dlg.auto_fix_tooltip(lizmap_cloud)
        self.dlg.label_autofix.setVisible(self.dlg.has_auto_fix())
        self.dlg.push_visit_settings.setVisible(self.dlg.has_auto_fix())

        if self.dlg.check_results.has_blocking() and not ignore_error:
            self.dlg.display_message_bar(
                tr("Blocking issue"),
                tr("The project has at least one blocking issue. The file is not saved."),
                Qgis.Critical,
            )

            return False

        return True

    def project_config_file(
            self, lwc_version: LwcVersions, with_gui: bool = True, check_server=True, ignore_error=False
    ) -> Optional[Dict]:
        """ Get the JSON CFG content. """

        if lwc_version >= LwcVersions.Lizmap_3_6:
            LOGGER.info(
                'Lizmap Web Client target version {}, let\'s try to make the project valid.'.format(
                    lwc_version.value)
            )
            # Set shortnames if it's not set
            ogc_projet_validity = OgcProjectValidity(self.project)
            ogc_projet_validity.add_shortnames()
            ogc_projet_validity.set_project_short_name()

            validator = QgsProjectServerValidator()
            valid, results = validator.validate(self.project)
            LOGGER.info(f"Project has been detected : {'VALID' if valid else 'NOT valid'} according to OGC validation.")  # NOQA E203
        else:
            LOGGER.info(
                "Lizmap Web Client target version {}, we do not update the project for OGC validity.".format(
                    lwc_version.value)
            )

        if not self.check_project(lwc_version, with_gui, check_server, ignore_error):
            # Some blocking issues, we can not continue
            return None

        server_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)

        LOGGER.info("Writing Lizmap configuration file for LWC version {}".format(lwc_version.value))
        current_version = self.global_options['metadata']['lizmap_plugin_version']['default']
        if self.is_dev_version:
            next_version = next_git_tag()
            if next_version != 'next':
                current_version = next_version

        target_status = self.dlg.server_combo.currentData(ServerComboData.LwcBranchStatus.value)
        if not target_status:
            target_status = ReleaseStatus.Unknown

        if is_lizmap_cloud(server_metadata):
            if self.dlg.current_server_info(ServerComboData.LwcBranchStatus.value) == ReleaseStatus.Retired:
                QMessageBox.warning(
                    self.dlg,
                    CLOUD_NAME,
                    tr(
                        'You current server <a href="{server_url}">{server_url}</a> is running '
                        'Lizmap Web Client version {lwc_version}.'
                    ).format(
                        server_url=self.dlg.current_server_info(ServerComboData.ServerUrl.value),
                        lwc_version=lwc_version.value,
                    )
                    + "<br><br>"
                    + tr(
                        'This version of Lizmap Web Client has now reached its end of life and is not supported '
                        'anymore. Please visit your administration panel in your web browser, in the dashboard, and '
                        'ask for the update.'
                    )
                    + "<br><br>"
                    + tr(
                        'You might have some old project which need an update from you. The list is written on the '
                        'dashboard. Projects are not deleted during the update of Lizmap Web Client, '
                        'they will be only invisible on the main landing page until they are updated by you.'
                    )
                    + "<br><br>"
                    + tr('This is not blocking your current usage of the plugin, only to advise you.'),
                    QMessageBox.Ok
                )

            qgis_server_info = server_metadata.get('qgis_server_info')
            md = qgis_server_info.get('metadata')
            qgis_server_version = tuple([int(i) for i in md.get('version').split('.')])
            if qgis_server_version < CLOUD_QGIS_MIN_RECOMMENDED:
                QMessageBox.warning(
                    self.dlg,
                    CLOUD_NAME,
                    tr(
                        'You current server <a href="{server_url}">{server_url}</a> is running '
                        'QGIS Server {version}.'
                    ).format(
                        server_url=self.dlg.current_server_info(ServerComboData.ServerUrl.value),
                        version=md.get('version'),
                    )
                    + "<br><br>"
                    + tr(
                        'This version of QGIS Server has now reached its end of life and is not supported '
                        'anymore by QGIS.org since February 2023, see the '
                        '<a href="https://www.qgis.org/en/site/getinvolved/development/roadmap.html#release-schedule">'
                        'QGIS roadmap'
                        '</a>.'
                    )
                    + "<br><br>"
                    + tr(
                        'Please visit your administration panel in your web browser, in the dashboard, and '
                        'ask for the update.'
                    )
                    + "<br><br>"
                    + tr('This is not blocking your current usage of the plugin, only to advise you.'),
                    QMessageBox.Ok
                )

        metadata = {
            'qgis_desktop_version': qgis_version(),
            'lizmap_plugin_version_str': current_version,
            'lizmap_plugin_version': int(format_version_integer(current_version)),
            'lizmap_web_client_target_version': int(format_version_integer('{}.0'.format(lwc_version.value))),
            'lizmap_web_client_target_status': target_status.value,
            'instance_target_url': self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        }
        repository = self.dlg.current_repository()
        if repository:
            metadata['instance_target_repository'] = repository

        profiler = QgsApplication.profiler()
        # We need to compute ourselves the total, QgsRuntimeProfiler::totalTime always returns 0
        time_total = 0
        group = 'projectload'
        for child in profiler.childGroups('', group):
            value = profiler.profileTime(child, group)
            time_total += value

        liz2json = dict()
        liz2json['metadata'] = metadata
        liz2json['warnings'] = self.dlg.check_results.to_json_summarized()
        liz2json['debug'] = {
            'total_time': time_total,
        }
        liz2json["options"] = dict()
        liz2json["layers"] = dict()

        # projection
        projection = self.dlg.widget_initial_extent.outputCrs()
        liz2json['options']['projection'] = dict()
        liz2json['options']['projection']['proj4'] = projection.toProj()
        liz2json['options']['projection']['ref'] = projection.authid()

        # WMS extent from project properties, QGIS server tab
        liz2json['options']['bbox'] = self.project.readListEntry('WMSExtent', '')[0]

        # set initialExtent values if not defined
        if self.dlg.widget_initial_extent.outputExtent().isNull():
            self.set_initial_extent_from_project()

        # gui user defined options
        for key, item in self.global_options.items():
            if item.get('widget'):
                input_value = None
                # Get field value depending on widget type
                if item['wType'] == 'text':
                    input_value = item['widget'].text().strip(' \t')

                if item['wType'] == 'wysiwyg':
                    input_value = item['widget'].html_content().strip(' \t')

                if item['wType'] == 'textarea':
                    input_value = item['widget'].toPlainText().strip(' \t')

                if item['wType'] == 'spinbox':
                    input_value = item['widget'].value()

                if item['wType'] == 'checkbox':
                    input_value = str(item['widget'].isChecked())

                if item['wType'] == 'list':
                    input_value = item['widget'].currentData()

                if item['wType'] == 'layers':
                    lay = item['widget'].layer(item['widget'].currentIndex())
                    input_value = lay.id()

                if item['wType'] == 'fields':
                    input_value = item['widget'].currentField()

                if item['wType'] == 'extent':
                    input_value = item['widget'].outputExtent()

                # Cast value depending of data type
                if item['type'] == 'string':
                    if item['wType'] in ('text', 'textarea'):
                        input_value = str(input_value)
                    else:
                        input_value = str(input_value)

                elif item['type'] in ('intlist', 'floatlist', 'list'):
                    if item['type'] == 'intlist':
                        input_value = [int(a) for a in input_value.split(', ') if a.isdigit()]
                    elif item['type'] == 'floatlist':
                        if item['wType'] != 'extent':
                            input_value = [float(a) for a in input_value.split(', ')]
                        else:
                            input_value = [
                                input_value.xMinimum(),
                                input_value.yMinimum(),
                                input_value.xMaximum(),
                                input_value.yMaximum(),
                            ]
                    else:
                        input_value = [a.strip() for a in input_value.split(',') if a.strip()]

                elif item['type'] == 'integer':
                    # noinspection PyBroadException
                    try:
                        input_value = int(input_value)
                    except Exception:
                        input_value = int(item['default'])

                elif item['type'] == 'boolean':
                    input_value = item['widget'].isChecked()
                    if not item.get('use_proper_boolean'):
                        input_value = str(input_value)

                # Add value to the option
                if item['type'] == 'boolean':
                    if not to_bool(input_value):
                        if not item.get('always_export'):
                            continue

                if item['type'] in ('list', 'string'):
                    if not input_value:
                        # Empty list or string
                        if not item.get('always_export'):
                            continue

                liz2json["options"][key] = input_value

            # Since LWC 3.7, we are managing manually these values
            if key == 'mapScales':
                liz2json["options"]['mapScales'] = self.map_scales()
            if key == 'minScale':
                liz2json["options"]['minScale'] = self.minimum_scale_value()
            if key == 'maxScale':
                liz2json["options"]['maxScale'] = self.maximum_scale_value()
            if key == 'use_native_zoom_levels':
                liz2json["options"]['use_native_zoom_levels'] = self.dlg.use_native_scales.isChecked()
            if key == 'automatic_permalink':
                liz2json["options"]['automatic_permalink'] = self.dlg.automatic_permalink.isChecked()

        for key in self.layers_table.keys():
            manager = self.layers_table[key].get('manager')
            if manager:
                try:
                    data = manager.to_json()
                except (AttributeError, ) as e:
                    import traceback
                    panel_name = self.dlg.mOptionsListWidget.item(self.layers_table[key].get('panel', key)).text()
                    QMessageBox.critical(
                        self.dlg,
                        'Lizmap',
                        tr(
                            'An error has been raised while saving table "<strong>{name}</strong>", maybe it was due '
                            'to invalid layers ?'
                        ).format(name=panel_name) + '\n\n'
                        + tr(
                            'If yes, saving the Lizmap configuration file with invalid layers in the legend is not '
                            'currently supported by the plugin.'
                        ) + '\n\n'
                        + tr(
                            'Please visit the corresponding tab "<strong>{name}</strong>" and check if you have a '
                            'warning in one of the column.'
                        ).format(name=panel_name) + '\n\n'
                        + tr(
                            'If not, it was a bug, please report it. The process is stopping.'
                        ) + '\n\n'
                        + tr('Error') + ' : ' + str(e) + '\n\n'
                        + traceback.format_exc()
                    )
                    return None

                if key == 'layouts':
                    # The print combobox is removed
                    # Let's remove from the CFG file
                    if lwc_version >= LwcVersions.Lizmap_3_7:
                        try:
                            del liz2json['options']['print']
                        except KeyError:
                            pass
                    else:
                        # We do not want to save this table if it's less than LWC 3.7
                        LOGGER.info("Skipping the 'layout' table because version is less than LWC 3.7")
                        continue

                if manager.use_single_row() and manager.table.rowCount() == 1:
                    liz2json['options'].update(data)
                else:
                    liz2json[key] = data

        # Drag drop dataviz designer
        if self.drag_drop_dataviz:
            # In tests, we don't have the variable set
            liz2json['options']['dataviz_drag_drop'] = self.drag_drop_dataviz.to_json()

        default_background_color_index = self.existing_group(
            self.existing_group(
                self.project.layerTreeRoot(), GroupNames.BaseLayers), GroupNames.BackgroundColor, index=True)
        if default_background_color_index is not None and default_background_color_index >= 0:
            liz2json["options"]["default_background_color_index"] = default_background_color_index

        if not isinstance(self.layerList, dict):
            # Wierd bug when the dialog was not having a server at the beginning
            # The navigation in the menu was not allowed
            # The user added a server → navigation allowed
            # But the project has not been loaded in the plugin
            # The layer tree is empty
            QMessageBox.warning(
                self.dlg,
                'Lizmap',
                tr(
                    '"Apply" or "OK" are not supported right now. Please close the dialog et reopen the plugin.'
                    'You will be able to save the Lizmap configuration file after.'
                ) + '\n\n'
                + tr('Sorry for the inconvenience.')
            )
            return None

        # gui user defined layers options
        for k, v in self.layerList.items():
            layer = False
            if v['groupAsLayer']:
                layer_type = 'layer'
            else:
                layer_type = 'group'

            if self.get_qgis_layer_by_id(k):
                layer_type = 'layer'

            # ~ # add layerOption only for geo layers
            # ~ if geometryType != 4:
            layer_options = dict()
            layer_options["id"] = str(k)
            layer_options["name"] = str(v['name'])
            layer_options["type"] = layer_type

            geometry_type = -1
            if layer_type == 'layer':
                layer = self.get_qgis_layer_by_id(k)
                if layer and layer.type() == QgsMapLayer.VectorLayer:  # if it is a vector layer:
                    geometry_type = layer.geometryType()

            # geometry type
            if geometry_type != -1:
                layer_options["geometryType"] = self.mapQgisGeometryType[layer.geometryType()]

            # extent
            if layer:
                extent = layer.extent()
                if extent.isNull() or extent.isEmpty():
                    LOGGER.info(f"Layer '{layer.name()}' has null or empty extent.")
                layer_options['extent'] = [
                    extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()]
                if any(x != x for x in layer_options['extent']):
                    if layer.isSpatial():
                        # https://github.com/3liz/lizmap-plugin/issues/571
                        if 33600 <= Qgis.QGIS_VERSION_INT < 33603:
                            msg = tr('A bug has been identified with QGIS 3.36.0 to 3.36.2 included, please change.')
                        else:
                            msg = ""
                        QMessageBox.warning(
                            self.dlg,
                            'Lizmap',
                            msg
                            + tr(
                                'Please check your layer extent for "{}" with the ID "{}".'
                                'The extent does not seem valid.'
                            ).format(layer.name(), layer.id()) + '\n\n'
                            + tr(
                                'You can visit vector layer properties → Information tab → Information from provider → '
                                'Extent.'
                            ) + '\n\n'
                            + tr(
                                'Then in the "Source" tab, you can recompute the extent or check your logs in QGIS.'
                            ) + '\n\n'
                            + tr(
                                'The extent has been set to a default value 0,0,0,0.'
                            )
                        )
                    layer_options['extent'] = [0, 0, 0, 0]
                layer_options['crs'] = layer.crs().authid()

            # styles
            if isinstance(layer, QgsMapLayer):
                ls = layer.styleManager().styles()
                if len(ls) > 1:
                    layer_options['styles'] = ls

            # Loop through the layer options and set properties from the dictionary
            for key, val in self.layer_options_list.items():
                property_value = v[key]
                if val['type'] == 'string':
                    if val['wType'] in ('text', 'textarea'):
                        property_value = str(property_value)
                    elif val['wType'] == 'list' and isinstance(property_value, tuple):
                        # Process later, do not cast for now
                        pass
                    else:
                        property_value = str(property_value)
                elif val['type'] == 'integer':
                    # noinspection PyBroadException
                    try:
                        property_value = int(property_value)
                    except Exception:
                        property_value = 1
                elif val['type'] == 'boolean':
                    if not val.get('use_proper_boolean'):
                        property_value = str(property_value)

                if key == 'link':
                    # TODO check media or ../media
                    pass

                if key in ('legend_image_option', 'noLegendImage'):
                    if layer_options.get('legend_image_option') and key == 'noLegendImage':
                        # Let's skip, the key is already saved
                        continue

                    if layer_options.get('noLegendImage') and key == 'legend_image_option':
                        # Let's skip, the key is already saved
                        continue

                    max_version = val.get('max_version')
                    if max_version and lwc_version > max_version:
                        # LOGGER.info("Skipping key '{}' because of max_version.".format(key))
                        continue

                    min_version = val.get('min_version')
                    if min_version and lwc_version < min_version:
                        # LOGGER.info("Skipping key '{}' because of min_version.".format(key))
                        continue

                    if key == 'noLegendImage':
                        # We take the value of legend_image_option
                        property_value = str(False)
                        if v['legend_image_option'] == 'disabled':
                            property_value = str(True)
                        if v['legend_image_option'] == 'expand_at_startup' and with_gui:
                            # We keep False
                            QMessageBox.warning(
                                self.dlg,
                                tr('Legend image'),
                                tr(
                                    'Be careful, the option "Expand at startup" for the layer "{layer_name}" is not '
                                    'available for your Lizmap Web Client target version {target}.'
                                ).format(layer_name=k, target=lwc_version.value)
                                + '\n\n'
                                + tr('Falling back to "Hide at startup" in the configuration file.')
                                + '\n\n'
                                + tr('This option is only available for Lizmap Web Client 3.6 and above.')
                            )

                    if isinstance(property_value, tuple):
                        property_value = property_value[0]

                    # LOGGER.info("Saving {} = {} for layer {}".format(key, property_value, k))

                layer_options[key] = property_value

            # Cache Metatile: unset metatileSize if empty
            # this is to avoid, but LWC must change accordingly to avoid using empty metatileSize
            # (2.2.0 does not handle it)

            # unset metatileSize
            meta_tile_size = layer_options.get('metatileSize')
            if meta_tile_size is not None and isinstance(meta_tile_size, str) and not re.match(r'\d,\d', meta_tile_size):
                del layer_options['metatileSize']

            # unset cacheExpiration if False
            cached = layer_options.get('cached')
            if cached and not to_bool(cached):
                del layer_options['cacheExpiration']

            # unset clientCacheExpiration if not needed
            client_cache = layer_options.get('clientCacheExpiration')
            if client_cache and client_cache < 0:
                del layer_options['clientCacheExpiration']

            # unset externalWms if False
            external_wms = layer_options.get('externalWmsToggle')
            if external_wms and not to_bool(external_wms):
                del layer_options['externalWmsToggle']

            # unset source project and repository if needed
            source_repository = layer_options.get('sourceRepository')
            source_project = layer_options.get('sourceProject')
            if not source_repository or not source_project:
                del layer_options['sourceRepository']
                del layer_options['sourceProject']

            # set popupSource to auto if set to lizmap and no lizmap conf found
            if to_bool(layer_options['popup']) and layer_options['popupSource'] == 'lizmap' \
                    and layer_options['popupTemplate'] == '':
                layer_options['popupSource'] = 'auto'

            if layer_options.get("geometryType") in ('point', 'line', 'polygon'):
                if layer_options.get('popupSource') == 'lizmap' and to_bool(layer_options.get('popup')):
                    QMessageBox.warning(
                        self.dlg,
                        tr('Deprecated feature'),
                        tr(
                            'The layer "{}" is vector layer and the popup is a "Lizmap HTML". This kind of popup is '
                            'deprecated for vector layer, you should switch to another kind of popup, for instance to '
                            'a "QGIS HTML maptip". This will be removed in a future version of Lizmap.'
                        ).format(layer_options["name"]),
                        QMessageBox.Ok
                    )

            # Add external WMS options if needed
            if isinstance(layer, QgsMapLayer) and to_bool(layer_options.get('externalWmsToggle', False)):
                # Only for layers stored in disk
                if layer.providerType() == 'wms':
                    wms_params = get_layer_wms_parameters(layer)
                    if wms_params:
                        layer_options['externalAccess'] = wms_params
                    else:
                        layer_options['externalWmsToggle'] = str(False)
                else:
                    layer_options['externalWmsToggle'] = str(False)

            if 'serverFrame' in layer_options.keys():
                del layer_options['serverFrame']

            if 'popupFrame' in layer_options.keys():
                del layer_options['popupFrame']

            # Add layer options to the json object
            liz2json["layers"][v['name']] = layer_options

        return liz2json

    def map_scales(self) -> list:
        """ Whe writing CFG file, return the list of map scales. """
        use_native = self.dlg.use_native_scales.isChecked()
        if use_native:
            return [self.dlg.minimum_scale.value(), self.dlg.maximum_scale.value()]
        else:
            return [int(a) for a in self.dlg.list_map_scales.text().split(', ') if a.isdigit()]

    def minimum_scale_value(self) -> int:
        """ Return the minimum scale value. """
        value = self.dlg.minimum_scale.text()
        if not value:
            value = self.global_options['minScale']['default']
        return int(value)

    def maximum_scale_value(self) -> int:
        """ Return the maximum scale value. """
        value = self.dlg.maximum_scale.text()
        if not value:
            value = self.global_options['maxScale']['default']
        return int(value)

    def set_map_scales_in_ui(
            self, map_scales: list, min_scale: int, max_scale: int, use_native: bool, project_crs: str):
        """ From CFG or default values into the user interface. """
        scales_widget = (
            self.dlg.minimum_scale,
            self.dlg.maximum_scale,
        )
        max_value = 2000000000

        if max_scale > max_value:
            # Avoid an OverflowError Python error
            max_scale = max_value

        for widget in scales_widget:
            widget.setMinimum(1)
            widget.setMaximum(max_value)
            widget.setSingleStep(5000)

        map_scales = [str(i) for i in map_scales]

        self.dlg.use_native_scales.toggled.connect(self.native_scales_toggled)

        if self.current_lwc_version() <= LwcVersions.Lizmap_3_6:
            # From CFG and default, scales are int, we need text
            self.dlg.list_map_scales.setText(', '.join(map_scales))
            self.dlg.minimum_scale.setValue(min_scale)
            self.dlg.maximum_scale.setValue(max_scale)
            self.connect_map_scales_min_max()
            self.dlg.use_native_scales.setChecked(False)
            return

        # We are now in LWC 3.7
        if use_native is None:
            # but coming from a 3.6 CFG file
            crs = QgsCoordinateReferenceSystem(project_crs)
            if crs in (QgsCoordinateReferenceSystem('EPSG:3857'), QgsCoordinateReferenceSystem('EPSG:900913')):
                use_native = True
            else:
                use_native = False

            # We set the scale bar only if it wasn't set
            self.dlg.hide_scale_value.setChecked(use_native)

        # CFG file from 3.7
        self.dlg.use_native_scales.setChecked(use_native)
        self.dlg.list_map_scales.setText(', '.join(map_scales))
        self.dlg.minimum_scale.setValue(min_scale)
        self.dlg.maximum_scale.setValue(max_scale)
        self.disconnect_map_scales_min_max()

    def connect_map_scales_min_max(self):
        """ Connect the list of scales to min/max fields. """
        self.dlg.list_map_scales.editingFinished.connect(self.get_min_max_scales)

    def disconnect_map_scales_min_max(self):
        """ Disconnect the list of scales to min/max fields. """
        try:
            self.dlg.list_map_scales.editingFinished.disconnect(self.get_min_max_scales)
        except TypeError:
            # It wasn't connected
            pass

    def native_scales_toggled(self):
        """ When the checkbox native scales is toggled. """
        use_native = self.dlg.use_native_scales.isChecked()

        if self.current_lwc_version() <= LwcVersions.Lizmap_3_6:
            use_native = False
            self.dlg.use_native_scales.setChecked(use_native)

        self.dlg.minimum_scale.setReadOnly(not use_native)
        self.dlg.maximum_scale.setReadOnly(not use_native)
        # The list of map scales is used for printing as well, this must be checked
        # self.dlg.list_map_scales.setVisible(not use_native)
        # self.dlg.button_reset_scales.setVisible(not use_native)
        # self.dlg.label_scales.setVisible(not use_native)

        if use_native:
            msg = tr("When using native scales, you can set minimum and maximum scales.")
        else:
            msg = tr("The minimum and maximum scales are defined by your minimum and maximum values in the list.")
        ui_items = (
            self.dlg.list_map_scales,
            self.dlg.label_min_scale,
            self.dlg.label_max_scale,
            self.dlg.min_scale_pic,
            self.dlg.max_scale_pic,
            self.dlg.minimum_scale,
            self.dlg.maximum_scale,
            self.dlg.label_scales,
        )
        for item in ui_items:
            item.setToolTip(msg)

        if use_native:
            self.disconnect_map_scales_min_max()
        else:
            self.connect_map_scales_min_max()

    def clean_project(self):
        """Clean a little the QGIS project.

        Mainly ghost layers for now.
        """
        layers = remove_all_ghost_layers()
        if layers:
            message = tr(
                'Lizmap has found these layers which are ghost layers: {}. '
                'They have been removed. You must save your project.').format(', '.join(layers))
            # noinspection PyUnresolvedReferences
            self.iface.messageBar().pushMessage('Lizmap', message, level=Qgis.Warning, duration=DURATION_WARNING_BAR)

    def check_global_project_options(self) -> Tuple[bool, str]:
        """Checks that the needed options are correctly set : relative path, project saved, etc.

        :return: Flag if the project is valid and an error message.
        :rtype: bool, basestring
        """
        base_message = "<br>" + tr("This is needed before using other tabs in the plugin.")
        message = tr('You need to open a QGIS project, using the QGS extension.')
        if not self.project.fileName():
            return False, message + base_message

        if not self.project.fileName().lower().endswith('qgs'):
            message += "\n\n" + tr(
                "Your extension is QGZ. Please save again the project using the other extension.")
            return False, message + base_message

        if self.project.baseName() != unaccent(self.project.baseName()):
            message = tr(
                "Your file name has some accents in its name. The project file name mustn't have accents in its name.")
            return False, message + base_message

        message = tr(
            "You mustn't open the QGS file located in your local webdav directory. Please open a local copy of the "
            "project.")
        # Windows
        network_dav = []
        for i in QStorageInfo.mountedVolumes():
            # Mapping table between 'Z:/' and
            # \\demo.snap.lizmap.com@SSL\DavWWWRoot\lizmap_3_6\dav.php\
            if 'dav.php' in i.device().data().decode():
                network_dav.append(i.rootPath())
        if self.project.fileName().startswith(tuple(network_dav)):
            return False, message + base_message

        # Linux : /run/user/1000/gvfs/dav:host=...,ssl=true,....,prefix=%2Flizmap_3_6%2Fdav.php/...tests_projects/..qgs
        if 'dav.php' in self.project.fileName():
            return False, message + base_message

        # Check if Qgis/capitaliseLayerName is set
        settings = QgsSettings()
        if settings.value('Qgis/capitaliseLayerName') and settings.value('Qgis/capitaliseLayerName', type=bool):
            message = tr(
                'Please deactivate the option "Capitalize layer names" in the tab "Canvas and legend" '
                'in the QGIS option dialog, as it could cause issues with Lizmap.')
            return False, message + base_message

        # Check relative/absolute path
        if to_bool(self.project.readEntry('Paths', 'Absolute')[0]):
            message = tr(
                'The project layer paths must be set to relative. '
                'Please change this options in the project settings.')
            return False, message + base_message

        # check if a title has been given in the project QGIS Server tab configuration
        # first set the WMSServiceCapabilities to true
        if not self.project.readEntry('WMSServiceCapabilities', '/')[1]:
            self.project.writeEntry('WMSServiceCapabilities', '/', str(True))
        if self.project.readEntry('WMSServiceTitle', '')[0] == '':
            self.project.writeEntry('WMSServiceTitle', '', self.project.baseName())

        # check if a bbox has been given in the project QGIS Server tab configuration
        project_wms_extent, _ = self.project.readListEntry('WMSExtent', '')
        full_extent = self.iface.mapCanvas().extent()
        if not project_wms_extent:
            project_wms_extent.append(str(full_extent.xMinimum()))
            project_wms_extent.append(str(full_extent.yMinimum()))
            project_wms_extent.append(str(full_extent.xMaximum()))
            project_wms_extent.append(str(full_extent.yMaximum()))
            self.project.writeEntry('WMSExtent', '', project_wms_extent)
        else:
            if not project_wms_extent[0] or not project_wms_extent[1] or not \
                    project_wms_extent[2] or not project_wms_extent[3]:
                project_wms_extent[0] = str(full_extent.xMinimum())
                project_wms_extent[1] = str(full_extent.yMinimum())
                project_wms_extent[2] = str(full_extent.xMaximum())
                project_wms_extent[3] = str(full_extent.yMaximum())
                self.project.writeEntry('WMSExtent', '', project_wms_extent)

        return True, ''

    def save_cfg_file_cursor(self, close_dialog: bool):
        """ Save CFG file with a waiting cursor. """
        if not self.dlg.check_cfg_file_exists():
            new_project = NewConfigDialog()
            new_project.exec_()

        with OverrideCursor(Qt.WaitCursor):
            result = self.save_cfg_file()

        if not result:
            # Generation failed, error message without closing the dialog
            # noinspection PyUnresolvedReferences
            self.dlg.display_message_bar(
                'Lizmap',
                tr('An error occurred while generating the projet, please check logs'),
                level=Qgis.Critical,
                duration=DURATION_SUCCESS_BAR,
            )
            return

        # Generation is OK
        auto_send = None
        url = None
        upload_is_visible = not self.dlg.mOptionsListWidget.item(Panels.Upload).isHidden()
        if upload_is_visible and self.dlg.send_webdav.isChecked():
            # Send files if necessary
            auto_send, url = self.send_files()

        if close_dialog:
            # First close the dialog
            # The method if the dialog will check which message bar is appropriate according to visibility
            self.dlg.close()

        if auto_send is None:
            # noinspection PyUnresolvedReferences
            self.dlg.display_message_bar(
                'Lizmap',
                tr(
                    'The project has been generated in <a href="file://{path}">"{path}"</a>'
                ).format(
                    path=self.dlg.cfg_file().parent.absolute(),
                ),
                level=Qgis.Success,
                duration=DURATION_SUCCESS_BAR,
            )
            return

        if auto_send:
            # noinspection PyUnresolvedReferences
            self.dlg.display_message_bar(
                'Lizmap',
                tr('Project <a href="{}">published !</a>'.format(url)),
                level=Qgis.Success,
                duration=DURATION_SUCCESS_BAR,
            )
            return

        self.dlg.display_message_bar(
            'Lizmap',
            tr('Project file generated, but the upload has failed'),
            level=Qgis.Warning,
            duration=DURATION_SUCCESS_BAR,
        )

    def save_cfg_file(
            self,
            lwc_version: LwcVersions = None,
            save_project: bool = None,
            with_gui: bool = True,
    ) -> bool:
        """Save the CFG file.

        Check the user defined data from GUI and save them to both global and project config files.
        """
        self.dlg.log_panel.clear()
        self.dlg.log_panel.append(tr('Start saving the Lizmap configuration'), style=Html.P, time=True)
        variables = self.project.customVariables()
        variables['lizmap_repository'] = self.dlg.current_repository()
        self.project.setCustomVariables(variables)

        if not lwc_version:
            lwc_version = self.current_lwc_version()
            # Let's trigger UI refresh according to latest releases, if it wasn't available on startup
            self.lwc_version_changed()

        defined_env_target = os.getenv('LIZMAP_TARGET_VERSION')
        if defined_env_target:
            msg = "Version defined by environment variable : {}".format(defined_env_target)
            LOGGER.warning(msg)
            self.dlg.log_panel.append(msg)
            lwc_version = LwcVersions.find(defined_env_target)

        lwc_version: LwcVersions

        if with_gui:
            self.dlg.refresh_helper_target_version(lwc_version)
            qgis_group = self.existing_group(self.project.layerTreeRoot(), GroupNames.BaseLayers)
            if qgis_group and self.current_lwc_version() >= LwcVersions.Lizmap_3_7:
                self.disable_legacy_empty_base_layer()

        if self.version_checker:
            # Maybe running from CLI tools about the version_checker object
            self.version_checker.check_outdated_version(lwc_version, with_gui=with_gui)

        if not self.check_dialog_validity():
            LOGGER.debug("Leaving the dialog without valid project and/or server.")
            self.dlg.log_panel.append(tr("No project or server"), Html.H2)
            self.dlg.log_panel.append(
                tr('Either you do not have a server reachable for a long time or you do not have a project opened.'),
                level=Qgis.Warning,
            )
            return False

        stop_process = tr("The CFG is not saved due to errors that must be fixed.")

        if not self.server_manager.check_admin_login_provided() and not self.is_dev_version:
            self.dlg.log_panel.append(tr('Missing login on a server'), style=Html.H2)
            self.dlg.log_panel.append('{}<br><br>{}<br><br><br>{}'.format(
                    tr(
                        "You have set up a server in the first panel of the plugin, but you have not provided a "
                        "login/password."
                    ),
                    tr("Please go back to the server panel and edit the server to add a login."),
                    stop_process
            ))
            return False

        if not self.is_dev_version:
            if not self.server_manager.check_lwc_version(lwc_version.value):
                QMessageBox.critical(
                    self.dlg,
                    tr('Lizmap Target Version'),
                    '{}\n\n{}\n\n{}'.format(
                        tr(
                            "Your Lizmap Web Client target version {version} has not been found in the server "
                            "table.").format(version=lwc_version.value),
                        tr(
                            "Either check your Lizmap Web Client target version in the first panel of the plugin or "
                            "check you have provided the correct server URL."
                        ),
                        stop_process
                    ), QMessageBox.Ok)
                return False

        # global project option checking
        is_valid, message = self.check_global_project_options()
        if not is_valid:
            QMessageBox.critical(
                self.dlg, tr('Lizmap Error'), '{}\n\n{}'.format(message, stop_process), QMessageBox.Ok)
            return False

        # Get configuration from input fields

        # Need to get these values to check for Pseudo Mercator projection
        mercator_layers = [
            self.dlg.cbOsmMapnik.isChecked(),
            self.dlg.cb_open_topo_map.isChecked(),
            self.dlg.cbGoogleStreets.isChecked(),
            self.dlg.cbGoogleSatellite.isChecked(),
            self.dlg.cbGoogleHybrid.isChecked(),
            self.dlg.cbGoogleTerrain.isChecked(),
            self.dlg.cbBingStreets.isChecked(),
            self.dlg.cbBingSatellite.isChecked(),
            self.dlg.cbBingHybrid.isChecked(),
            self.dlg.cbIgnStreets.isChecked(),
            self.dlg.cbIgnSatellite.isChecked(),
            self.dlg.cbIgnTerrain.isChecked(),
            self.dlg.cbIgnCadastral.isChecked(),
        ]

        # self.dlg.log_panel.separator()
        # self.dlg.log_panel.append(tr('Map - options'), Html.Strong)
        # self.dlg.log_panel.separator()

        # Checking configuration data
        # Get the project data from api to check the "coordinate system restriction" of the WMS Server settings

        # public base-layers: check that the 3857 projection is set in the
        # "Coordinate System Restriction" section of the project WMS Server tab properties
        if True in mercator_layers:
            crs_list = self.project.readListEntry('WMSCrsList', '')
            mercator_found = False
            for i in crs_list[0]:
                if i == 'EPSG:3857':
                    mercator_found = True
            if not mercator_found:
                crs_list[0].append('EPSG:3857')
                self.project.writeEntry('WMSCrsList', '', crs_list[0])

        # write data in the lizmap json config file
        if not self.write_project_config_file(lwc_version, with_gui):
            return False

        msg = tr('Lizmap configuration file has been updated')
        # self.dlg.log_panel.append(tr('All the map parameters are correctly set'), abort=False, time=True)
        self.dlg.log_panel.append("<p>")
        self.dlg.log_panel.append(msg, style=Html.Strong, abort=False, time=True)
        self.dlg.log_panel.append("</p>")

        self.get_min_max_scales()

        # Ask to save the project
        auto_save = self.dlg.checkbox_save_project.isChecked()
        auto_send = self.dlg.send_webdav.isChecked()
        if save_project is None:
            # Only save when we are in GUI
            QgsSettings().setValue(Settings.key(Settings.AutoSave), auto_save)
            QgsSettings().setValue(Settings.key(Settings.AutoSend), auto_send)

        if self.project.isDirty():
            if save_project or auto_save:
                # Do not use QgsProject.write() as it will trigger file
                # modified warning in QGIS Desktop later
                self.iface.actionSaveProject().trigger()
            else:
                # noinspection PyUnresolvedReferences
                self.iface.messageBar().pushMessage(
                    'Lizmap',
                    tr('Please do not forget to save the QGIS project before publishing your map'),
                    level=Qgis.Warning,
                    duration=DURATION_WARNING_BAR
                )

        if not auto_save:
            # noinspection PyUnresolvedReferences
            self.iface.messageBar().pushMessage(
                'Lizmap',
                msg,
                level=Qgis.Success,
                duration=DURATION_MESSAGE_BAR
            )
            # No automatic saving, the process is finished
            return True

        return True

    def send_files(self) -> Tuple[bool, str]:
        """ Send both files to the server, designed for UI interaction.

        With a waiting cursor and sending messages to the message bar.
        """
        with OverrideCursor(Qt.WaitCursor):
            result, _, url = self.send_webdav()
        return result, url

    def create_new_repository(self):
        """ Open wizard to create a new remote repository. """
        dialog = CreateFolderWizard(
            self.dlg,
            webdav_server=self.webdav.dav_server,
            auth_id=self.webdav.auth_id,
            url=self.webdav.server_url(),
        )
        dialog.exec_()
        self.dlg.refresh_versions_button.click()

    # def open_web_browser_project(self):
    #     """ Open the project in the web browser. """
    #     url = self.webdav.project_url()
    #     # noinspection PyArgumentList
    #     QDesktopServices.openUrl(QUrl(url))

    def send_webdav(self) -> Tuple[bool, str, str]:
        """ Sync the QGS and CFG file over the webdav. """
        folder = self.dlg.current_repository(RepositoryComboData.Path)
        if not folder:
            # Maybe we are on a new server ?
            return False, '', ''

        with OverrideCursor(Qt.WaitCursor):
            qgis_exists, error = self.webdav.check_exists_qgs()
        if error:
            self.iface.messageBar().pushMessage('Lizmap', error, level=Qgis.Critical, duration=DURATION_WARNING_BAR)
            return False, '', ''

        server = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        if not qgis_exists:
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Question)
            box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )
            box.setWindowTitle(tr('The project is not published yet'))
            box.setText(tr(
                'The project <b>"{}"</b> does not exist yet on the server <br>'
                '<b>"{}"</b> '
                'in the folder <b>"{}"</b>.'
                '<br><br>'
                'Do you want to publish it for the first time in this directory ?'
            ).format(
                self.project.baseName(), server, folder))
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDefaultButton(QMessageBox.No)
            result = box.exec_()
            if result == QMessageBox.No:
                return False, '', ''

        with OverrideCursor(Qt.WaitCursor):
            flag, error, url = self.webdav.send_all_project_files()
        if not flag:
            # Error while sending files
            LOGGER.error(error)
            self.iface.messageBar().pushMessage('Lizmap', error, level=Qgis.Critical, duration=DURATION_WARNING_BAR)
            return False, error, ''

        LOGGER.debug("Webdav has been OK : {}".format(url))
        self.check_latest_update_webdav()

        if flag and qgis_exists:
            # Everything went fine
            return True, '', url

        # Only the first time if the project didn't exist before
        # noinspection PyArgumentList
        QDesktopServices.openUrl(QUrl(url))
        return True, '', url

    def create_media_dir_remote(self):
        """ Create the remote "media" directory. """
        directory = self.dlg.current_repository(RepositoryComboData.Path)
        if not directory:
            return

        with OverrideCursor(Qt.WaitCursor):
            result, msg = self.webdav.file_stats_media()
        if result is not None:
            self.dlg.display_message_bar(
                'Lizmap',
                tr('The "media" directory was already existing on the server. Please check with a file browser.'),
                level=Qgis.Info,
                duration=DURATION_WARNING_BAR,
                more_details=msg,
            )
            return

        box = QMessageBox(self.dlg)
        box.setIcon(QMessageBox.Question)
        box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )
        box.setWindowTitle(tr('Create "media" directory on the server'))
        box.setText(tr(
            'Are you sure you want to create the "media" directory on the server <strong>{server}</strong> in the '
            'Lizmap repository <strong>{name}</strong> ?'
        ).format(
            server=self.dlg.server_combo.currentText(),
            name=self.dlg.repository_combo.currentText()
        ))
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        result = box.exec_()
        if result == QMessageBox.No:
            return

        directory += 'media/'
        result, msg = self.webdav.make_dir(directory)
        if not result and msg:
            self.dlg.display_message_bar('Lizmap', msg, level=Qgis.Critical, duration=DURATION_WARNING_BAR)
            return

        self.dlg.display_message_bar(
            'Lizmap',
            tr('The "media" directory has been created'), level=Qgis.Success, duration=DURATION_WARNING_BAR)

    def create_media_dir_local(self):
        """ Create the local "media" directory. """
        media = Path(self.project.fileName()).parent.joinpath('media')
        media.mkdir(exist_ok=True)
        self.dlg.display_message_bar(
            'Lizmap',
            tr('The local <a href="file://{}">"media"</a> directory has been created').format(media),
            level=Qgis.Success,
            duration=DURATION_WARNING_BAR,
        )

    def upload_media(self):
        """ Upload the current media path on the server. """
        current_path = self.dlg.inLayerLink.text()

        # On Windows, it's like media\photo.png
        # TODO check line below
        # current_path = current_path.replace('\\', '/')

        if not current_path.startswith('media/'):
            self.dlg.display_message_bar(
                'Lizmap',
                tr('Path not starting by "media/"'),
                level=Qgis.Critical,
                duration=DURATION_WARNING_BAR
            )
            return

        current_file = Path(self.project.absolutePath()).joinpath(current_path)
        if not current_file.exists():
            self.dlg.display_message_bar(
                'Lizmap',
                tr('Path does not exist'),
                level=Qgis.Critical,
                duration=DURATION_WARNING_BAR
            )
            return

        if not current_file.is_file():
            self.dlg.display_message_bar(
                'Lizmap',
                tr('Path is not a file'),
                level=Qgis.Critical,
                duration=DURATION_WARNING_BAR
            )
            return

        with OverrideCursor(Qt.WaitCursor):
            result, message = self.webdav.send_media(current_file)
        if not result and message:
            self.dlg.display_message_bar('Lizmap', message, level=Qgis.Critical, duration=DURATION_WARNING_BAR)
            return

        msg = tr("File send")
        self.dlg.display_message_bar(
            'Lizmap',
            f'<a href="{self.webdav.media_url(current_path)}">{msg}</a>',
            level=Qgis.Success,
            duration=DURATION_WARNING_BAR,
        )
        return

    def upload_thumbnail(self):
        """ Upload the thumbnail on the server. """
        with OverrideCursor(Qt.WaitCursor):
            result, message = self.webdav.send_thumbnail()
        if not result and message:
            self.dlg.display_message_bar('Lizmap', message, level=Qgis.Critical, duration=DURATION_WARNING_BAR)
            return

        if result:
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Information)
            box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )
            box.setWindowTitle(tr('Cache about the thumbnail'))
            box.setText(tr(
                'The upload of the thumbnail is successful. You can open it in your <a href="{}">web-browser</a>.'
                ).format(message) + '<br><br>'
                + tr(
                'However, you might have some cache in your web-browser, for the next {number} hours. You should do a '
                'CTRL + F5 (or CTRL + MAJ + R or similar) to force the refresh of the page without using the '
                'web-browser cache.'
            ).format(number=24))
            box.setStandardButtons(QMessageBox.Ok)
            box.setDefaultButton(QMessageBox.Ok)
            box.exec_()

            file_stats, error = self.webdav.file_stats_thumbnail()
            if error:
                LOGGER.error(error)
                return
            self.dlg.set_tooltip_webdav(self.dlg.button_upload_thumbnail, file_stats.last_modified_pretty)
            self.dlg.line_thumbnail_date.setText(file_stats.last_modified_pretty)

    def upload_action(self):
        """ Upload the action file on the server. """
        with OverrideCursor(Qt.WaitCursor):
            result, error = self.webdav.send_action()
        if not result and error:
            self.dlg.display_message_bar('Lizmap', error, level=Qgis.Critical, duration=DURATION_WARNING_BAR)
            return

        if result:
            self.dlg.display_message_bar(
                'Lizmap',
                tr('Upload of the action file is successful.'),
                level=Qgis.Success,
                duration=DURATION_WARNING_BAR
            )
            file_stats, error = self.webdav.file_stats_action()
            if error:
                LOGGER.error(error)
                return
            self.dlg.set_tooltip_webdav(self.dlg.button_upload_action, file_stats.last_modified_pretty)
            self.dlg.line_action_date.setText(file_stats.last_modified_pretty)

    def _question_remove_remote_file(self) -> bool:
        """ Question to confirme deletion on the remote server. """
        box = QMessageBox(self.dlg)
        box.setIcon(QMessageBox.Question)
        box.setWindowIcon(QIcon(resources_path('icons', 'icon.png')), )
        box.setWindowTitle(tr('Remove a remote file'))
        box.setText(tr('Are you sure you want to remove the remote file ?'))
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        result = box.exec_()
        return result == QMessageBox.No

    def remove_remote_file(self, button: QPushButton):
        """ Remove a remote file. """
        if self._question_remove_remote_file():
            return
        with OverrideCursor(Qt.WaitCursor):
            if 'qgs' in button.objectName():
                self.webdav.remove_qgs()
                self.check_latest_update_webdav()
            elif 'cfg' in button.objectName():
                self.webdav.remove_cfg()
                self._refresh_cfg()
            elif 'action' in button.objectName():
                self.webdav.remove_action()
                self._refresh_action()
            elif 'thumbnail' in button.objectName():
                self.webdav.remove_thumbnail()
                self._refresh_thumbnail()

    def remove_remote_layer_index(self, row: int):
        """ Remove a layer from the remote server. """
        if self._question_remove_remote_file():
            return
        relative_path_layer = self.dlg.table_files.item(row, 1).data(self.dlg.table_files.RELATIVE_PATH)
        self.webdav.remove_file(str(relative_path_layer))
        self.refresh_single_layer(row)

    def refresh_single_layer(self, row: int):
        """ Refresh a single layer status. """
        relative_path_layer = self.dlg.table_files.item(row, 1).data(self.dlg.table_files.RELATIVE_PATH)
        # Refresh date and size from the server
        result, error = self.webdav.file_stats(path_to_url(relative_path_layer))
        if result:
            self.dlg.table_files.file_status(row, result.last_modified_pretty, human_size(result.content_length))
        elif result is None and not error:
            self.dlg.table_files.file_status(row, tr('Error'), tr("Not found on the server"))
        else:
            self.dlg.table_files.file_status(row, tr('Error'), error)

    def refresh_all_layers(self):
        """ Refresh the status of all layers. """
        for row in range(self.dlg.table_files.rowCount()):
            self.dlg.table_files.file_status(row, tr("Work in progress"), tr("Work in progress"))

        with OverrideCursor(Qt.WaitCursor):
            for row in range(self.dlg.table_files.rowCount()):
                self.refresh_single_layer(row)

    def send_all_layers(self):
        """ Send all layers from the table on the server. """
        for row in range(self.dlg.table_files.rowCount()):
            self.dlg.table_files.file_status(row, tr("Work in progress"), tr("Work in progress"))

        with OverrideCursor(Qt.WaitCursor):
            for row in range(self.dlg.table_files.rowCount()):
                relative_path_layer = self.dlg.table_files.item(row, 1).data(self.dlg.table_files.RELATIVE_PATH)
                absolute_path_layer = self.dlg.table_files.item(row, 1).data(self.dlg.table_files.ABSOLUTE_PATH)

                # Create recursive directories
                self.webdav.make_dirs_recursive(relative_path_layer, exists_ok=True)

                # Upload the layer path
                self.webdav.put_file(absolute_path_layer, relative_path_layer)

                # Refresh date and size from the server
                result, error = self.webdav.file_stats(path_to_url(relative_path_layer))
                if result:
                    self.dlg.table_files.file_status(row, result.last_modified_pretty, human_size(result.content_length))
                elif result is None and not error:
                    self.dlg.table_files.file_status(row, tr('Error'), tr("Not found on the server"))
                else:
                    self.dlg.table_files.file_status(row, tr('Error'), error)

    def _refresh_cfg(self):
        """ Refresh CFG. """
        with OverrideCursor(Qt.WaitCursor):
            directory = self.dlg.current_repository()
            self.dlg.line_cfg_date.setText("")
            result, error = self.webdav.file_stats_cfg()
            if result:
                self.dlg.line_cfg_date.setText(f"{result.last_modified_pretty} : {human_size(result.content_length)}")  # NOQA E203
            elif result is None and not error:
                self.dlg.line_cfg_date.setText(tr(
                    "Project {name} not found in {folder}").format(name=self.project.baseName(), folder=directory))
            else:
                self.dlg.line_cfg_date.setText(error)

    def _refresh_thumbnail(self):
        """ Refresh thumbnail. """
        with OverrideCursor(Qt.WaitCursor):
            directory = self.dlg.current_repository()
            self.dlg.line_thumbnail_date.setText("")
            result, error = self.webdav.file_stats_thumbnail()
            if result:
                self.dlg.line_thumbnail_date.setText(f"{result.last_modified_pretty} : {human_size(result.content_length)}")  # NOQA E203
                self.dlg.set_tooltip_webdav(self.dlg.button_upload_thumbnail, result.last_modified_pretty)
            elif result is None and not error:
                self.dlg.line_thumbnail_date.setText(tr(
                    "Project thumbnail {name} not found in {folder}").format(
                    name=self.project.baseName(),
                    folder=directory)
                )
            else:
                self.dlg.line_thumbnail_date.setText(error)

    def _refresh_action(self):
        """ Refresh action. """
        with OverrideCursor(Qt.WaitCursor):
            self.dlg.line_action_date.setText("")
            result, error = self.webdav.file_stats_action()
            if result:
                self.dlg.line_action_date.setText(result.last_modified_pretty)
                self.dlg.set_tooltip_webdav(self.dlg.button_upload_action, result.last_modified_pretty)
            else:
                self.dlg.line_action_date.setText(error)

    def check_all_dates_dav(self):
        """ Check all dates on the Web DAV server. """
        self.check_latest_update_webdav()
        self._refresh_cfg()
        self._refresh_thumbnail()
        self._refresh_action()

        # Media
        self.dlg.line_media_date.setText("")
        with OverrideCursor(Qt.WaitCursor):
            result, error = self.webdav.file_stats_media()
            if result:
                self.dlg.line_media_date.setText(result.last_modified_pretty)
            else:
                self.dlg.line_media_date.setText(error)

    def check_latest_update_webdav(self):
        """ Check the latest date about QGS file on the server. """
        with OverrideCursor(Qt.WaitCursor):
            self.dlg.line_qgs_date.setText("")
            result, error = self.webdav.file_stats_qgs()
            if result:
                url = self.webdav.project_url()
                self.dlg.webdav_last_update.setText(f'<a href="{url}">{result.last_modified_pretty}</a>')
                self.dlg.webdav_last_update.setOpenExternalLinks(True)
                self.dlg.set_tooltip_webdav(self.dlg.button_upload_webdav, result.last_modified_pretty)
                self.dlg.line_qgs_date.setText(f"{result.last_modified_pretty} : {human_size(result.content_length)}")  # NOQA E203
            elif result is None and not error:
                directory = self.dlg.current_repository()
                self.dlg.line_qgs_date.setText(tr(
                    "Project {name} not found in {folder}").format(name=self.project.baseName(), folder=directory))
            else:
                self.dlg.webdav_last_update.setText(tr("Error"))
                self.dlg.webdav_last_update.setToolTip(error)
                self.dlg.line_qgs_date.setText(error)
                LOGGER.error(error)

    def check_server_capabilities(self):
        """ If we are stuck on the dialog, let's try manually ..."""
        self.check_webdav()
        self.check_training_panel()
        # Do NOT CALL target_server_changed
        # self.target_server_changed()
        current_version = self.current_lwc_version()
        self.dlg.refresh_helper_target_version(current_version)
        self.lwc_version_changed()

    def check_visibility_crs_3857(self):
        """ Check if we display the warning about scales.

        These checkboxes are deprecated starting from Lizmap Web Client 3.7.
        """
        visible = False
        for item in self.crs_3857_base_layers_list.values():
            if item.isChecked():
                visible = True

        current_version = self.current_lwc_version()
        if not current_version:
            # No server yet
            return

        if current_version >= LwcVersions.Lizmap_3_7:
            # We start showing some deprecated warnings if needed
            self.dlg.warning_base_layer_deprecated.setVisible(True)

            if visible:
                # At least one checkbox was used, we still need to enable widgets
                self.dlg.gb_externalLayers.setEnabled(True)
            else:
                # It means no checkboxes were used
                self.dlg.gb_externalLayers.setEnabled(False)

            if not self.dlg.cbAddEmptyBaselayer.isChecked():
                # Only when the checkbox wasn't used before
                self.dlg.cbAddEmptyBaselayer.setEnabled(False)

            if self.dlg.cbStartupBaselayer.count() == 0:
                # When no item in the combobox
                self.dlg.cbStartupBaselayer.setEnabled(False)

            if self.dlg.cbStartupBaselayer.count() == 1:
                # When only one item in the combobox but it's the 'empty' base layer
                if self.dlg.cbStartupBaselayer.itemText(0) == 'empty':
                    self.dlg.cbStartupBaselayer.setEnabled(False)

        else:
            # We do nothing ...
            self.dlg.warning_base_layer_deprecated.setVisible(False)
            self.dlg.gb_externalLayers.setEnabled(True)
            self.dlg.cbAddEmptyBaselayer.setEnabled(True)
            self.dlg.cbStartupBaselayer.setEnabled(True)
            self.dlg.scales_warning.setVisible(visible)

    def on_baselayer_checkbox_change(self):
        """
        Add or remove a base-layer in cbStartupBaselayer combobox
        when user change state of any base-layer related checkbox
        """
        if not self.layerList:
            return

        # Combo to fill up with base-layer
        combo = self.dlg.cbStartupBaselayer

        # First get selected item
        idx = combo.currentIndex()
        data = combo.itemData(idx)

        # Clear the combo
        combo.clear()
        i = 0
        blist = []

        # Fill with checked base-layers
        # 1/ QGIS layers
        for k, v in self.layerList.items():
            if not v['baseLayer']:
                continue
            combo.addItem(v['name'], v['name'])
            blist.append(v['name'])
            if data == k:
                idx = i
            i += 1

        # 2/ External base-layers
        for k, v in self.base_layer_widget_list.items():
            if k != 'layer':
                if v.isChecked():
                    combo.addItem(k, k)
                    blist.append(k)
                    if data == k:
                        idx = i
                    i += 1

        # Set last chosen item
        combo.setCurrentIndex(idx)

        # Fill self.globalOptions
        self.global_options['startupBaselayer']['list'] = blist

    def set_startup_baselayer_from_config(self):
        """
        Read lizmap current cfg configuration
        and set the startup base-layer if found
        """
        if not self.dlg.check_cfg_file_exists():
            return

        with open(self.dlg.cfg_file(), encoding='utf8') as f:
            json_file_reader = f.read()

        # noinspection PyBroadException
        try:
            json_content = json.loads(json_file_reader)
            json_options = json_content['options']

            base_layer = json_options.get('startupBaselayer')
            if not base_layer:
                return

            i = self.dlg.cbStartupBaselayer.findData(base_layer)
            if i < 0:
                return

            self.dlg.cbStartupBaselayer.setCurrentIndex(i)
        except Exception:
            pass

    def reinit_default_properties(self):
        for key in self.layers_table.keys():
            self.layers_table[key]['jsonConfig'] = dict()

    def on_project_read(self):
        """
        Close Lizmap plugin when project is opened
        """
        self.reinit_default_properties()
        self.dlg.close()

    def open_dock_preview_maptip(self):
        if self.dock_html_preview.isVisible():
            return

        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_html_preview)
        self.dock_html_preview.setVisible(True)

    def check_training_panel(self):
        """ Check if the training panel should be visible or not. """
        current_url = self.dlg.current_server_info(ServerComboData.ServerUrl.value)
        # By default, set to a long training, with ZIP file
        self.dlg.workshop_type.setCurrentWidget(self.dlg.training_panel)

        if not current_url:
            self.dlg.mOptionsListWidget.item(Panels.Training).setHidden(True)
            return

        if bool([domain for domain in WORKSHOP_DOMAINS if (domain in current_url)]):
            self.dlg.mOptionsListWidget.item(Panels.Training).setHidden(False)

        LOGGER.info("Current server has been detected as a training server.")

        metadata = self.dlg.current_server_info(ServerComboData.JsonMetadata.value)
        repositories = metadata.get('repositories')
        if not repositories:
            return

        workshop = repositories.get(WORKSHOP_FOLDER_ID)
        if not workshop:
            return

        auth_id = self.dlg.current_server_info(ServerComboData.AuthId.value)
        user_project = workshop['projects'].get(self.login_from_auth_id(auth_id))
        if not user_project:
            return

        # Now set, to a short training with the prepared project
        # TODO remove or improve very soon
        self.dlg.send_webdav.setChecked(True)
        self.dlg.checkbox_save_project.setChecked(True)
        self.dlg.radio_beginner.setChecked(True)
        self.dlg.workshop_type.setCurrentWidget(self.dlg.quick_workshop_panel)
        LOGGER.info(f"Remote project '{user_project}', matching the user connected, has been detected on the server")

    def download_training_data_clicked(self, workshop_type: str = WorkshopType.ZipFile):
        """ Download the hard coded ZIP. """
        if workshop_type == WorkshopType.IndividualQgsFile:
            if not self.dlg.path_training_folder_qgs.filePath():
                return
        else:
            if not self.dlg.path_training_folder_zip.filePath():
                return

        metadata = self.dlg.current_server_info(ServerComboData.JsonMetadata.value)
        url = webdav_url(metadata)
        if not url:
            self.dlg.display_message_bar(
                CLOUD_NAME,
                tr("WebDAV is not available on the instance '{}'").format(
                    self.dlg.current_server_info(ServerComboData.ServerUrl.value)),
                level=Qgis.Critical,
            )

        if workshop_type == WorkshopType.IndividualQgsFile:
            auth_id = self.dlg.current_server_info(ServerComboData.AuthId.value)
            user_project = self.login_from_auth_id(auth_id)
            url_path = f"{url}/{WORKSHOP_FOLDER_PATH}/{user_project}.qgs"
            destination = str(
                self.training_folder_destination(WorkshopType.IndividualQgsFile).joinpath(f'{user_project}.qgs'))
        else:
            url_path = f"{url}/{TRAINING_ZIP}"
            destination = str(Path(tempfile.gettempdir()).joinpath(TRAINING_ZIP))

        downloader = QgsFileDownloader(
            QUrl(url_path),
            destination,
            delayStart=True,
            authcfg=self.dlg.current_server_info(ServerComboData.AuthId.value),
        )
        loop = QEventLoop()
        downloader.downloadExited.connect(loop.quit)
        downloader.downloadError.connect(self.download_error)
        # downloader.downloadCanceled.connect(self.download_canceled)
        if workshop_type == WorkshopType.IndividualQgsFile:
            downloader.downloadCompleted.connect(self.download_completed_qgs)
        else:
            downloader.downloadCompleted.connect(self.download_completed_zip)
        downloader.startDownload()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        loop.exec_()

    @staticmethod
    def login_from_auth_id(auth_id) -> str:
        """ Login used in the QGIS password manager from an Auth ID. """
        # noinspection PyArgumentList
        auth_manager = QgsApplication.authManager()
        conf = QgsAuthMethodConfig()
        auth_manager.loadAuthenticationConfig(auth_id, conf, True)
        return conf.config('username')

    def download_error(self, errors):
        """ Display error message about the download. """
        QApplication.restoreOverrideCursor()
        self.dlg.display_message_bar(
            CLOUD_NAME,
            tr("Error while downloading the project : {}").format(','.join(errors)),
            level=Qgis.Critical
        )

    def download_completed_qgs(self):
        """ Extract the downloaded QGS. """
        # We start again about CFG file
        metadata = self.dlg.current_server_info(ServerComboData.JsonMetadata.value)
        url = webdav_url(metadata)
        auth_id = self.dlg.current_server_info(ServerComboData.AuthId.value)
        user_project = self.login_from_auth_id(auth_id)
        url_path = f"{url}/{WORKSHOP_FOLDER_PATH}/{user_project}.qgs.cfg"
        destination = str(
            self.training_folder_destination(WorkshopType.IndividualQgsFile).joinpath(f'{user_project}.qgs.cfg'))

        downloader = QgsFileDownloader(
            QUrl(url_path),
            destination,
            delayStart=True,
            authcfg=self.dlg.current_server_info(ServerComboData.AuthId.value),
        )
        loop = QEventLoop()
        downloader.downloadExited.connect(loop.quit)
        downloader.downloadError.connect(self.download_error)
        # downloader.downloadCanceled.connect(self.download_canceled)
        downloader.downloadCompleted.connect(self.download_completed)
        downloader.startDownload()
        loop.exec_()

    def download_completed(self):
        """ Show the success bar, for both kind of workshops. """
        QApplication.restoreOverrideCursor()
        with OverrideCursor(Qt.WaitCursor):
            self.dlg.display_message_bar(
                CLOUD_NAME,
                tr("Download and extract OK about the training project"),
                level=Qgis.Success
            )

    def download_completed_zip(self):
        """ Extract the downloaded zip. """
        file_path = self.training_folder_destination(WorkshopType.ZipFile)
        with zipfile.ZipFile(Path(tempfile.gettempdir()).joinpath(TRAINING_ZIP), 'r') as zip_ref:
            zip_ref.extractall(str(file_path))

        cfg_file = file_path.joinpath(TRAINING_PROJECT + ".cfg")
        if cfg_file.exists():
            # Never apply a CFG downloaded from the internet if it's present in the ZIP by mistake
            cfg_file.unlink()

        # Make the project more unique
        qgs_file = file_path.joinpath(TRAINING_PROJECT)
        qgs_file.rename(Path(qgs_file.parent, qgs_file.stem + "_" + self.destination_name() + qgs_file.suffix))
        self.download_completed()

    def destination_name(self) -> str:
        """ Return the destination cleaned name. """
        destination = self.dlg.name_training_folder.text()
        if not destination:
            destination = self.dlg.name_training_folder.placeholderText()

        destination = unaccent(destination)
        destination = destination.replace('-', '_')
        destination = destination.replace(' ', '_')
        destination = destination.replace("'", '_')
        destination = destination.lower()
        return destination

    def training_folder_destination(self, workshop_type: str = WorkshopType.ZipFile) -> Optional[Path]:
        """ Destination folder where to store the data. """
        if workshop_type == WorkshopType.IndividualQgsFile:
            output = Path(self.dlg.path_training_folder_qgs.filePath())
            QgsSettings().setValue(Settings.key(Settings.LizmapRepository), WORKSHOP_FOLDER_ID)
        else:
            file_path = self.dlg.path_training_folder_zip.filePath()
            if not file_path:
                return

            destination = self.destination_name()
            output = Path(file_path).joinpath(destination)
            QgsSettings().setValue(Settings.key(Settings.LizmapRepository), destination)

        if not output:
            return

        if not output.exists():
            output.mkdir()

        return output

    def open_training_folder_clicked(self, workshop_type: str = WorkshopType.ZipFile):
        """ Open the training folder set above. """
        file_path = self.training_folder_destination(workshop_type)
        if not file_path:
            return

        # noinspection PyArgumentList
        QDesktopServices.openUrl(QUrl(f"file://{file_path}"))  # NOQA E231

    def open_training_project_clicked(self, workshop_type: str = WorkshopType.ZipFile):
        """ Open the training project in QGIS Desktop. """
        file_path = self.training_folder_destination(workshop_type)
        if workshop_type == WorkshopType.IndividualQgsFile:
            auth_id = self.dlg.current_server_info(ServerComboData.AuthId.value)
            user_project = self.login_from_auth_id(auth_id)
            project_path = str(file_path.joinpath(f"{user_project}.qgs"))
        else:
            user_project = self.current_login()
            project_path = str(file_path.joinpath(TRAINING_PROJECT))

        if not file_path:
            return

        with OverrideCursor(Qt.WaitCursor):
            self.project.read(project_path)
            # Rename the project
            self.project.writeEntry("WMSServiceTitle", "/", user_project)

        # Enable the "Upload" panel
        item = self.dlg.mOptionsListWidget.item(Panels.Upload)
        item.setFlags(item.flags() | Qt.ItemIsEnabled)

        variables = self.project.customVariables()
        if 'lizmap_user' in list(variables.keys()):
            del variables['lizmap_user']
        if 'lizmap_user_groups' in list(variables.keys()):
            del variables['lizmap_user_groups']
        self.project.setCustomVariables(variables)

    def run(self) -> bool:
        """Plugin run method : launch the GUI."""
        self.dlg.check_action_file_exists()
        self.dlg.check_project_thumbnail()
        self.check_webdav()

        if self.dlg.isVisible():
            # show dialog in front of QGIS
            self.dlg.raise_()
            self.dlg.activateWindow()
            return False

        # QGIS Plugin manager
        if QGIS_PLUGIN_MANAGER:
            plugin_manager = QgisPluginManager()
            self.update_plugin = plugin_manager.current_plugin_needs_update()

        self.version_checker = VersionChecker(self.dlg, VERSION_URL, self.is_dev_version)
        self.version_checker.fetch()

        if not self.check_dialog_validity():
            # Go back to the first panel because no project loaded.
            # Otherwise, the plugin opens the latest valid panel before the previous project has been closed.
            self.dlg.mOptionsListWidget.setCurrentRow(Panels.Information)
        else:
            # Starting from LWC 3.7, we need to know the server BEFORE reading the CFG file
            # So we do not read CFG file if the navigation is not OK

            # Reading the CFG will trigger signals with input text and the plugin will check the validity
            # We do not want that.
            # https://github.com/3liz/lizmap-plugin/issues/513
            self.dlg.block_signals_address(True)

            # Get config file data
            self.read_cfg_file()

            self.dlg.block_signals_address(False)

        self.dlg.show()

        auto_save = QgsSettings().value(Settings.key(Settings.AutoSave), False, bool)
        self.dlg.checkbox_save_project.setChecked(auto_save)

        auto_send = QgsSettings().value(Settings.key(Settings.AutoSend), False, bool)
        self.dlg.send_webdav.setChecked(auto_send)

        self.dlg.exec_()
        # self.check_webdav()
        return True
