import contextlib
import json
import logging
import os
import tempfile

from functools import partial
from os.path import relpath
from pathlib import Path
from typing import (
    Dict,
    Optional,
)

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsEditFormConfig,
    QgsExpression,
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
    Qt,
    QTranslator,
)
from qgis.PyQt.QtGui import (
    QGuiApplication,
    QIcon,
)
from qgis.PyQt.QtWidgets import (
    QAction,
    QDialogButtonBox,
    QFileDialog,
    QLineEdit,
    QMessageBox,
)
from qgis.utils import OverrideCursor

from lizmap.config import LizmapConfig
from lizmap.definitions.atlas import AtlasDefinitions
from lizmap.definitions.attribute_table import AttributeTableDefinitions
from lizmap.definitions.definitions import (
    DURATION_SUCCESS_BAR,
    UNSTABLE_VERSION_PREFIX,
    LayerProperties,
    LwcVersions,
    ServerComboData,
)
from lizmap.definitions.edition import EditionDefinitions
from lizmap.definitions.filter_by_form import FilterByFormDefinitions
from lizmap.definitions.filter_by_login import FilterByLoginDefinitions
from lizmap.definitions.filter_by_polygon import FilterByPolygonDefinitions
from lizmap.definitions.layouts import LayoutsDefinitions
from lizmap.definitions.lizmap_cloud import (
    CLOUD_NAME,
)
from lizmap.definitions.locate_by_layer import LocateByLayerDefinitions
from lizmap.definitions.online_help import (
    Panels,
    online_cloud_help,
)
from lizmap.definitions.qgis_settings import Settings
from lizmap.definitions.time_manager import TimeManagerDefinitions
from lizmap.definitions.tooltip import ToolTipDefinitions
from lizmap.dialogs.dock_html_preview import HtmlPreview
from lizmap.dialogs.html_editor import HtmlEditorDialog
from lizmap.dialogs.html_maptip import HtmlMapTipDialog
from lizmap.dialogs.lizmap_popup import LizmapPopupDialog
from lizmap.dialogs.main import LizmapDialog
from lizmap.dialogs.news import NewConfigDialog
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
from lizmap.project_checker_tools import (  # duplicated_layer_with_filter_legend,
    project_trust_layer_metadata,
)
from lizmap.saas import is_lizmap_cloud
from lizmap.table_manager.base import TableManager
from lizmap.table_manager.dxf_export import TableManagerDxfExport
from lizmap.table_manager.layouts import TableManagerLayouts
from lizmap.widgets.project_tools import (
    is_layer_published_wfs,
)

try:
    from lizmap.plugin_manager import QgisPluginManager
    QGIS_PLUGIN_MANAGER = True
except ModuleNotFoundError:
    # In a standalone application
    QGIS_PLUGIN_MANAGER = False


from lizmap.qt_style_sheets import NEW_FEATURE_CSS
from lizmap.server_lwc import MAX_DAYS, ServerManager
from lizmap.toolbelt.convert import ambiguous_to_bool, as_boolean
from lizmap.toolbelt.custom_logging import (
    add_logging_handler_once,
    setup_logger,
)
from lizmap.toolbelt.git import current_git_hash, next_git_tag
from lizmap.toolbelt.i18n import setup_translation, tr
from lizmap.toolbelt.layer import (
    layer_property,
)
from lizmap.toolbelt.lizmap import convert_lizmap_popup
from lizmap.toolbelt.resources import (
    load_icon,
    plugin_name,
    plugin_path,
    window_icon,
)
from lizmap.toolbelt.version import (
    qgis_version_info,
    version,
)
from lizmap.tooltip import Tooltip
from lizmap.version_checker import VersionChecker

from . import helpers
from .baselayers import BaseLayersManager
from .config import ConfigFileManager
from .dataviz import DatavizManager
from .layer_tree import LayerTreeManager
from .lwc_versions import LwcVersionManager
from .options import global_options, layer_options
from .project import ProjectManager
from .scales import ScalesManager
from .settings import configure_qgis_settings
from .training import TrainingManager
from .webdav import WebDavManager

LOGGER = logging.getLogger(plugin_name())
VERSION_URL = 'https://raw.githubusercontent.com/3liz/lizmap-web-client/versions/versions.json'
# To try a local file
# VERSION_URL = 'file:///home/etienne/.local/share/QGIS/QGIS3/profiles/default/Lizmap/released_versions.json'


class Lizmap(
    BaseLayersManager,
    ConfigFileManager,
    LayerTreeManager,
    ScalesManager,
    TrainingManager,
    DatavizManager,
    LwcVersionManager,
    WebDavManager,
    ProjectManager,
):

    @property
    def lwc_version(self) -> LwcVersions:
        # From LwcVersionManager
        return self.current_lwc_version()

    @property
    def layerList(self) -> Dict:
        # From LayerTreeManager
        return self._layerList

    def __init__(self, iface: QgisInterface, lwc_version: LwcVersions = None):
        """Constructor of the Lizmap plugin."""
        LOGGER.info("Plugin starting")
        self.iface = iface
        # noinspection PyArgumentList
        self.project = QgsProject.instance()

        # Configure QGIS settings
        configure_qgis_settings()

        # Connect the current project filepath
        self.initialize_project_management()

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

        # Initialize global options
        self.global_options = global_options(self.dlg, lizmap_config)
        self.layer_options_list = layer_options(self.dlg, lizmap_config, self.global_options)

        # Must only be used in tests
        # In production, version is coming from the UI, according to the current server selected
        # In production, this variable must be None
        self.initialize_lwc_versions(lwc_version)

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
        # Connect single WMS checkbox to enable/disable the exclude basemaps option
        self.dlg.checkbox_wms_single_request_all_layers.toggled.connect(self.on_single_wms_toggled)
        self.on_single_wms_toggled(self.dlg.checkbox_wms_single_request_all_layers.isChecked())

        # Initialize layer tree
        self.initialize_layer_tree()

        # Initialize scales UI
        self.initialize_scales()

        # Initialize dataviz
        self.initialize_dataviz()

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

        self.dlg.button_check_capabilities.setToolTip(
            'If the server selected in this dropdown menu has not the correct version displayed under, or if some '
            'server capabilities is missing.'
        )
        self.dlg.button_check_capabilities.setText('')
        self.dlg.button_check_capabilities.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.dlg.button_check_capabilities.clicked.connect(self.check_server_capabilities)
        # self.dlg.button_open_project.clicked.connect(self.open_web_browser_project)

        self.initialize_webdav()

        # Base layers
        self.configure_base_layers()

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

        self.initialize_base_layers()

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
        self.initialize_training_dialog()

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
        # The new repository is only set when we save the CFG file
        # Otherwise, it will make a mess with the signals about the last repository used and the server refreshed list
        if self.dlg.page_dataviz.isVisible():
            self.layers_table['datavizLayers'].get('manager').preview_dataviz_dialog()

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
        self.set_dataviz_options(self.global_options)

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
                    self.dataviz_init_gui(item)
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

        self.layer_tree_init_gui()

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
