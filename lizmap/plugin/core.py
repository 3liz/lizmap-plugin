import contextlib
import json
import logging
import os
import re
import tempfile

from functools import cached_property, partial
from os.path import relpath
from pathlib import Path
from shutil import copyfile
from typing import (
    TYPE_CHECKING,
    Dict,
    Optional,
    Tuple,
    cast,
)

from pyplugin_installer.version_compare import compareVersions
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsEditFormConfig,
    QgsExpression,
    QgsLayerTreeGroup,
    QgsMapLayer,
    QgsMapLayerProxyModel,
    QgsMasterLayoutInterface,
    QgsProject,
    QgsRectangle,
    QgsSettings,
    QgsVectorLayer,
)
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QStorageInfo,
    Qt,
    QTranslator,
    QUrl,
)
from qgis.PyQt.QtGui import (
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QTextCursor,
)
from qgis.PyQt.QtWidgets import (
    QAction,
    QDialogButtonBox,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
)
from qgis.utils import OverrideCursor
from qgis.utils import plugins as all_plugins

from lizmap.config import LizmapConfig, MappingQgisGeometryType
from lizmap.definitions.atlas import AtlasDefinitions
from lizmap.definitions.attribute_table import AttributeTableDefinitions
from lizmap.definitions.definitions import (
    DEV_VERSION_PREFIX,
    DURATION_MESSAGE_BAR,
    DURATION_SUCCESS_BAR,
    DURATION_WARNING_BAR,
    UNSTABLE_VERSION_PREFIX,
    GroupNames,
    Html,
    LayerProperties,
    LwcVersions,
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
from lizmap.dialogs.confirmation_text_box import ConfirmationTextMessageBox
from lizmap.dialogs.dock_html_preview import HtmlPreview
from lizmap.dialogs.html_editor import HtmlEditorDialog
from lizmap.dialogs.html_maptip import HtmlMapTipDialog
from lizmap.dialogs.lizmap_popup import LizmapPopupDialog
from lizmap.dialogs.main import LizmapDialog
from lizmap.dialogs.news import NewConfigDialog
from lizmap.dialogs.server_wizard import CreateFolderWizard
from lizmap.dialogs.wizard_group import WizardGroupDialog
from lizmap.forms.atlas_edition import AtlasEditionDialog
from lizmap.forms.attribute_table_edition import AttributeTableEditionDialog
from lizmap.forms.edition_edition import EditionLayerDialog
from lizmap.forms.filter_by_form_edition import FilterByFormEditionDialog
from lizmap.forms.filter_by_login import FilterByLoginEditionDialog
from lizmap.forms.filter_by_polygon import FilterByPolygonEditionDialog
from lizmap.forms.layout_edition import LayoutEditionDialog
from lizmap.forms.locate_layer_edition import LocateLayerEditionDialog
from lizmap.forms.time_manager_edition import TimeManagerEditionDialog
from lizmap.forms.tooltip_edition import ToolTipEditionDialog
from lizmap.ogc_project_validity import OgcProjectValidity
from lizmap.project_checker_tools import (  # duplicated_layer_with_filter_legend,
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
    duplicated_rule_key_legend,
    project_invalid_pk,
    project_safeguards_checks,
    project_tos_layers,
    project_trust_layer_metadata,
    simplify_provider_side,
    trailing_layer_group_name,
    use_estimated_metadata,
)
from lizmap.saas import check_project_ssl_postgis, is_lizmap_cloud
from lizmap.table_manager.base import TableManager
from lizmap.table_manager.dxf_export import TableManagerDxfExport
from lizmap.table_manager.layouts import TableManagerLayouts
from lizmap.widgets.check_project import Check, SourceField
from lizmap.widgets.project_tools import (
    empty_baselayers,
    is_layer_published_wfs,
)

try:
    from lizmap.plugin_manager import QgisPluginManager
    QGIS_PLUGIN_MANAGER = True
except ModuleNotFoundError:
    # In a standalone application
    QGIS_PLUGIN_MANAGER = False

from qgis.core import QgsProjectServerValidator

from lizmap.qt_style_sheets import NEW_FEATURE_CSS
from lizmap.server_dav import WebDav
from lizmap.server_lwc import MAX_DAYS, ServerManager
from lizmap.toolbelt.convert import ambiguous_to_bool, as_boolean
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
from lizmap.toolbelt.resources import (
    load_icon,
    plugin_name,
    plugin_path,
    window_icon,
)
from lizmap.toolbelt.strings import human_size, path_to_url, unaccent
from lizmap.toolbelt.version import (
    format_version_integer,
    qgis_version_info,
    version,
)
from lizmap.tooltip import Tooltip
from lizmap.version_checker import VersionChecker

from . import baselayers
from . import helpers
from .dataviz import DatavizManager
from .layer_tree import LayerTreeManager
from .lwc_versions import LwcVersionManager
from .options import global_options, layer_options
from .scales import ScalesManager
from .settings import configure_qgis_settings
from .training import TrainingManager
from .webdav import WebDavManager

if TYPE_CHECKING:
    from lizmap.drag_drop_dataviz_manager import DragDropDatavizManager

LOGGER = logging.getLogger(plugin_name())
VERSION_URL = 'https://raw.githubusercontent.com/3liz/lizmap-web-client/versions/versions.json'
# To try a local file
# VERSION_URL = 'file:///home/etienne/.local/share/QGIS/QGIS3/profiles/default/Lizmap/released_versions.json'


class Lizmap:

    @cached_property
    def scale_mngr(self) -> ScalesManager:
        return ScalesManager(
            dlg=self.dlg,
            global_options=self.global_options,
            is_dev_version=self.is_dev_version,
            lwc_version_mngr=self.version_mngr,
        )

    @cached_property
    def training_mngr(self) -> TrainingManager:
        return TrainingManager(
            dlg=self.dlg,
            project=self.project,
        )

    @cached_property
    def layer_tree_mngr(self) -> LayerTreeManager:
        return LayerTreeManager(
            dlg=self.dlg,
            project=self.project,
            is_dev_version=self.is_dev_version,
            lwc_version_mngr=self.version_mngr,
            iface=self.iface,
        )

    @property
    def layerList(self) -> Dict:
        return self.layer_tree_mngr.layerList

    @cached_property
    def dataviz_mngr(self) -> DatavizManager:
        return DatavizManager(
            dlg=self.dlg,
            is_dev_version=self.is_dev_version,
            lwc_version_mngr=self.version_mngr,
        )

    @property
    def drag_drop_dataviz(self) -> "DragDropDatavizManager":
        return cast("DragDropDatavizManager", self.dataviz_mngr.drag_drop_dataviz)

    @property
    def lwc_version(self) -> LwcVersions:
        return self.version_mngr.lwc_version

    @property
    def webdav(self) -> WebDav:
        return self.webdav_mngr.webdav

    def __init__(self, iface: QgisInterface, lwc_version: LwcVersions = None):
        """Constructor of the Lizmap plugin."""
        LOGGER.info("Plugin starting")
        self.iface = iface
        # noinspection PyArgumentList
        self.project = QgsProject.instance()

        # Configure QGIS settings
        configure_qgis_settings()
        # Connect the current project filepath
        self.current_path = None

        self.project.fileNameChanged.connect(self.filename_changed)
        self.project.projectSaved.connect(self.project_saved)
        self.filename_changed()
        self.update_plugin = None

        setup_logger(plugin_name())

        locale, file_path = setup_translation('lizmap_qgis_plugin_{}.qm', plugin_path('i18n'))
        LOGGER.info("Language in QGIS : {}".format(locale))

        if file_path:
            self.translator = QTranslator()
            self.translator.load(str(file_path.absolute()))
            QCoreApplication.installTranslator(self.translator)

        lizmap_config = LizmapConfig(project=self.project)

        self.lizmap_config = lizmap_config
        self.version = version()
        self.is_dev_version = any(item in self.version for item in UNSTABLE_VERSION_PREFIX)
        self.dlg = LizmapDialog(is_dev_version=self.is_dev_version, lwc_version=lwc_version)

        # Must only be used in tests
        # In production, version is coming from the UI, according to the current server selected
        # In production, this variable must be None
        self.version_mngr = LwcVersionManager(self.dlg, lwc_version)
        self.webdav_mngr = WebDavManager(self.dlg, self.project)

        self.dock_html_preview = None
        self.version_checker = None
        if self.is_dev_version:
            self.configure_dev_version()

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

        # Manage LWC versions combo
        self.dlg.label_lwc_version.setStyleSheet(NEW_FEATURE_CSS)

        self.lizmap_cloud = [
            self.dlg.label_lizmap_search_grant,
            self.dlg.label_safe_lizmap_cloud,
        ]

        self.layers_table = dict()

        # Initialize global options
        self.global_options = global_options(self.dlg, lizmap_config)
        self.layer_options_list = layer_options(self.dlg, lizmap_config, self.global_options)

        # Connect single WMS checkbox to enable/disable the exclude basemaps option
        self.dlg.checkbox_wms_single_request_all_layers.toggled.connect(self.on_single_wms_toggled)
        self.on_single_wms_toggled(self.dlg.checkbox_wms_single_request_all_layers.isChecked())

        # Initialize layer tree
        self.layer_tree_mngr.initialize()

        # Initialize scales UI
        self.scale_mngr.initialize()

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
            button.setIcon(load_icon('upload.svg'))
            button.setText('')
            self.dlg.set_tooltip_webdav(button)
        self.dlg.button_upload_thumbnail.clicked.connect(self.upload_thumbnail)
        self.dlg.button_upload_action.clicked.connect(self.upload_action)
        self.dlg.button_upload_webdav.clicked.connect(self.send_files)
        self.dlg.button_upload_media.clicked.connect(self.upload_media)
        self.dlg.button_create_media_remote.clicked.connect(self.create_media_dir_remote)
        self.dlg.button_create_media_local.clicked.connect(self.create_media_dir_local)

        # Base layers
        baselayers.configure_base_layers(self.dlg, self.layer_tree_mngr)

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
                elif item['wType'] == 'radio':
                    control.toggled.connect(slot)
                elif item['wType'] == 'list':
                    control.currentIndexChanged.connect(slot)
                elif item['wType'] == 'layers':
                    control.layerChanged.connect(slot)
                elif item['wType'] == 'fields':
                    control.fieldChanged.connect(slot)

        self.baselayers_mngr = baselayers.BaseLayersManager(
            self.dlg,
            self.version_mngr,
        )

        for item in self.baselayers_mngr.base_layer_widget_list.values():
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

        current = qgis_version_info(Qgis.versionInt())
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
            'dxfExport': {
                'panel': Panels.DxfExport,
                'tableWidget': self.dlg.table_dxf_export,
                'addButton': self.dlg.add_dxf_export_layer,
                'removeButton': self.dlg.remove_dxf_export_layer,
                'editButton': self.dlg.edit_dxf_export_layer,
                'upButton': self.dlg.up_dxf_export_layer,
                'downButton': self.dlg.down_dxf_export_layer,
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
        self.dlg.layer_filter_polygon.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        self.dlg.layer_filter_polygon.layerChanged.connect(self.dlg.field_filter_polygon.setLayer)
        self.dlg.field_filter_polygon.setLayer(self.dlg.layer_filter_polygon.currentLayer())

        # Server combo
        server = QgsSettings().value('lizmap/instance_target_url', '')
        if server:
            index = self.dlg.server_combo.findData(server, ServerComboData.ServerUrl.value)
            if index:
                self.dlg.server_combo.setCurrentIndex(index)
        self.dlg.server_combo.currentIndexChanged.connect(self.target_server_changed)
        self.dlg.repository_combo.currentIndexChanged.connect(self.target_repository_changed)
        self.target_server_changed()
        self.lwc_version_changed()
        self.dlg.refresh_combo_repositories()

        self.dlg.tab_dataviz.setCurrentIndex(0)

        # Initialize training
        self.training_mngr.initialize(self.current_login())

        self.dlg.button_quick_start.clicked.connect(self.dlg.open_lizmap_how_to)
        self.dlg.workshop_edition.clicked.connect(self.dlg.open_workshop_edition)

        self.action = None
        self.help_action = None
        self.help_action_cloud = None

    def configure_dev_version(self):
        # File handler for logging
        temp_dir = Path(tempfile.gettempdir()).joinpath('QGIS_Lizmap')
        if not temp_dir.exists():
            temp_dir.mkdir()

        if not as_boolean(os.getenv("CI")):
            file_handler = logging.FileHandler(temp_dir.joinpath("lizmap.log"))
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            add_logging_handler_once(LOGGER, file_handler)
            LOGGER.debug(
                f"The directory <a href='file://{temp_dir}'>{temp_dir}</a> "
                "is currently used for file logging."
            )

        # All logs
        def write_log_message(message, tag, level):
            """ Write all tabs from QGIS to files. """
            temp_dir_log = Path(tempfile.gettempdir()).joinpath('QGIS_Lizmap')
            with open(temp_dir_log.joinpath("all.log"), 'a') as log_file:
                log_file.write(
                    '{tag}({level}): {message}'.format(tag=tag, level=level, message=message)
                )

        QgsApplication.messageLog().messageReceived.connect(write_log_message)

        self.dlg.setWindowTitle('Lizmap branch {}, commit {}, next {}'.format(
            self.version, current_git_hash(), next_git_tag()))

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

        new_cfg = new_path.with_suffix('.qgs.cfg')
        if new_cfg.exists():
            # The CFG was already here, let's keep the previous one
            return

        if self.current_path and new_path != self.current_path and not as_boolean(os.getenv("CI")):
            old_cfg = self.current_path.with_suffix('.qgs.cfg')
            if old_cfg.exists():
                box = QMessageBox(self.dlg)
                box.setIcon(QMessageBox.Icon.Question)
                box.setWindowIcon(window_icon() )
                box.setWindowTitle(tr('Project has been renamed'))
                box.setText(tr(
                    'The previous project located at "{}" was associated to a Lizmap configuration. '
                    'Do you want to copy the previous Lizmap configuration file to this new project ?'
                ).format(self.current_path))
                box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                box.setDefaultButton(QMessageBox.StandardButton.No)
                result = box.exec()
                if result == QMessageBox.StandardButton.No:
                    return

                copyfile(str(old_cfg), str(new_cfg))
                LOGGER.info("Project has been renamed and Lizmap configuration file has been copied as well.")

        self.current_path = new_path

    @staticmethod
    def current_login() -> str:
        """ Current login on the OS. """
        try:
            return os.getlogin()
        except OSError:
            return 'repository'

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

        if current_metadata and current_metadata.get("info"):
            current_version = LwcVersions.find(current_metadata["info"].get("version", "_"))
            # FIXME: handle 'None' value
            self.dlg.refresh_helper_target_version(current_version)

        current_version = self.lwc_version
        old_version = QgsSettings().value('lizmap/lizmap_web_client_version', type=str)
        if current_version != old_version:
            self.lwc_version_changed()
        self.dlg.check_qgis_version(widget=True)

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
        self.baselayers_mngr.check_visibility_crs_3857()

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
        # The new repository is only set when we save the CFG file
        # Otherwise, it will make a mess with the signals about the last repository used and the server refreshed list
        if self.dlg.page_dataviz.isVisible():
            self.layers_table['datavizLayers'].get('manager').preview_dataviz_dialog()

    def lwc_version_changed(self):
        self.version_mngr.lwc_version_changed(self.layers_table)

    def check_webdav(self):
        # I hope temporary, to force the version displayed
        self.dlg.refresh_helper_target_version(self.lwc_version)
        self.webdav_mngr.check_webdav()

    def initGui(self):
        """Create action that will start plugin configuration"""
        LOGGER.debug("Plugin starting in the initGui")

        icon = window_icon()
        self.action = QAction(icon, 'Lizmap', self.iface.mainWindow())

        # connect the action to the run method
        # noinspection PyUnresolvedReferences
        self.action.triggered.connect(self.run)

        self.dock_html_preview = HtmlPreview(None)
        self.dock_html_preview.set_server_url(self.dlg.current_server_info(ServerComboData.ServerUrl.value))
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_html_preview)
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

        self.dlg.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.dlg.close)
        self.dlg.buttonBox.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(partial(self.save_cfg_file_cursor, False))
        self.dlg.buttonBox.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(partial(self.save_cfg_file_cursor, True))
        self.dlg.buttonBox.button(QDialogButtonBox.StandardButton.Help).clicked.connect(self.show_help_question)

        # Connect the left menu to the right panel
        self.dlg.mOptionsListWidget.currentRowChanged.connect(self.dlg.mOptionsStackedWidget.setCurrentIndex)

        # Abstract HTML editor
        self.dlg.button_abstract_html.setIcon(QIcon(":images/themes/default/mActionEditHtml.svg"))
        self.dlg.button_abstract_html.clicked.connect(self.configure_html_abstract)

        # Group wizard
        icon = load_icon('user_group.svg')
        self.dlg.button_wizard_group_visibility_project.setText('')
        self.dlg.button_wizard_group_visibility_layer.setText('')
        self.dlg.button_wizard_group_visibility_project.setIcon(icon)
        self.dlg.button_wizard_group_visibility_layer.setIcon(icon)
        self.dlg.button_wizard_group_visibility_project.clicked.connect(self.open_wizard_group_project)
        self.dlg.button_wizard_group_visibility_layer.clicked.connect(self.open_wizard_group_layer)
        tooltip = tr("Open the group wizard")
        self.dlg.button_wizard_group_visibility_project.setToolTip(tooltip)
        self.dlg.button_wizard_group_visibility_layer.setToolTip(tooltip)

        # DXF export group wizard
        self.dlg.button_dxf_wizard_group.setText('')
        self.dlg.button_dxf_wizard_group.setIcon(icon)
        self.dlg.button_dxf_wizard_group.clicked.connect(self.open_wizard_group_dxf)
        self.dlg.button_dxf_wizard_group.setToolTip(tr("Open the group wizard for DXF export"))

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
        self.dataviz_mngr.set_options(self.global_options)

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

                # Handle DXF Export separately - it uses a simplified table without dialogs
                if key == 'dxfExport':
                    manager = TableManagerDxfExport(item['tableWidget'])
                    item['manager'] = manager
                    # Hide all buttons - DXF export is auto-populated from WFS layers
                    for button_key in ['addButton', 'removeButton', 'editButton', 'upButton', 'downButton']:
                        if item.get(button_key):
                            item[button_key].setVisible(False)

                    # Connect global checkbox to enable/disable table and populate if needed
                    def on_dxf_export_toggled(checked):
                        if checked:
                            # Enable table
                            manager.table.setEnabled(True)
                            # Only populate if table is currently empty
                            # (avoid overwriting loaded config values)
                            if manager.table.rowCount() == 0:
                                manager.populate_from_project()
                        else:
                            # Disable table but keep the data (preserve user settings)
                            manager.table.setEnabled(False)

                    # Disconnect any existing connections to avoid multiple connections
                    # when dialog is reused between sessions
                    with contextlib.suppress(TypeError):
                        # No connections exist yet
                        self.dlg.checkbox_dxf_export_enabled.toggled.disconnect()

                    self.dlg.checkbox_dxf_export_enabled.toggled.connect(on_dxf_export_toggled)
                    continue

                item['tableWidget'].horizontalHeader().setStretchLastSection(True)

                if key == 'datavizLayers':
                    self.dataviz_mngr.init_gui(item)
                if key == 'layouts':
                    definition = LayoutsDefinitions()
                    dialog = LayoutEditionDialog
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
                    if key == 'atlas':
                        definition = AtlasDefinitions()
                        dialog = AtlasEditionDialog
                    elif key == 'attributeLayers':
                        definition = AttributeTableDefinitions()
                        dialog = AttributeTableEditionDialog
                    elif key == 'editionLayers':
                        definition = EditionDefinitions()
                        dialog = EditionLayerDialog
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

        self.layer_tree_mngr.init_gui()

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
        self.layer_tree_mngr.enable_popup_source_button()

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

    def open_wizard_group_dxf(self):
        """ Open the group wizard for DXF export. """
        helper = tr("Setting groups allowed to export DXF files.")
        self._open_wizard_group(self.dlg.text_dxf_allowed_groups, helper)

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
                QMessageBox.StandardButton.Ok
            )
            return None
        # End of duplicated

        current_acl = line_edit.text()
        wizard_dialog = WizardGroupDialog(helper, current_acl, acl['groups'])
        if not wizard_dialog.exec():
            return None

        text = wizard_dialog.preview.text()
        if not text:
            return

        line_edit.setText(text)

    def show_help_question(self):
        helpers.show_help_question(self.dlg)

    def enable_check_box_in_layer_tab(self, value: bool):
        self.layer_tree_mngr.enable_check_box_in_layer_tab(value)

    def reset_scales(self):
        """ Reset scales in the line edit. """
        scales = ', '.join([str(i) for i in self.global_options['mapScales']['default']])
        if self.dlg.list_map_scales.text() != '':
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowIcon(window_icon() )
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            box.setWindowTitle(tr('Reset the scales'))
            box.setText(tr(
                'You have some scales predefined. Are you sure you want to reset with "{}" ?'
            ).format(scales))

            result = box.exec()
            if result == QMessageBox.StandardButton.No:
                return

        self.dlg.list_map_scales.setText(scales)
        self.get_min_max_scales()

    def get_min_max_scales(self):
        self.scale_mngr.get_min_max_scales()

    def read_cfg_file(self, skip_tables: bool = False) -> dict:
        """Get the saved configuration from the project.qgs.cfg config file.

        Populate the gui fields accordingly

        skip_tables is only used in tests, as we don't have "table managers". It's only for testing the "layer" panel.
        """
        json_options = {}
        json_file = self.dlg.cfg_file()
        if json_file.exists():
            with open(json_file, encoding='utf-8') as f:
                json_file_reader = f.read()

            try:
                sjson = json.loads(json_file_reader)
                json_options = sjson['options']
                for key in self.layers_table:
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

                        if key == 'dxfExport':
                            # Pass full sjson so manager can read from layers section
                            manager.load_wfs_layers(sjson)
                            continue

                        if key in sjson:
                            manager.from_json(sjson[key])
                        else:
                            # get a subset of the data to give to the table form
                            data = {k: json_options[k] for k in json_options if k.startswith(manager.definitions.key())}
                            if data:
                                manager.from_json(data)

                        if key == 'datavizLayers':
                            self.dataviz_mngr.read_cfg(sjson)

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
                    self.dlg, tr('Lizmap Error'), message, QMessageBox.StandardButton.Ok)
                self.dlg.log_panel.append(message, abort=True, style=Html.P)
                LOGGER.critical('Error while reading the Lizmap configuration file')

        else:
            LOGGER.info('Lizmap CFG does not exist for this project.')
            for key in self.layers_table:
                manager = self.layers_table[key].get('manager')
                if manager:
                    manager.truncate()

        # Set the global options (map, tools, etc.)
        for key, item in self.global_options.items():
            if item.get('widget'):
                if item.get('tooltip'):
                    item['widget'].setToolTip(item.get('tooltip'))

                if item['wType'] in ('checkbox', 'radio'):
                    # Block signals while setting values to avoid triggering actions during config load
                    item['widget'].blockSignals(True)
                    item['widget'].setChecked(item['default'])
                    if key in json_options:
                        item['widget'].setChecked(ambiguous_to_bool(json_options[key]))
                    item['widget'].blockSignals(False)

                if item['wType'] == 'scale':
                    item['widget'].setShowCurrentScaleButton(True)
                    item['widget'].setMapCanvas(self.iface.mapCanvas())
                    item['widget'].setAllowNull(False)
                    value = json_options.get(key)
                    if value:
                        item['widget'].setScale(value)
                    else:
                        item['widget'].setScale(item['default'])

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

            self.set_map_scales_in_ui(
                map_scales=map_scales,
                min_scale=min_scale,
                max_scale=max_scale,
                use_native=use_native,
                project_crs=project_crs,
            )

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

        # Set DXF export table enabled state based on global checkbox
        dxf_manager = self.layers_table.get('dxfExport', {}).get('manager')
        if dxf_manager:
            dxf_enabled = self.dlg.checkbox_dxf_export_enabled.isChecked()
            dxf_manager.table.setEnabled(dxf_enabled)

        out = '' if json_file.exists() else 'out'
        LOGGER.info(f'Dialog has been loaded successful, with{out} Lizmap configuration file')

        if self.project.fileName().lower().endswith('qgs'):
            # Manage lizmap_user project variable
            variables = self.project.customVariables()
            if 'lizmap_user' in variables and not self.dlg.check_cfg_file_exists() and not skip_tables:
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
                    self.dlg, tr('New Lizmap configuration'), message, QMessageBox.StandardButton.Ok)

            # Add default variables in the project
            if not variables.get('lizmap_user'):
                variables['lizmap_user'] = ''
            if not variables.get('lizmap_user_groups'):
                variables['lizmap_user_groups'] = list()
            self.project.setCustomVariables(variables)

        # Fill the layer tree
        data = self.populate_layer_tree()

        # Fill base-layer startup
        self.on_baselayer_checkbox_change()
        self.baselayers_mngr.set_startup_baselayer_from_config()
        self.dlg.default_lizmap_folder()

        # The return is used in tests
        return data

    def get_qgis_layer_by_id(self, my_id: str) -> Optional[QgsMapLayer]:
        """ Get a QgsMapLayer by its ID. """
        return self.layer_tree_mngr.get_qgis_layer_by_id(my_id)

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

    def layout_renamed(self, layout: QgsMasterLayoutInterface, new_name: str):
        """ When a layout has been renamed in the project. """
        if not self.dlg.check_cfg_file_exists():
            return

        self.layers_table['layouts']['manager'].layout_renamed(layout, new_name)

    def layout_removed(self, name: str):
        """ When a layout has been removed from the project. """
        if not self.dlg.check_cfg_file_exists():
            return

        self.layers_table['layouts']['manager'].layout_removed(name)

    def check_wfs_is_checked(self, layer: QgsVectorLayer) -> bool:
        """ Check if the layer is published as WFS. """
        if not is_layer_published_wfs(self.project, layer.id()):
            self.display_error(tr(
                'The layers you have chosen for this tool must be checked in the '
                '"WFS Capabilities" option of the '
                'QGIS Server tab in the "Project Properties" dialog.'))
            return False
        return True

    def display_error(self, message: str):
        helpers.display_error(self.dlg, message)

    def populate_layer_tree(self) -> Dict:
        return self.layer_tree_mngr.populate_layer_tree()

    def disable_legacy_empty_base_layer(self):
        self.layer_tree_mngr.disable_legacy_empty_base_layer()

    def _add_base_layer(
        self,
        source: str,
        name: str,
        attribution_url: Optional[str] = None,
        attribution_name: Optional[str] = None,
    ):
        self.layer_tree_mngr._add_base_layer(
            source,
            name,
            attribution_url,
            attribution_name,
        )

    def save_value_layer_group_data(self, key: str):
        self.layer_tree_mngr.save_value_layer_group_data(key)

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
                QMessageBox.StandardButton.Ok)

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
        if not html_editor.exec():
            return

        self.dlg.teLayerAbstract.setPlainText(html_editor.editor.html_content())

    def configure_html_popup(self):
        """Open the dialog with a text field to store the popup template for one layer/group"""
        # get the selected item in the layer tree
        layer_or_group = self._current_selected_item_in_config()
        if not layer_or_group:
            return

        # do nothing if no popup configured for this layer/group
        if not ambiguous_to_bool(self.layerList[layer_or_group]['popup']):
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
            if not popup_dialog.exec():
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
            if not html_editor.exec():
                return

            self._set_maptip(layer, html_editor.editor.html_content(), False)

    def _current_selected_item_in_config(self) -> Optional[str]:
        return self.layer_tree_mngr._current_selected_item_in_config()

    def _current_selected_layer(self) -> Optional[QgsMapLayer]:
        return self.layer_tree_mngr._current_selected_layer()

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
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowIcon(window_icon())
            box.setWindowTitle(tr('Existing maptip for layer {}').format(layer.title()))
            box.setText(tr(
                'A maptip already exists for this layer. This is going to override it. '
                'Are you sure you want to continue ?'))
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            result = box.exec()
            if result == QMessageBox.StandardButton.No:
                return False

        layer.setMapTipTemplate(html_content)
        QMessageBox.information(
            self.dlg,
            tr('Maptip'),
            tr('The maptip has been set in the layer "{}".').format(layer.name()),
            QMessageBox.StandardButton.Ok
        )
        self.dock_html_preview.update_html()
        return True

    def html_table_from_layer(self):
        """ Button set popup maptip from layer in the Lizmap configuration. """
        layer = self._current_selected_layer()
        if not isinstance(layer, QgsVectorLayer):
            return

        html_maptip_dialog = HtmlMapTipDialog(layer)
        if not html_maptip_dialog.exec():
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
        if config.layout() != QgsEditFormConfig.EditorLayout.TabLayout:
            LOGGER.warning('Maptip : the layer is not using a drag and drop form.')
            QMessageBox.warning(
                self.dlg,
                tr('Lizmap - Warning'),
                tr('The form for this layer is not a drag and drop layout.'),
                QMessageBox.StandardButton.Ok)
            return

        root = config.invisibleRootContainer()
        relation_manager = self.project.relationManager()
        html_content = Tooltip.create_popup_node_item_from_form(
            layer, root, 0, [], '', relation_manager,
            bootstrap_5=self.lwc_version >= LwcVersions.Lizmap_3_9,
        )
        html_content = Tooltip.create_popup(html_content)

        server_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)
        versions = ServerManager.split_lizmap_version(server_metadata['info']['version'])
        if versions[0:2] <= (3, 7):
            # LWC 3.7.X and older
            html_content += Tooltip.css()
        elif (3, 8, 0) <= versions[0:3] <= (3, 8, 7):
            # LWC 3.8.0 to 3.8.6
            html_content += Tooltip.css_3_8_6()

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
            tr('Copied'), tr('Your versions have been copied in your clipboard.'), level=Qgis.MessageLevel.Success)

    def check_project_clicked(self):
        """ Launch the check on the current project. """
        lwc_version = self.lwc_version
        # Let's trigger UI refresh according to latest releases, if it wasn't available on startup
        self.lwc_version_changed()
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            self.check_project(lwc_version)

    def check_project(
        self,
        lwc_version: LwcVersions,
        with_gui: bool = True,
        check_server: bool = True,
        ignore_error: bool = False,
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
        LOGGER.info(f"Project has been detected : {'VALID' if valid else 'NOT valid'} according to OGC validation.")
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
            if as_boolean(use_layer_id):
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
                self.dlg.log_panel.append("<em>" + tr("A leading or a trailing spaces can be added.") + "</em>")
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
                    ), Html.P, level=Qgis.MessageLevel.Critical)
                else:
                    self.dlg.log_panel.append(tr(
                        "The process is continuing but these layers might be invisible if the server is not well "
                        "configured or if the project is not correctly uploaded to the server."
                    ), Html.P)

        if check_server:

            if lizmap_cloud:
                error, _message = check_project_ssl_postgis(self.project)
                for layer in error:
                    self.dlg.check_results.add_error(
                        Error(
                            layer.name,
                            checks.SSLConnection,
                            source_type=SourceLayer(layer.name, layer.layer_id),
                        )
                    )
                    self.dlg.enabled_ssl_button(True)

            autogenerated_keys, not_int4 = project_invalid_pk(self.project)
            for layer in autogenerated_keys:
                self.dlg.check_results.add_error(
                    Error(
                        layer.name,
                        checks.MissingPk,
                        source_type=SourceLayer(layer.name, layer.layer_id),
                    )
                )
            for layer in not_int4:
                self.dlg.check_results.add_error(
                    Error(
                        layer.name,
                        checks.NotInt4Pk,
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

            # if lwc_version >= LwcVersions.Lizmap_3_7:
            #     # Temporary disabled, I think there are some valid use cases for this for now.
            #     results = duplicated_layer_with_filter_legend(self.project)
            #     if results:
            #         self.dlg.log_panel.append(checks.DuplicatedLayerFilterLegend.title, Html.H2)
            #         self.dlg.log_panel.start_table()
            #         self.dlg.log_panel.append(
            #             "<tr><th>{}</th><th>{}</th><th>{}</th></tr>".format(
            #                 tr('Datasource'), tr('Filters'), tr('Layers'))
            #         )
            #         for i, result in enumerate(results):
            #             for uri, filters in result.items():
            #                 self.dlg.log_panel.add_row(i)
            #                 self.dlg.log_panel.append(uri, Html.Td)
            #
            #                 # Icon
            #                 for k, v in filters.items():
            #                     if k == "_wkb_type":
            #                         icon = QgsIconUtils.iconForWkbType(v)
            #                         break
            #                 else:
            #                     icon = QIcon(':/images/themes/default/algorithms/mAlgorithmMergeLayers.svg')
            #
            #                 del filters["_wkb_type"]
            #
            #                 uri_filter = '<ul>' + ''.join([f"<li>{k}</li>" for k in filters.keys()]) + '</ul>'
            #                 self.dlg.log_panel.append(uri_filter, Html.Td)
            #
            #                 layer_names = '<ul>' + ''.join([f"<li>{k}</li>" for k in filters.values()]) + '</ul>'
            #                 self.dlg.log_panel.append(layer_names, Html.Td)
            #
            #                 self.dlg.log_panel.end_row()
            #
            #                 self.dlg.check_results.add_error(
            #                     Error(
            #                         uri,
            #                         checks.DuplicatedLayerFilterLegend,
            #                     ),
            #                     icon=icon,
            #                 )
            #
            #         self.dlg.log_panel.end_table()
            #
            #         self.dlg.log_panel.append(tr(
            #             'Checkboxes are supported natively in the legend. Using filters for the same '
            #             'datasource are highly discouraged.'
            #         ), style=Html.P)

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
        for key in self.layers_table:
            manager: TableManager = self.layers_table[key].get('manager')
            if manager:
                for layer_id, fields in manager.wfs_fields_used().items():
                    if layer_id not in data:
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

        if not self.dlg.mOptionsListWidget.item(Panels.Training).isHidden():
            # Make the life easier a little bit for short workshops.
            project_trust_layer_metadata(self.project, True)
        elif not project_trust_layer_metadata(self.project):
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
                min_required_version = qgis_version_info(min_required_version, increase_odd_number=False)
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
            self.dlg.out_log.moveCursor(QTextCursor.MoveOperation.Start)
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
                Qgis.MessageLevel.Critical,
            )

            return False

        important_issues = self.dlg.check_results.has_importants()
        if important_issues >= 1 and lizmap_cloud:
            base_name = self.project.baseName()
            dialog = ConfirmationTextMessageBox(important_issues, f"{base_name}:{important_issues}")
            result = dialog.exec()
            self.dlg.log_panel.append(tr(
                "{count} error(s) have been found on the project, user has agreed with these errors : {result}"
            ).format(count=important_issues, result="<strong>" + tr("Yes") + "<strong>" if result else tr("No")), Html.P)
            if not result:
                return False

        return True

    def project_config_file(
        self,
        lwc_version: LwcVersions,
        with_gui: bool = True,
        check_server: bool = True,
        ignore_error: bool = False,
    ) -> Optional[Dict]:
        """ Get the JSON CFG content. """

        if lwc_version >= LwcVersions.Lizmap_3_6:
            LOGGER.info(f"Update project OGC validity for LWC version {lwc_version.value}")
            # Set shortnames if it's not set
            ogc_projet_validity = OgcProjectValidity(self.project)
            ogc_projet_validity.add_shortnames()
            ogc_projet_validity.set_project_short_name()

            validator = QgsProjectServerValidator()
            valid, _results = validator.validate(self.project)
            LOGGER.info(f"Project has been detected : {'VALID' if valid else 'NOT valid'} according to OGC validation.")

        if not self.check_project(lwc_version, with_gui, check_server, ignore_error):
            # Some blocking issues, we can not continue
            return None

        server_metadata = self.dlg.server_combo.currentData(ServerComboData.JsonMetadata.value)

        LOGGER.info(f"Writing Lizmap configuration file for LWC version {lwc_version.value}")
        current_version = self.global_options['metadata']['lizmap_plugin_version']['default']
        if self.is_dev_version:
            next_version = next_git_tag()
            if next_version != 'next':
                current_version = next_version

        target_status = self.dlg.server_combo.currentData(ServerComboData.LwcBranchStatus.value)
        if not target_status:
            target_status = ReleaseStatus.Unknown

        if is_lizmap_cloud(server_metadata):
            eol = (ReleaseStatus.Retired, ReleaseStatus.SecurityBugfixOnly)
            if self.dlg.current_server_info(ServerComboData.LwcBranchStatus.value) in eol:
                if self.dlg.current_server_info(ServerComboData.LwcBranchStatus.value) == ReleaseStatus.Retired:
                    msg = tr(
                        'This version of Lizmap Web Client is now <strong>not supported anymore</strong>.'
                    )
                else:
                    msg = tr(
                        'This version of Lizmap Web Client is <strong>nearly not supported anymore</strong>. '
                        'It is in <strong>security bugfix mode only</strong>, it means only critical bugfix are fixed '
                        'and soon the branch will be declared <strong>not maintained</strong>.'
                    )
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
                    + msg
                    + "<br><br>"
                    + "<strong>"
                    + tr(
                        'Please visit your administration panel in your web browser, in the dashboard, and '
                        'ask for the update.'
                    )
                    + "</strong>"
                    + "<br><br>"
                    + tr(
                        'You might have some old project which need an update from you. The list is written on the '
                        'dashboard. Projects are not deleted during the update of Lizmap Web Client, '
                        'they will be only invisible on the main landing page until they are updated by you.'
                    )
                    + "<br><br>"
                    + tr('This is not blocking your current usage of the plugin, only to advise you.'),
                    QMessageBox.StandardButton.Ok
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
                        'anymore by QGIS.org since {month_and_year}, see the '
                        '<a href="https://www.qgis.org/en/site/getinvolved/development/roadmap.html#release-schedule">'
                        'QGIS roadmap'
                        '</a>.'
                    ).format(
                        month_and_year=tr("February 2024"),  # About QGIS 3.28
                    )
                    + "<br><br>"
                    + tr(
                        'Please visit your administration panel in your web browser, in the dashboard, and '
                        'ask for the update.'
                    )
                    + "<br><br>"
                    + tr('This is not blocking your current usage of the plugin, only to advise you.'),
                    QMessageBox.StandardButton.Ok
                )

        metadata = {
            'qgis_desktop_version': Qgis.versionInt(),
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

        # GUI user defined options
        for key, item in self.global_options.items():
            if item.get('widget'):
                input_value = None
                # Get field value depending on widget type
                if item['wType'] == 'text':
                    input_value = item['widget'].text().strip(' \t')

                if item['wType'] == 'scale':
                    input_value = item['widget'].scale()
                    if input_value == item['default']:
                        # Only save if different from the default value
                        continue

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
                    if not ambiguous_to_bool(input_value):
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

        for key in self.layers_table:
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
                        with contextlib.suppress(KeyError):
                            del liz2json['options']['print']
                    else:
                        # We do not want to save this table if it's less than LWC 3.7
                        LOGGER.info("Skipping the 'layout' table because version is less than LWC 3.7")
                        continue

                if key == 'dxfExport':
                    # Store DXF export data to be processed during layer building loop
                    # This avoids trying to write to liz2json['layers'] before layers are added
                    continue

                if manager.use_single_row() and manager.table.rowCount() == 1:
                    liz2json['options'].update(data)
                else:
                    liz2json[key] = data

        # Drag drop dataviz designer
        if self.drag_drop_dataviz:
            # In tests, we don't have the variable set
            liz2json['options']['dataviz_drag_drop'] = self.drag_drop_dataviz.to_json()

        base_layers_group = LayerTreeManager.existing_group(
            self.project.layerTreeRoot(),
            GroupNames.BaseLayers,
        )

        if base_layers_group:
            base_layers_group: QgsLayerTreeGroup
            base_layers_group.setIsMutuallyExclusive(True, -1)

            default_background_color_index = LayerTreeManager.existing_group(
                base_layers_group,
                GroupNames.BackgroundColor,
                index=True,
            )

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

        # Get DXF export data to apply during layer building
        # Always get the data if table has content, regardless of global enable state
        # This preserves user settings when they temporarily disable DXF export globally
        dxf_layer_settings = {}
        dxf_manager = self.layers_table.get('dxfExport', {}).get('manager')
        if dxf_manager:
            dxf_data = dxf_manager.to_json()
            # Build map from layer ID to enabled status
            for layer_config in dxf_data.get('layers', []):
                layer_id = layer_config.get('layerId')
                enabled = layer_config.get('enabled', True)
                if layer_id:
                    dxf_layer_settings[layer_id] = enabled

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
                if layer and layer.type() == QgsMapLayer.LayerType.VectorLayer:  # if it is a vector layer:
                    geometry_type = layer.geometryType()

            # geometry type
            if geometry_type != -1:
                layer_options["geometryType"] = MappingQgisGeometryType[layer.geometryType()]

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
                        if 33600 <= Qgis.versionInt() < 33603:
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
                elif val['type'] in ('boolean', 'radio'):
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
            if cached and not ambiguous_to_bool(cached):
                del layer_options['cacheExpiration']

            # unset clientCacheExpiration if not needed
            client_cache = layer_options.get('clientCacheExpiration')
            if client_cache and client_cache < 0:
                del layer_options['clientCacheExpiration']

            # unset externalWms if False
            external_wms = layer_options.get('externalWmsToggle')
            if external_wms and not ambiguous_to_bool(external_wms):
                del layer_options['externalWmsToggle']

            # unset source project and repository if needed
            source_repository = layer_options.get('sourceRepository')
            source_project = layer_options.get('sourceProject')
            if not source_repository or not source_project:
                del layer_options['sourceRepository']
                del layer_options['sourceProject']

            # set popupSource to auto if set to lizmap and no lizmap conf found
            if ambiguous_to_bool(layer_options['popup']) and layer_options['popupSource'] == 'lizmap' \
                    and layer_options['popupTemplate'] == '':
                layer_options['popupSource'] = 'auto'

            if layer_options.get("geometryType") in ('point', 'line', 'polygon'):
                if layer_options.get('popupSource') == 'lizmap' and ambiguous_to_bool(layer_options.get('popup')):
                    QMessageBox.warning(
                        self.dlg,
                        tr('Deprecated feature'),
                        tr(
                            'The layer "{}" is vector layer and the popup is a "Lizmap HTML". This kind of popup is '
                            'deprecated for vector layer, you should switch to another kind of popup, for instance to '
                            'a "QGIS HTML maptip". This will be removed in a future version of Lizmap.'
                        ).format(layer_options["name"]),
                        QMessageBox.StandardButton.Ok
                    )

            # Add external WMS options if needed
            if isinstance(layer, QgsMapLayer) and as_boolean(layer_options.get('externalWmsToggle')):
                # Only for layers stored in disk
                if layer.providerType() == 'wms':
                    wms_params = get_layer_wms_parameters(layer)
                    if wms_params:
                        layer_options['externalAccess'] = wms_params
                    else:
                        layer_options['externalWmsToggle'] = str(False)
                else:
                    layer_options['externalWmsToggle'] = str(False)

            layer_options.pop('serverFrame', None)

            layer_options.pop('popupFrame', None)

            # Add DXF export setting if applicable
            # Write settings regardless of global enable state to preserve user choices
            if k in dxf_layer_settings:
                # Only add if this layer is published as WFS
                if is_layer_published_wfs(self.project, k):
                    layer_options['dxfExportEnabled'] = dxf_layer_settings[k]

            # Add layer options to the json object
            liz2json["layers"][v['name']] = layer_options

        return liz2json

    def map_scales(self) -> list:
        return self.scale_mngr.map_scales()

    def minimum_scale_value(self) -> int:
        return self.scale_mngr.minimum_scale_value()

    def maximum_scale_value(self) -> int:
        return self.scale_mngr.maximum_scale_value()

    def set_map_scales_in_ui(
        self,
        *,
        map_scales: list,
        min_scale: int,
        max_scale: int,
        use_native: bool,
        project_crs: str,
    ):
        self.scale_mngr.set_map_scales_in_ui(
            map_scales=map_scales,
            min_scale=min_scale,
            max_scale=max_scale,
            use_native=use_native,
            project_crs=project_crs,
        )

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
            self.iface.messageBar().pushMessage('Lizmap', message, level=Qgis.MessageLevel.Warning, duration=DURATION_WARNING_BAR)

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
        if ambiguous_to_bool(self.project.readEntry('Paths', 'Absolute')[0]):
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
            # Convenient option for users, for new CFG file only : project trust, and add geometry to GetFeatureInfo
            project_trust_layer_metadata(self.project, True)
            self.project.writeEntryBool('WMSAddWktGeometry', '/', True)

            new_project = NewConfigDialog()
            new_project.exec()

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result = self.save_cfg_file()

        if not result:
            # Generation failed, error message without closing the dialog
            # noinspection PyUnresolvedReferences
            self.dlg.display_message_bar(
                'Lizmap',
                tr('An error occurred while generating the projet, please check logs'),
                level=Qgis.MessageLevel.Critical,
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
                level=Qgis.MessageLevel.Success,
                duration=DURATION_SUCCESS_BAR,
            )
            return

        if auto_send:
            # noinspection PyUnresolvedReferences
            self.dlg.display_message_bar(
                'Lizmap',
                tr('Project <a href="{}">published !</a>'.format(url)),
                level=Qgis.MessageLevel.Success,
                duration=DURATION_SUCCESS_BAR,
            )
            return

        self.dlg.display_message_bar(
            'Lizmap',
            tr('Project file generated, but the upload has failed'),
            level=Qgis.MessageLevel.Warning,
            duration=DURATION_SUCCESS_BAR,
        )

    def save_cfg_file(
        self,
        lwc_version: Optional[LwcVersions] = None,
        # TODO find better semantic
        save_project: Optional[bool] = None,
        # FIXME seems to be redondant with save_project == None
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
            lwc_version = self.lwc_version
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
            qgis_group = LayerTreeManager.existing_group(
                self.project.layerTreeRoot(),
                GroupNames.BaseLayers,
            )
            if qgis_group and self.lwc_version >= LwcVersions.Lizmap_3_7:
                self.disable_legacy_empty_base_layer()

        if self.version_checker:
            # Maybe running from CLI tools about the version_checker object
            self.version_checker.check_outdated_version(lwc_version, with_gui=with_gui)

        if not self.check_dialog_validity():
            LOGGER.debug("Leaving the dialog without valid project and/or server.")
            self.dlg.log_panel.append(tr("No project or server"), Html.H2)
            self.dlg.log_panel.append(
                tr('Either you do not have a server reachable for a long time or you do not have a project opened.'),
                level=Qgis.MessageLevel.Warning,
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
                    ), QMessageBox.StandardButton.Ok)
                return False

        # global project option checking
        is_valid, message = self.check_global_project_options()
        if not is_valid:
            QMessageBox.critical(
                self.dlg, tr('Lizmap Error'), '{}\n\n{}'.format(message, stop_process), QMessageBox.StandardButton.Ok)
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
                    level=Qgis.MessageLevel.Warning,
                    duration=DURATION_WARNING_BAR
                )

        if not auto_save:
            # noinspection PyUnresolvedReferences
            self.iface.messageBar().pushMessage(
                'Lizmap',
                msg,
                level=Qgis.MessageLevel.Success,
                duration=DURATION_MESSAGE_BAR
            )
            # No automatic saving, the process is finished
            return True

        return True

    def send_files(self) -> Tuple[bool, str]:
        """ Send both files to the server, designed for UI interaction.

        With a waiting cursor and sending messages to the message bar.
        """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
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
        dialog.exec()
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

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            qgis_exists, error = self.webdav.check_exists_qgs()
        if error:
            self.iface.messageBar().pushMessage('Lizmap', error, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR)
            return False, '', ''

        server = self.dlg.server_combo.currentData(ServerComboData.ServerUrl.value)
        if not qgis_exists:
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Icon.Question)
            box.setWindowIcon(window_icon() )
            box.setWindowTitle(tr('The project is not published yet'))
            box.setText(tr(
                'The project <b>"{}"</b> does not exist yet on the server <br>'
                '<b>"{}"</b> '
                'in the folder <b>"{}"</b>.'
                '<br><br>'
                'Do you want to publish it for the first time in this directory ?'
            ).format(
                self.project.baseName(), server, folder))
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            result = box.exec()
            if result == QMessageBox.StandardButton.No:
                return False, '', ''

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            flag, error, url = self.webdav.send_all_project_files()
        if not flag:
            # Error while sending files
            LOGGER.error(error)
            self.iface.messageBar().pushMessage('Lizmap', error, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR)
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

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, msg = self.webdav.file_stats_media()
        if result is not None:
            self.dlg.display_message_bar(
                'Lizmap',
                tr('The "media" directory was already existing on the server. Please check with a file browser.'),
                level=Qgis.MessageLevel.Info,
                duration=DURATION_WARNING_BAR,
                more_details=msg,
            )
            return

        box = QMessageBox(self.dlg)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowIcon(window_icon() )
        box.setWindowTitle(tr('Create "media" directory on the server'))
        box.setText(tr(
            'Are you sure you want to create the "media" directory on the server <strong>{server}</strong> in the '
            'Lizmap repository <strong>{name}</strong> ?'
        ).format(
            server=self.dlg.server_combo.currentText(),
            name=self.dlg.repository_combo.currentText()
        ))
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        result = box.exec()
        if result == QMessageBox.StandardButton.No:
            return

        directory += 'media/'
        result, msg = self.webdav.make_dir(directory)
        if not result and msg:
            self.dlg.display_message_bar('Lizmap', msg, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR)
            return

        self.dlg.display_message_bar(
            'Lizmap',
            tr('The "media" directory has been created'), level=Qgis.MessageLevel.Success, duration=DURATION_WARNING_BAR)

    def create_media_dir_local(self):
        """ Create the local "media" directory. """
        media = Path(self.project.fileName()).parent.joinpath('media')
        media.mkdir(exist_ok=True)
        self.dlg.display_message_bar(
            'Lizmap',
            tr('The local <a href="file://{}">"media"</a> directory has been created').format(media),
            level=Qgis.MessageLevel.Success,
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
                level=Qgis.MessageLevel.Critical,
                duration=DURATION_WARNING_BAR
            )
            return

        current_file = Path(self.project.absolutePath()).joinpath(current_path)
        if not current_file.exists():
            self.dlg.display_message_bar(
                'Lizmap',
                tr('Path does not exist'),
                level=Qgis.MessageLevel.Critical,
                duration=DURATION_WARNING_BAR
            )
            return

        if not current_file.is_file():
            self.dlg.display_message_bar(
                'Lizmap',
                tr('Path is not a file'),
                level=Qgis.MessageLevel.Critical,
                duration=DURATION_WARNING_BAR
            )
            return

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, message = self.webdav.send_media(current_file)
        if not result and message:
            self.dlg.display_message_bar('Lizmap', message, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR)
            return

        msg = tr("File send")
        self.dlg.display_message_bar(
            'Lizmap',
            f'<a href="{self.webdav.media_url(current_path)}">{msg}</a>',
            level=Qgis.MessageLevel.Success,
            duration=DURATION_WARNING_BAR,
        )
        return

    def upload_thumbnail(self):
        """ Upload the thumbnail on the server. """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, message = self.webdav.send_thumbnail()
        if not result and message:
            self.dlg.display_message_bar('Lizmap', message, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR)
            return

        if result:
            box = QMessageBox(self.dlg)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowIcon(window_icon() )
            box.setWindowTitle(tr('Cache about the thumbnail'))
            box.setText(tr(
                'The upload of the thumbnail is successful. You can open it in your <a href="{}">web-browser</a>.'
                ).format(message) + '<br><br>'
                + tr(
                'However, you might have some cache in your web-browser, for the next {number} hours. You should do a '
                'CTRL + F5 (or CTRL + MAJ + R or similar) to force the refresh of the page without using the '
                'web-browser cache.'
            ).format(number=24))
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            box.setDefaultButton(QMessageBox.StandardButton.Ok)
            box.exec()

            file_stats, error = self.webdav.file_stats_thumbnail()
            if error:
                LOGGER.error(error)
                return
            self.dlg.set_tooltip_webdav(self.dlg.button_upload_thumbnail, file_stats.last_modified_pretty)
            self.dlg.line_thumbnail_date.setText(file_stats.last_modified_pretty)

    def upload_action(self):
        """ Upload the action file on the server. """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, error = self.webdav.send_action()
        if not result and error:
            self.dlg.display_message_bar('Lizmap', error, level=Qgis.MessageLevel.Critical, duration=DURATION_WARNING_BAR)
            return

        if result:
            self.dlg.display_message_bar(
                'Lizmap',
                tr('Upload of the action file is successful.'),
                level=Qgis.MessageLevel.Success,
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
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowIcon(window_icon() )
        box.setWindowTitle(tr('Remove a remote file'))
        box.setText(tr('Are you sure you want to remove the remote file ?'))
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        result = box.exec()
        return result == QMessageBox.StandardButton.No

    def remove_remote_file(self, button: QPushButton):
        """ Remove a remote file. """
        if self._question_remove_remote_file():
            return
        with OverrideCursor(Qt.CursorShape.WaitCursor):
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

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            for row in range(self.dlg.table_files.rowCount()):
                self.refresh_single_layer(row)

    def send_all_layers(self):
        """ Send all layers from the table on the server. """
        for row in range(self.dlg.table_files.rowCount()):
            self.dlg.table_files.file_status(row, tr("Work in progress"), tr("Work in progress"))

        with OverrideCursor(Qt.CursorShape.WaitCursor):
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
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            directory = self.dlg.current_repository()
            self.dlg.line_cfg_date.setText("")
            result, error = self.webdav.file_stats_cfg()
            if result:
                self.dlg.line_cfg_date.setText(f"{result.last_modified_pretty} : {human_size(result.content_length)}")
            elif result is None and not error:
                self.dlg.line_cfg_date.setText(tr(
                    "Project {name} not found in {folder}").format(name=self.project.baseName(), folder=directory))
            else:
                self.dlg.line_cfg_date.setText(error)

    def _refresh_thumbnail(self):
        """ Refresh thumbnail. """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            directory = self.dlg.current_repository()
            self.dlg.line_thumbnail_date.setText("")
            result, error = self.webdav.file_stats_thumbnail()
            if result:
                self.dlg.line_thumbnail_date.setText(f"{result.last_modified_pretty} : {human_size(result.content_length)}")
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
        with OverrideCursor(Qt.CursorShape.WaitCursor):
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
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            result, error = self.webdav.file_stats_media()
            if result:
                self.dlg.line_media_date.setText(result.last_modified_pretty)
            else:
                self.dlg.line_media_date.setText(error)

    def check_latest_update_webdav(self):
        """ Check the latest date about QGS file on the server. """
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            self.dlg.line_qgs_date.setText("")
            result, error = self.webdav.file_stats_qgs()
            if result:
                url = self.webdav.project_url()
                self.dlg.webdav_last_update.setText(f'<a href="{url}">{result.last_modified_pretty}</a>')
                self.dlg.webdav_last_update.setOpenExternalLinks(True)
                self.dlg.set_tooltip_webdav(self.dlg.button_upload_webdav, result.last_modified_pretty)
                self.dlg.line_qgs_date.setText(f"{result.last_modified_pretty} : {human_size(result.content_length)}")
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
        current_version = self.lwc_version
        self.dlg.refresh_helper_target_version(current_version)
        self.lwc_version_changed()

    def on_single_wms_toggled(self, checked: bool):
        """
        Enable or disable the exclude basemaps checkbox based on single WMS state.
        The exclude option only makes sense when single WMS is enabled.
        """
        self.dlg.checkbox_exclude_basemaps_from_single_wms.setEnabled(checked)

    def on_baselayer_checkbox_change(self):
        blist = self.baselayers_mngr.on_baselayer_checkbox_change(self.layerList)
        # Fill self.globalOptions
        self.global_options['startupBaselayer']['list'] = blist

    def reinit_default_properties(self):
        for key in self.layers_table:
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

        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_html_preview)
        self.dock_html_preview.setVisible(True)

    def check_training_panel(self):
        self.training_mngr.check_training_panel()

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

        self.dlg.exec()
        return True
