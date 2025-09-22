__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from pathlib import Path
from typing import Optional

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsFieldProxyModel,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsSettings,
)
from qgis.gui import QgsFeaturePickerWidget
from qgis.PyQt.QtCore import QSize, Qt, QUrl
from qgis.PyQt.QtGui import (
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QImageReader,
    QPixmap,
)
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
)
from qgis.utils import OverrideCursor, iface

from lizmap.definitions.lizmap_cloud import (
    CLOUD_MAX_PARENT_FOLDER,
    CLOUD_NAME,
    UPLOAD_EXTENSIONS,
    UPLOAD_MAX_SIZE,
)
from lizmap.definitions.qgis_settings import Settings
from lizmap.log_panel import LogPanel
from lizmap.plausible import Plausible
from lizmap.project_checker_tools import (
    ALLOW_PARENT_FOLDER,
    FORCE_LOCAL_FOLDER,
    FORCE_PG_USER_PASS,
    PREVENT_AUTH_DB,
    PREVENT_ECW,
    PREVENT_OTHER_DRIVE,
    PREVENT_SERVICE,
    project_trust_layer_metadata,
    simplify_provider_side,
    use_estimated_metadata,
)
from lizmap.saas import fix_ssl, is_lizmap_cloud
from lizmap.table_manager.upload_files import TableFilesManager
from lizmap.widgets.check_project import Checks, Headers, TableCheck

try:
    from qgis.PyQt.QtWebKitWidgets import QWebView
    WEBKIT_AVAILABLE = True
except ModuleNotFoundError:
    WEBKIT_AVAILABLE = False

from lizmap.definitions.definitions import (
    LwcVersions,
    RepositoryComboData,
    ServerComboData,
)
from lizmap.definitions.online_help import (
    Panels,
    online_lwc_help,
    pg_service_help,
    qgis_theme_help,
)
from lizmap.qt_style_sheets import COMPLETE_STYLE_SHEET
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.layer import relative_path
from lizmap.toolbelt.resources import load_ui, resources_path
from lizmap.toolbelt.strings import human_size
from lizmap.toolbelt.version import format_qgis_version, qgis_version

FORM_CLASS = load_ui('ui_lizmap.ui')
LOGGER = logging.getLogger("Lizmap")


class LizmapDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None, is_dev_version=True, lwc_version: LwcVersions = None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)
        self.project = QgsProject.instance()

        # Should only be used in tests
        self._lwc_version = lwc_version

        self.mOptionsStackedWidget.currentChanged.connect(self.panel_changed)
        self.plausible = Plausible(self)

        self.is_dev_version = is_dev_version

        self.label_lizmap_logo.setText('')
        pixmap = QPixmap(resources_path('icons', 'logo.png'))
        # noinspection PyUnresolvedReferences
        pixmap = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio)
        self.label_lizmap_logo.setPixmap(pixmap)

        # Initial extent widget
        self.widget_initial_extent.setMapCanvas(iface.mapCanvas(), False)
        self.widget_initial_extent.setOutputCrs(self.project.crs())
        self.widget_initial_extent.setOriginalExtent(iface.mapCanvas().extent(), self.project.crs())
        self.project.crsChanged.connect(self.project_crs_changed)

        if WEBKIT_AVAILABLE:
            self.dataviz_viewer = QWebView()
        else:
            self.dataviz_viewer = QLabel(tr('You must install Qt Webkit to enable this feature.'))
        self.html_content.layout().addWidget(self.dataviz_viewer)

        self.dataviz_feature_picker = QgsFeaturePickerWidget()

        self.feature_picker_layout.addWidget(self.dataviz_feature_picker)
        self.feature_picker_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.warning_old_server.setVisible(False)

        # Make them hidden until we have the changelog URL
        self.lwc_version_latest_changelog.setVisible(False)
        self.lwc_version_oldest_changelog.setVisible(False)

        welcome = (self.add_first_server, self.publish_first_map)
        for button in welcome:
            button.setMinimumSize(QSize(1, 40))
        self.publish_first_map.setIcon(QIcon(":/images/themes/default/mActionSharingExport.svg"))
        self.publish_first_map.setToolTip(tr('Open the online how-to for publishing a project'))
        self.publish_first_map.clicked.connect(self.open_lizmap_how_to)
        self.add_first_server.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.add_first_server.setToolTip(tr('Add a new server in the list'))

        for widget in (self.label_current_lwc_label, self.label_current_lwc):
            widget.setToolTip(tr(
                'The plugin is using this version for the User Interface (blue background) and when saving the Lizmap '
                'configuration file.'
            ))

        self.label_general_help.setText(
            tr("The plugin is doing some checks on your project.") + " "
            + tr(
                "To know how to fix these checks, either use the tooltip (by hovering your mouse pointer on the table "
                "row) in the last column <strong>'{column_name}'</strong>, or check the documentation in the next tab "
                "<strong>'{tab_name}'</strong> for all errors which can be reported."
            ).format(column_name=Headers().error.label, tab_name=self.tab_log.tabText(1))
        )
        auto_fix_panel = self.mOptionsListWidget.item(Panels.AutoFix).text()
        self.label_autofix.setText(tr(
            "An auto-fix is available in the '{tab_name}' panel"
        ).format(tab_name=auto_fix_panel))
        self.push_visit_settings.setText(tr("Visit the '{tab_name}' panel").format(tab_name=auto_fix_panel))
        self.push_visit_settings.clicked.connect(self.visit_settings_panel)
        self.push_visit_settings.setIcon(QIcon(":/images/themes/default/console/iconSettingsConsole.svg"))
        self.label_check_resume.setVisible(False)
        self.label_autofix.setVisible(False)
        self.push_visit_settings.setVisible(False)

        # Filtering features
        self.tab_filtering.setCurrentIndex(0)

        self.helper_list_group.setReadOnly(True)
        self.button_helper_group.setToolTip(tr('Select features having at least one group not matching on the server'))
        self.button_helper_group.clicked.connect(self.select_unknown_features_group)
        self.button_helper_group.setIcon(QIcon(":images/themes/default/mActionToggleSelectedLayers.svg"))
        self.helper_layer_group.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)
        tooltip = tr("The layer to check group IDs")
        self.helper_layer_group.setToolTip(tooltip)
        self.helper_field_group.setFilters(QgsFieldProxyModel.Filter.String)
        self.helper_field_group.setLayer(self.helper_layer_group.currentLayer())
        self.label_helper_layer_group.setToolTip(tooltip)
        tooltip = tr("The field which must contains group IDs")
        self.helper_field_group.setToolTip(tooltip)
        self.helper_layer_group.layerChanged.connect(self.helper_field_group.setLayer)
        self.label_helper_field_group.setToolTip(tooltip)

        icon = QgsApplication.getThemeIcon("mActionToggleSelectedLayers.svg")
        self.preview_attribute_filtering.setIcon(icon)
        self.preview_attribute_filtering.setText("")
        self.preview_attribute_filtering.setToolTip(tr("To have a preview of the attribute filtering tool"))
        self.preview_attribute_filtering.setVisible(False)
        # self.preview_attribute_filtering.clicked.connect(self.open_filter_preview)

        # IGN and google
        self.inIgnKey.textChanged.connect(self.check_ign_french_free_key)
        self.inIgnKey.textChanged.connect(self.check_api_key_address)
        self.inGoogleKey.textChanged.connect(self.check_api_key_address)

        # Layer tree
        self.layer_tree.headerItem().setText(0, tr('List of layers'))
        self.help_map_theme.setIcon(QIcon(":/images/themes/default/mActionHelpContents.svg"))
        self.help_map_theme.setText("")
        self.help_map_theme.clicked.connect(self.open_theme_help)
        self.activate_first_map_theme.toggled.connect(self.follow_map_theme_toggled)

        tooltip = tr(
            'You can add either a URL starting by "http" or insert a string starting by "media/", "../media/" to '
            'insert a link to a media stored in the Lizmap instance.')
        self.label_link.setToolTip(tooltip)
        self.inLayerLink.setToolTip(tooltip)

        self.automatic_permalink.setToolTip(tr(
            "On every pan, zoom, toggle of a layer, the permalink can be automatically updated in the URL."))

        self.use_native_scales.setToolTip(tr(
            "It's recommended, for instance on EPSG:3857, text on an external tile will have a better rendering."
        ))

        self.help_lizmap_features_table.setText("")
        self.help_lizmap_features_table.setIcon(QIcon(":/images/themes/default/mActionHelpContents.svg"))
        self.help_lizmap_features_table.clicked.connect(self.open_lizmap_features_table_help)

        self.log_panel = LogPanel(self.out_log)
        self.button_clear_log.setIcon(QIcon(":images/themes/default/console/iconClearConsole.svg"))
        self.button_clear_log.clicked.connect(self.log_panel.clear)

        self.button_refresh_action.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.button_refresh_action.setText('')
        self.button_refresh_action.setToolTip(tr('Refresh action detection'))
        self.button_refresh_action.clicked.connect(self.check_action_file_exists)

        self.button_refresh_thumbnail.setIcon(QIcon(QgsApplication.iconPath('mActionRefresh.svg')))
        self.button_refresh_thumbnail.setText('')
        self.button_refresh_thumbnail.setToolTip(tr('Refresh thumbnail detection'))
        self.button_refresh_thumbnail.clicked.connect(self.check_project_thumbnail)
        self.check_project_thumbnail()
        self.check_action_file_exists()
        self.setup_icons()

        # Fixer tools
        self.fixer_project_label.setText(tr(
            'These tools can fix your current loaded layers in <b>this project only</b>. '
            'You still need to update your connection or default settings in your QGIS global settings, to be be '
            'applied automatically for new project or newly added layer.'))
        self.enable_all_fixer_buttons(False)

        self.button_convert_ssl.clicked.connect(self.fix_project_ssl)
        self.button_convert_ssl.setIcon(QIcon(":images/themes/default/mIconPostgis.svg"))

        self.button_use_estimated_md.clicked.connect(self.fix_project_estimated_md)
        self.button_use_estimated_md.setIcon(QIcon(":images/themes/default/mIconPostgis.svg"))

        self.button_trust_project.clicked.connect(self.fix_project_trust)
        self.button_trust_project.setIcon(QIcon(':/images/themes/default/mIconQgsProjectFile.svg'))

        self.button_simplify_geom.clicked.connect(self.fix_simplify_geom_provider)
        self.button_simplify_geom.setIcon(QIcon(":images/themes/default/mIconPostgis.svg"))

        self.buttonBox.button(QDialogButtonBox.StandardButton.Help).setToolTip(tr(
            'Open the help in the web-browser'
        ))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setToolTip(tr(
            'The Lizmap configuration file is generated and the dialog is closed, except if there is at least one '
            'blocking check.'
        ))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setToolTip(tr(
            'The Lizmap configuration file is not generated and the dialog is closed.'
        ))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setToolTip(tr(
            'The Lizmap configuration file is generated, but the dialog stays opened.'
        ))
        self.checkbox_save_project.setToolTip(tr(
            'When ever you click on "Apply" or "Ok" for saving the Lizmap configuration file, the QGS file can be '
            'saved as well if necessary'
        ))

        self.warning_base_layer_deprecated.set_text(tr(
            "You are using a version equal or higher than Lizmap Web Client 3.7 on this server, this panel "
            "<strong>below</strong> is now deprecated."
        ))

        self.widget_deprecated_popup.set_text(tr(
            "This source of popup is deprecated for vector layer. You should switch to another one, such as the QGIS "
            "HTML maptip which is the more powerful. This popup will be removed later for vector layer."
        ))

        text = tr(
            "Actions in Lizmap Web Client are similar to <a href=\"{}\">Actions in QGIS</a> but it's using a custom "
            "format and not the dedicated tab in the vector layer properties dialog. For now, creating an action "
            "requires manual editing of the action configuration file named below. "
            "Please check the <a href=\"{}\">Lizmap documentation</a>. There is the 'Feature' scope."
        ).format(
            "https://docs.qgis.org/latest/en/docs/user_manual/working_with_vector/vector_properties.html#"
            "actions-properties",
            online_lwc_help('publish/lizmap_plugin/actions.html').url()
        )
        self.label_help_action.setText(text)
        self.label_demo_action.setText(tr(
            "See the <a href=\"{}\">online demo</a> for an example, using actions in the 'Feature' scope."
        ).format(
            "https://demo.lizmap.com/lizmap/index.php/view/map?repository=features&project=fire_hydrant_actions"))
        self.label_file_action.setOpenExternalLinks(True)

        self.radio_beginner.setToolTip(tr(
            'If one safeguard is not OK, the Lizmap configuration file is not going to be generated.'
        ))
        self.radio_normal.setToolTip(tr(
            'If one safeguard is not OK, only a warning will be displayed, not blocking the saving of the Lizmap '
            'configuration file.'
        ))

        self.radio_force_local_folder.setText(FORCE_LOCAL_FOLDER)
        self.radio_force_local_folder.setToolTip(tr(
            'Files must be located in {folder} or in a sub directory.'
        ).format(folder=self.project.homePath()))
        self.radio_allow_parent_folder.setText(ALLOW_PARENT_FOLDER)
        self.radio_allow_parent_folder.setToolTip(tr(
            'Files can be located in a parent folder from {folder}, up to the setting below.'
        ).format(folder=self.project.homePath()))

        self.help_pg_service.setText("")
        self.help_pg_service.setIcon(QIcon(":/images/themes/default/mActionHelpContents.svg"))
        self.help_pg_service.clicked.connect(self.open_pg_service_help)
        self.safe_other_drive.setText(PREVENT_OTHER_DRIVE)
        self.safe_pg_service.setText(PREVENT_SERVICE)
        self.safe_pg_auth_db.setText(PREVENT_AUTH_DB)
        self.safe_pg_user_password.setText(FORCE_PG_USER_PASS)
        self.safe_ecw.setText(PREVENT_ECW)

        # Normal / beginner
        self.radio_normal.setChecked(
            not QgsSettings().value(Settings.key(Settings.BeginnerMode), type=bool))
        self.radio_beginner.setChecked(
            QgsSettings().value(Settings.key(Settings.BeginnerMode), type=bool))
        self.radio_normal.toggled.connect(self.radio_mode_normal_toggled)
        self.radio_normal.toggled.connect(self.save_settings)
        self.radio_mode_normal_toggled()

        # Parent or subdirectory
        self.radio_force_local_folder.setChecked(
            not QgsSettings().value(Settings.key(Settings.AllowParentFolder), type=bool))
        self.radio_allow_parent_folder.setChecked(
            QgsSettings().value(Settings.key(Settings.AllowParentFolder), type=bool))
        self.radio_allow_parent_folder.toggled.connect(self.radio_parent_folder_toggled)
        self.radio_allow_parent_folder.toggled.connect(self.save_settings)
        self.radio_parent_folder_toggled()

        # Number
        self.safe_number_parent.setValue(QgsSettings().value(Settings.key(Settings.NumberParentFolder), type=int))
        self.safe_number_parent.valueChanged.connect(self.save_settings)

        self.checks = Checks()

        # Other drive
        self.safe_other_drive.setChecked(QgsSettings().value(Settings.key(Settings.PreventDrive), type=bool))
        self.safe_other_drive.toggled.connect(self.save_settings)
        self.safe_other_drive.setToolTip(self.checks.PreventDrive.description)

        # PG Service
        self.safe_pg_service.setChecked(QgsSettings().value(Settings.key(Settings.PreventPgService), type=bool))
        self.safe_pg_service.toggled.connect(self.save_settings)
        self.safe_pg_service.setToolTip(self.checks.PgService.description)

        # PG Auth DB
        self.safe_pg_auth_db.setChecked(QgsSettings().value(Settings.key(Settings.PreventPgAuthDb), type=bool))
        self.safe_pg_auth_db.toggled.connect(self.save_settings)
        self.safe_pg_auth_db.setToolTip(self.checks.AuthenticationDb.description)

        # User password
        self.safe_pg_user_password.setChecked(QgsSettings().value(Settings.key(Settings.ForcePgUserPass), type=bool))
        self.safe_pg_user_password.toggled.connect(self.save_settings)
        self.safe_pg_user_password.setToolTip(self.checks.PgForceUserPass.description)

        # ECW
        self.safe_ecw.setChecked(QgsSettings().value(Settings.key(Settings.PreventEcw), type=bool))
        self.safe_ecw.toggled.connect(self.save_settings)
        self.safe_ecw.setToolTip(self.checks.PreventEcw.description)

        msg = tr(
            "Some safeguards are overridden by {host}. Even in 'normal' mode, some safeguards are becoming 'blocking' "
            "with a {host} instance.").format(host=CLOUD_NAME)
        msg += (
            '<ul>'
            '<li>{max_parent}</li>'
            '<li>{network}</li>'
            '<li>{auth_db}</li>'
            '<li>{user_pass}</li>'
            '<li>{ecw}</li>'
            '</ul>'.format(
                max_parent=tr("Maximum of parent folder {max_number} : {example}").format(
                    max_number=CLOUD_MAX_PARENT_FOLDER, example=relative_path(CLOUD_MAX_PARENT_FOLDER)),
                network=PREVENT_OTHER_DRIVE,
                auth_db=PREVENT_AUTH_DB,
                user_pass=FORCE_PG_USER_PASS,
                ecw=PREVENT_ECW,
            )
        )
        self.label_safe_lizmap_cloud.setText(msg)

        self.export_summary_table.clicked.connect(self.copy_clip_board_summary_table)

        self.button_run_checks.setIcon(QIcon(":/images/themes/default/mActionStart.svg"))
        buttons = (
            self.export_summary_table,
            self.button_copy,
        )
        copy_icon = QIcon(":images/themes/default/mActionEditCopy.svg")
        for button in buttons:
            button.setIcon(copy_icon)

        self.mOptionsListWidget.item(Panels.Upload).setHidden(True)
        self.mOptionsListWidget.item(Panels.Training).setHidden(True)
        self.label_upload_path.setText(tr(
            "Only files located in the <strong>current QGS file directory (or in a sub-directory)</strong>, "
            "having a file weight less than <strong>{}</strong> and having extensions <strong>{}</strong> are "
            "supported.").format(
                human_size(UPLOAD_MAX_SIZE), ', '.join(UPLOAD_EXTENSIONS)
            )
        )
        self.label_upload_path.setWordWrap(True)
        self.label_current_folder.setText("")
        self.table_checks.setup()
        self.table_files.setup()
        self.table_files_manager = TableFilesManager(self, self.table_files, self.button_refresh_local_files)

        css_path = resources_path('css', 'log.css')
        with open(css_path, encoding='utf8') as f:
            css = f.read()
        self.html_help.document().setDefaultStyleSheet(css)

    @property
    def check_results(self) -> TableCheck:
        return self.table_checks

    def project_crs_changed(self):
        """ When the project CRS has changed.   """
        self.widget_initial_extent.setOutputCrs(self.project.crs())
        # TODO, check with the previous CRS in the Lizmap configuration
        # if iface:
        #     iface.messageBar().pushMessage(
        #         'Lizmap',
        #         tr(
        #             'The project CRS has changed. Do not forget to regenerate the Lizmap configuration file about '
        #             'your initial extent.'
        #         ),
        #         level=Qgis.Warning,
        #     )

    def open_lizmap_features_table_help(self):
        """ Open Lizmap-Features-Table helper."""
        QMessageBox.information(
            self,
            'Lizmap-Features-Table',
            tr('For now, to use this new behavior, it is needed to enable the layer in the "Attribute table" tool as well.')
            + "<br><br>"
            + tr(
                'Soon, it will not be necessary to enable the attribute table tool on the children layer. Hopefully,'
                'it will be done in 3.9.1.'
            )
            + "<br><br>"
            + tr(
                'For more advanced features about lizmap-features-table, it\'s possible to customize it more, add some virtual columns based on QGIS expressions,'
                'by adding the HTML manually in the parent layer maptip, from the '
                '<a href="https://docs.3liz.org/lizmap-web-client/js/module-FeaturesTable.html">documentation</a>. '
                'But with using this radio button, it is not needed to add extra HTML.'
            ),
            QMessageBox.StandardButton.Ok
        )

    @staticmethod
    def open_theme_help():
        """ Open the QGIS theme documentation. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(qgis_theme_help())

    @staticmethod
    def open_pg_service_help():
        """ Open the PG service documentation. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(pg_service_help())

    @staticmethod
    def open_lizmap_how_to():
        """ Open the how-to on Lizmap. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(online_lwc_help("publish/quick_start/index.html"))

    @staticmethod
    def open_workshop_edition():
        """ Open the Editing workshop. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(QUrl("https://docs.3liz.org/workshop/workshop/"))

    @staticmethod
    def set_tooltip_webdav(button: QPushButton, date: str = None):
        """ Set tooltip about the upload on the WebDAV server. """
        msg = tr('Upload on the server')
        if date:
            msg += '\n' + tr('Last update is {date}').format(date=date)
        button.setToolTip(msg)

    def check_api_key_address(self):
        """ Check the API key is provided for the address search bar. """
        # Before, IGN was requiring a key
        # With the new Geoplateforme, it seems the key is not required anymore, the code below has been simplified.
        provider = self.liExternalSearch.currentData()
        if provider not in ('google', ):
            return

        provider = 'Google'
        key = self.inGoogleKey.text()

        if key:
            return

        QMessageBox.critical(
            self,
            tr('Address provider'),
            tr('You have selected "{}" for the address search bar.').format(provider)
            + "\n\n"
            + tr(
                'However, you have not provided any API key for this provider. Please add one in the '
                '"Basemaps" panel to use this provider.'
            ),
            QMessageBox.StandardButton.Ok
        )

    def block_signals_address(self, flag: bool):
        """Block or not signals when reading the CFG to avoid the message box."""
        # https://github.com/3liz/lizmap-plugin/issues/477
        # When reading the CFG file, the address provider is set, before the key field is filled.
        # The signal is too early
        self.inIgnKey.blockSignals(flag)
        self.inGoogleKey.blockSignals(flag)
        self.liExternalSearch.blockSignals(flag)

    def check_ign_french_free_key(self):
        """ French IGN free API keys choisirgeoportail/pratique do not include all layers. """
        key = self.inIgnKey.text()
        if not key:
            self.cbIgnTerrain.setEnabled(False)
            self.cbIgnTerrain.setChecked(False)
        else:
            self.cbIgnTerrain.setEnabled(True)

    def visit_settings_panel(self):
        """ Go to settings panel. """
        self.mOptionsListWidget.setCurrentRow(Panels.AutoFix)

    def auto_fix_tooltip(self, lizmap_cloud):
        """ Set some tooltips on these auto-fix buttons, according to Lizmap Cloud status. """
        tooltip = self.checks.SSLConnection.html_tooltip(lizmap_cloud)
        self.label_pg_ssl.setToolTip(tooltip)
        self.button_convert_ssl.setToolTip(tooltip)

        tooltip = self.checks.EstimatedMetadata.html_tooltip(lizmap_cloud)
        self.label_pg_estimated.setToolTip(tooltip)
        self.button_use_estimated_md.setToolTip(tooltip)

        tooltip = self.checks.TrustProject.html_tooltip(lizmap_cloud)
        self.label_trust_project.setToolTip(tooltip)
        self.button_trust_project.setToolTip(tooltip)

        tooltip = self.checks.SimplifyGeometry.html_tooltip(lizmap_cloud)
        self.label_simplify.setToolTip(tooltip)
        self.button_simplify_geom.setToolTip(tooltip)

    def has_auto_fix(self) -> bool:
        """ Return if an auto-fix is enabled. """
        return any([
            self.button_convert_ssl.isEnabled(),
            self.button_use_estimated_md.isEnabled(),
            self.button_trust_project.isEnabled(),
            self.button_simplify_geom.isEnabled(),
        ])

    def enabled_ssl_button(self, status: bool):
        """ Enable or not the button. """
        self.button_convert_ssl.setEnabled(status)

    def enabled_estimated_md_button(self, status: bool):
        """ Enable or not the button. """
        self.button_use_estimated_md.setEnabled(status)

    def enabled_trust_project(self, status: bool):
        """ Enable or not the button. """
        self.button_trust_project.setEnabled(status)

    def enabled_simplify_geom(self, status: bool):
        """ Enable or not the button. """
        self.button_simplify_geom.setEnabled(status)

    def enable_all_fixer_buttons(self, status: bool):
        """ Enable or disable all buttons about fixing the project. """
        self.enabled_ssl_button(status)
        self.enabled_estimated_md_button(status)
        self.enabled_trust_project(status)
        self.enabled_simplify_geom(status)

    def copy_clip_board_summary_table(self):
        """ Export the table as Markdown in the clipboard. """
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.table_checks.to_markdown_summarized())
        self.display_message_bar(
            tr('Copied'), tr('Your results have been copied in your clipboard.'), level=Qgis.MessageLevel.Success)

    def follow_map_theme_toggled(self):
        """ If the theme is loaded at startup, the UX is updated about the toggled checkbox and the legend option. """
        text = ". " + tr("Overridden by the map theme")

        # List of item data where we need to add the text suffix.
        items = ('expand_at_startup', 'hide_at_startup')

        if self.activate_first_map_theme.isChecked():
            # Layer toggled checkbox must be disabled
            self.cbToggled.setEnabled(False)

            # Some legend options are not used anymore, we add the suffix text
            for item in items:
                index = self.combo_legend_option.findData(item)

                current_text = self.combo_legend_option.itemText(index)
                if not current_text.endswith(text):
                    self.combo_legend_option.setItemText(index, current_text + text)

            # Change current text item if necessary
            if self.combo_legend_option.currentData() in items:
                current_text = self.combo_legend_option.currentText()
                if not current_text.endswith(text):
                    self.combo_legend_option.setCurrentText(current_text + text)

        else:
            # Layer toggled checkbox must be enabled
            self.cbToggled.setEnabled(True)

            # All legend options are used, we remove the suffix text
            for item in items:
                index = self.combo_legend_option.findData(item)

                current_text = self.combo_legend_option.itemText(index)
                if current_text.endswith(text):
                    self.combo_legend_option.setItemText(index, current_text.replace(text, ''))

            # Change current item if necessary
            if self.combo_legend_option.currentData() in items:
                current_text = self.combo_legend_option.currentText()
                if current_text.endswith(text):
                    self.combo_legend_option.setCurrentText(current_text.replace(text, ''))

    def check_qgis_version(self, message_bar=False, widget=False) -> bool:
        """ Compare QGIS desktop and server versions and display results if necessary. """
        self.warning_old_server.setVisible(False)

        current = format_qgis_version(qgis_version())
        qgis_desktop = (current[0], current[1])

        metadata = self.current_server_info(ServerComboData.JsonMetadata.value)
        try:
            qgis_server = metadata.get('qgis_server_info').get('metadata').get('version').split('.')
            qgis_server = (int(qgis_server[0]), int(qgis_server[1]))
        except AttributeError:
            # Maybe returning LWC 3.4 or LWC 3.5 without the server plugin
            return False

        if qgis_server >= qgis_desktop:
            # Alright
            return False

        title = tr('QGIS server version is lower than QGIS desktop version')
        LOGGER.error(title)

        description = tr('Your QGIS desktop is writing QGS project in the future compare to QGIS server.')

        qgis_server = '{}.{}'.format(qgis_server[0], qgis_server[1])
        qgis_desktop = '{}.{}'.format(qgis_desktop[0], qgis_desktop[1])

        if message_bar:
            more = tr('Current QGIS server selected : ')
            more += '<b>{}</b>'.format(qgis_server)
            more += "<br>"
            more += tr('Current QGIS desktop : ')
            more += '<b>{}</b>'.format(qgis_desktop)
            more += "<br><br>"
            more += tr('Your QGIS desktop is writing QGS project in the future compare to QGIS server.')
            more += "<br>"
            more += tr(
                'You are strongly encouraged to upgrade your QGIS server. You will have issues when your QGIS '
                'server {} will read your QGS project made with this version of QGIS desktop {}.'
            ).format(qgis_server, qgis_desktop)
            self.display_message_bar(title, description, Qgis.MessageLevel.Warning, more_details=more)

        if widget:
            self.warning_old_server.setVisible(True)
            message = description
            message += " "
            message += tr(
                "Either upgrade your QGIS Server {} or downgrade your QGIS Desktop {}, to have the same version."
            ).format(qgis_server, qgis_desktop)
            self.warning_old_server.set_text(message)

        return True

    def current_server_info(self, info: ServerComboData):
        """ Return the current LWC server information from the server combobox. """
        return self.server_combo.currentData(info)

    def current_lwc_version(self, default_value: bool = True) -> Optional[LwcVersions]:
        """ Return the current LWC version from the server combobox. """
        metadata = self.current_server_info(ServerComboData.JsonMetadata.value)
        # In tests, we might not have metadata in the combobox
        if metadata and metadata.get('info'):
            return LwcVersions.find_from_metadata(metadata)

        if not default_value:
            return None

        if self._lwc_version:
            return self._lwc_version

        return None

    def current_repository(self, role=RepositoryComboData.Id) -> str:
        """ Fetch the current directory on the server if available. """
        if not self.repository_combo.isVisible():
            return ''

        return self.repository_combo.currentData(role.value)

    def tooltip_server_combo(self, index: int):
        """ Set the tooltip for a given row in the server combo. """
        # This method must use itemData() as we are not the current selected server in the combobox.
        url = self.server_combo.itemData(index, ServerComboData.ServerUrl.value)
        metadata = self.server_combo.itemData(index, ServerComboData.JsonMetadata.value)
        if not metadata or not metadata.get('info'):
            self.server_combo.setItemData(index, tr('No metadata about this server'), Qt.ItemDataRole.ToolTipRole)
            return

        target_version = LwcVersions.find_from_metadata(metadata)
        if target_version:
            target_version = target_version.value
        else:
            target_version = tr('Unknown')

        msg = tr(
            '<b>URL</b> {}<br>'
            '<b>Target branch</b> {}'
        ).format(url, target_version)
        self.server_combo.setItemData(index, msg, Qt.ItemDataRole.ToolTipRole)

    def refresh_combo_repositories(self):
        """ Refresh the combobox about repositories. """
        # Set the default error message that could happen for the dataviz
        # TODO change to latest 3.6.X in a few months
        error = tr(
            "Your current version of the selected server doesn't support the plot preview. "
            "You must upgrade at least to Lizmap Web Client "
            "<a href=\"https://github.com/3liz/lizmap-web-client/releases/tag/3.6.1\">3.6.1</a>."
            "\n\n"
            "Upgrade to the latest 3.6.X available."
        )
        self.dataviz_error_message.setText(error)

        self.repository_combo.clear()

        current = self.current_server_info(ServerComboData.ServerUrl.value)
        if not current:
            return

        if not current.endswith('/'):
            current += '/'

        metadata = self.current_server_info(ServerComboData.JsonMetadata.value)
        if not metadata:
            self.repository_combo.setVisible(False)
            self.stacked_dataviz_preview.setCurrentWidget(self.error_content)
            return

        repositories = metadata.get("repositories")
        if repositories is None:
            self.repository_combo.setVisible(False)
            self.stacked_dataviz_preview.setCurrentWidget(self.error_content)
            return

        # At this stage, a more precise error message for the dataviz
        error = tr("You should select a plot to have the preview.")
        self.dataviz_error_message.setText(error)

        self.repository_combo.setVisible(True)
        self.stacked_dataviz_preview.setCurrentWidget(self.error_content)

        if len(repositories) == 0:
            # The list might be empty on the server
            self.repository_combo.setToolTip("There isn't repository on the server")
            return

        self.repository_combo.setToolTip("List of repositories found on the server")

        for repository_id, repository_data in repositories.items():
            self.repository_combo.addItem(repository_data['label'], repository_id)
            index = self.repository_combo.findData(repository_id)
            self.repository_combo.setItemData(
                index,
                "ID : {}<br>Path : {}".format(repository_id, repository_data['path']),
                Qt.ItemDataRole.ToolTipRole)
            self.repository_combo.setItemData(index, repository_data['path'], RepositoryComboData.Path.value)

        # Dirty hack to trigger webdav check in plugin.py
        # Because all folders have been set in the combobox and the webdav is checking for repositories...
        # Be careful of recursion call
        self.button_check_capabilities.click()

        self.default_lizmap_folder()

    def default_lizmap_folder(self):
        """ Make the default value for folder combobox. """
        if self.repository_combo.count() >= 1:
            # At least, make one selected
            self.repository_combo.setCurrentIndex(0)

        # Restore the previous value if possible
        previous = self.project.customVariables().get('lizmap_repository')
        if not previous:
            return

        index = self.repository_combo.findData(previous)
        if not index:
            return

        self.repository_combo.setCurrentIndex(index)

    def display_message_bar(
            self,
            title: str,
            message: str = None,
            level: Qgis.MessageLevel = Qgis.MessageLevel.Info,
            duration: int = None,
            more_details: str = None,
            open_logs: bool = False):
        """Display a message.

        :param title: Title of the message.
        :type title: basestring

        :param message: The message.
        :type message: basestring

        :param level: A QGIS error level.

        :param duration: Duration in second.
        :type duration: int

        :param open_logs: If we need to add a button for the log panel.
        :type open_logs: bool

        :param more_details: The message to display in the "More button".
        :type more_details: basestring
        """
        widget = self.message_bar.createMessage(title, message)

        if more_details or open_logs:
            # Adding the button
            button = QPushButton(widget)
            widget.layout().addWidget(button)

            if open_logs:
                button.setText(tr('Open log panel'))
                # noinspection PyUnresolvedReferences
                button.pressed.connect(
                    lambda: iface.openMessageLog())
            else:
                button.setText(tr('More details'))
                # noinspection PyUnresolvedReferences
                button.pressed.connect(
                    lambda: QMessageBox.information(None, title, more_details))

        if duration is None:
            duration = int(QgsSettings().value("qgis/messageTimeout", 5))

        if self.isVisible():
            self.message_bar.pushWidget(widget, level, duration)
        else:
            iface.messageBar().pushWidget(widget, level, duration)

    def setup_icons(self):
        """ Setup icons in the left menu. """
        self.mOptionsListWidget.setIconSize(QSize(20, 20))

        # If adding a new panel, all mOptionsListWidget.item(X) must be checked
        # definitions/online_help.py about mapping as well

        # Information
        # It must be the first tab, with index 0.
        icon = QIcon()
        icon.addFile(resources_path('icons', '03-metadata-white'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '03-metadata-dark'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.Information).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Information).setData(Qt.ItemDataRole.UserRole, 'info')

        # Map options
        icon = QIcon()
        icon.addFile(resources_path('icons', '15-baselayer-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '15-baselayer-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.MapOptions).setIcon(icon)
        self.mOptionsListWidget.item(Panels.MapOptions).setData(Qt.ItemDataRole.UserRole, 'map-options')

        # Layers
        icon = QIcon()
        icon.addFile(resources_path('icons', '02-switcher-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '02-switcher-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.Layers).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Layers).setData(Qt.ItemDataRole.UserRole, 'layers')

        # Base layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '02-switcher-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '02-switcher-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.Basemap).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Basemap).setData(Qt.ItemDataRole.UserRole, 'base-layers')

        # Attribute table
        icon = QIcon()
        icon.addFile(resources_path('icons', '11-attribute-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '11-attribute-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.AttributeTable).setIcon(icon)
        self.mOptionsListWidget.item(Panels.AttributeTable).setData(Qt.ItemDataRole.UserRole, 'attribute-table')

        # Layer editing
        icon = QIcon()
        icon.addFile(resources_path('icons', '10-edition-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '10-edition-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.Editing).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Editing).setData(Qt.ItemDataRole.UserRole, 'layer-editing')

        # Layouts
        icon = QIcon()
        icon.addFile(resources_path('icons', '08-print-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '08-print-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.Layouts).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Layouts).setData(Qt.ItemDataRole.UserRole, 'layouts')

        # Filter data with form
        icon = QIcon()
        icon.addFile(resources_path('icons', 'filter-icon-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', 'filter-icon-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.FormFiltering).setIcon(icon)
        self.mOptionsListWidget.item(Panels.FormFiltering).setData(Qt.ItemDataRole.UserRole, 'filter-data-form')

        # Dataviz
        icon = QIcon()
        icon.addFile(resources_path('icons', 'dataviz-icon-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', 'dataviz-icon-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.Dataviz).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Dataviz).setData(Qt.ItemDataRole.UserRole, 'dataviz')

        # Filter layer by user
        icon = QIcon()
        icon.addFile(resources_path('icons', '12-user-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '12-user-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.FilteredLayers).setIcon(icon)
        self.mOptionsListWidget.item(Panels.FilteredLayers).setData(Qt.ItemDataRole.UserRole, 'filter-data-user')

        # Actions
        icon = QIcon()
        icon.addFile(resources_path('icons', 'actions-white.svg'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', 'actions-dark.svg'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.Actions).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Actions).setData(Qt.ItemDataRole.UserRole, 'actions')

        # Time manager
        icon = QIcon()
        icon.addFile(resources_path('icons', '13-timemanager-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '13-timemanager-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.TimeManager).setIcon(icon)
        self.mOptionsListWidget.item(Panels.TimeManager).setData(Qt.ItemDataRole.UserRole, 'time-manager')

        # Atlas
        icon = QIcon()
        icon.addFile(resources_path('icons', 'atlas-icon-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', 'atlas-icon-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.Atlas).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Atlas).setData(Qt.ItemDataRole.UserRole, 'atlas')

        # Locate by layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '04-locate-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '04-locate-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.LocateByLayer).setIcon(icon)
        self.mOptionsListWidget.item(Panels.LocateByLayer).setData(Qt.ItemDataRole.UserRole, 'locate-by-layer')

        # Tooltip layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '16-tooltip-white.png'), mode=QIcon.Mode.Normal)
        icon.addFile(resources_path('icons', '16-tooltip-dark.png'), mode=QIcon.Mode.Selected)
        self.mOptionsListWidget.item(Panels.ToolTip).setIcon(icon)
        self.mOptionsListWidget.item(Panels.ToolTip).setData(Qt.ItemDataRole.UserRole, 'tooltip-layer')

        # Checks
        # noinspection PyCallByClass,PyArgumentList
        icon = QIcon(QIcon(':/geometrychecker/icons/geometrychecker.svg'))
        self.mOptionsListWidget.item(Panels.Checks).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Checks).setData(Qt.ItemDataRole.UserRole, 'log')

        # Auto-fix
        # noinspection PyCallByClass,PyArgumentList
        icon = QIcon(":images/themes/default/console/iconSettingsConsole.svg")
        self.mOptionsListWidget.item(Panels.AutoFix).setIcon(icon)
        self.mOptionsListWidget.item(Panels.AutoFix).setData(Qt.ItemDataRole.UserRole, 'auto-fix')

        # Settings
        # noinspection PyCallByClass,PyArgumentList
        icon = QIcon(":/images/themes/default/propertyicons/settings.svg")
        self.mOptionsListWidget.item(Panels.Settings).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Settings).setData(Qt.ItemDataRole.UserRole, 'settings')

        # Upload
        # noinspection PyCallByClass,PyArgumentList
        icon = QIcon(resources_path('icons', 'upload.svg'))
        self.mOptionsListWidget.item(Panels.Upload).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Upload).setData(Qt.ItemDataRole.UserRole, 'upload')

        # Upload
        # noinspection PyCallByClass,PyArgumentList
        icon = QIcon(resources_path('icons', 'abc-block.png'))
        self.mOptionsListWidget.item(Panels.Training).setIcon(icon)
        self.mOptionsListWidget.item(Panels.Training).setData(Qt.ItemDataRole.UserRole, 'training')

        # Set stylesheet for QGroupBox
        q_group_box = (
            self.gb_tree,
            self.panel_layer_all_settings,
            self.gb_project_thumbnail,
            self.gb_visibleTools,
            self.group_api_keys,
            self.gb_Scales,
            self.frame_layer_popup,
            self.gb_extent,
            self.gb_externalLayers,
            self.gb_generalOptions,
            self.gb_interface,
            self.gb_baselayersOptions,
            self.predefined_groups_legend,
            self.predefined_groups,
            self.predefined_baselayers,
            self.attribute_filtering,
            self.spatial_filtering,
            self.webdav_frame,
            self.group_settings,
            self.group_safeguards,
            # self.group_upload,
            self.group_local,
            self.group_remote,
            self.group_local_layers,
            self.group_project_status,
            self.group_links,
            self.group_box_max_scale_zoom,
        )
        for widget in q_group_box:
            widget.setStyleSheet(COMPLETE_STYLE_SHEET)

    def check_project_thumbnail(self):
        """ Check the project thumbnail and display the metadata. """
        tooltip = tr(
            "You can add a file named {}.qgs.EXTENSION with one of the following extension : jpg, jpeg, png, gif."
        ).format(self.project.baseName())
        tooltip += ' <br>'
        tooltip += tr('Lizmap Web Client 3.6 adds webp and avif formats.')
        tooltip += ' <br>'
        tooltip += tr('The width and height should be ideally 250x250px.') + ' '
        tooltip += tr('The size should be ideally less than 50 KB for JPG, 150KB for PNG.')
        tooltip += ' <br>'
        tooltip += tr('You can use this online tool to optimize the size of the picture :')
        tooltip += ' https://squoosh.app'
        self.label_project_thumbnail.setToolTip(tooltip)
        self.label_project_thumbnail.setOpenExternalLinks(True)

        folder = Path(self.project.fileName()).parent
        text = "<a href=\"file://{}\">".format(folder) + tr("No thumbnail detected.") + "</a>" + " "
        text += tr(
            "You can add one by reading the <a href='{}'>online documentation</a>."
        ).format(online_lwc_help("publish/configuration/project_thumbnail.html").toString())
        self.label_project_thumbnail.setText(text)

        if self.check_cfg_file_exists():
            thumbnail = self.thumbnail_file()
            if thumbnail:
                image_size = QImageReader(str(thumbnail)).size()
                if image_size.width() > 0 and image_size.height() > 0:
                    image_size = f"{image_size.width()}x{image_size.height()}px"
                else:
                    # Qt can not read image size for AVIF format
                    # See https://github.com/novomesk/qt-avif-image-plugin
                    image_size = tr("unknown size")
                self.label_project_thumbnail.setText(
                    tr("Thumbnail <a href=\"file://{}\">detected</a>, {}, {}").format(
                        thumbnail.parent,
                        image_size,
                        human_size(thumbnail.stat().st_size))
                )

    def thumbnail_file(self) -> Optional[Path]:
        """ Get filepath to the thumbnail if found. """
        # Check the project image
        # https://github.com/3liz/lizmap-web-client/blob/master/lizmap/modules/view/controllers/media.classic.php
        # Line 251
        images_types = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'avif']
        images_types.extend([f.upper() for f in images_types])
        for test_file in images_types:
            thumbnail = Path(f'{self.project.fileName()}.{test_file}')
            if thumbnail.exists():
                return thumbnail
        return None

    def cfg_file(self) -> Path:
        """ Return the path to the current CFG file. """
        return Path(self.project.fileName() + '.cfg')

    def check_cfg_file_exists(self) -> bool:
        """ Return boolean if a CFG file exists for the given project. """
        return self.cfg_file().exists()

    def action_file(self) -> Path:
        """ Return the path to the current action file. """
        return Path(self.project.fileName() + '.action')

    def check_action_file_exists(self) -> bool:
        """ Return boolean if an action file exists for the given project and update UI. """
        self.label_file_action.setText(
            tr("Configuration file") + " : <a href=\"file://{}\">".format(self.action_file().parent)
            + self.action_file().name + "</a>"
        )

        if self.action_file().is_file():
            self.label_file_action_found.setText('✔')
            return True

        self.label_file_action_found.setText("<strong>" + tr('Not found') + "</strong>")
        return False

    def radio_parent_folder_toggled(self):
        """ When the parent allowed folder radio is toggled. """
        parent_allowed = self.radio_allow_parent_folder.isChecked()
        widgets = (
            self.label_parent_folder,
            self.safe_number_parent,
        )
        for widget in widgets:
            widget.setEnabled(parent_allowed)

    def lizmap_cloud_instance(self):
        """ Check if the user has at least one Lizmap Cloud instance. """
        instances = []
        for row in range(self.server_combo.count()):
            metadata = self.server_combo.itemData(row, ServerComboData.JsonMetadata.value)
            instances.append(is_lizmap_cloud(metadata))

        # Widgets disabled if the user doesn't have at least one Lizmap Cloud instance
        widgets = (
            # These rules are hard coded
            # Other rules depends on the user.
            self.safe_ecw,
            self.safe_other_drive,
            self.safe_pg_auth_db,
            self.safe_pg_user_password,
        )
        for widget in widgets:
            widget.setVisible(not all(instances))

        # Widgets enabled if at least one Lizmap Cloud instance
        widgets = (
            self.label_pg_ssl,
            self.button_convert_ssl,
        )
        for widget in widgets:
            widget.setVisible(any(instances))

        # We hard code only if ALL instances are Lizmap Cloud
        if all(instances):
            if self.safe_number_parent.value() > CLOUD_MAX_PARENT_FOLDER:
                self.safe_number_parent.setValue(CLOUD_MAX_PARENT_FOLDER)
            self.safe_number_parent.setMaximum(CLOUD_MAX_PARENT_FOLDER)
        else:
            self.safe_number_parent.setMaximum(1000)

    def radio_mode_normal_toggled(self):
        """ When the beginner/normal radio are toggled. """
        is_normal = self.radio_normal.isChecked()
        widgets = (
            self.group_file_layer,
            self.safe_number_parent,
            self.safe_other_drive,
            self.safe_pg_service,
            self.help_pg_service,
            self.safe_pg_auth_db,
            self.safe_pg_user_password,
            self.safe_ecw,
            self.label_parent_folder,
            self.label_explanations_safest,
        )
        for widget in widgets:
            widget.setEnabled(is_normal)
            widget.setVisible(is_normal)

    def safeguards_to_markdown(self) -> str:
        """ Export the list of safeguards to markdown. """
        text = '<details>\n'
        text += '<summary>List of safeguards :</summary>\n'
        text += '<br/>\n'
        text += '* Mode : {}<br/>\n'.format('normal' if self.radio_normal.isChecked() else 'safe')
        text += '* Allow parent folder : {}<br/>\n'.format('yes' if self.radio_allow_parent_folder.isChecked() else 'no')
        if self.radio_allow_parent_folder.isChecked():
            text += '* Number of parent : {} folder(s)<br/>\n'.format(self.safe_number_parent.value())
        text += '* Prevent other drive : {}<br/>\n'.format('yes' if self.safe_other_drive.isChecked() else 'no')
        text += '* Prevent PG service : {}<br/>\n'.format('yes' if self.safe_pg_service.isChecked() else 'no')
        text += '* Prevent PG Auth DB : {}<br/>\n'.format('yes' if self.safe_pg_auth_db.isChecked() else 'no')
        text += '* Force PG user&pass : {}<br/>\n'.format('yes' if self.safe_pg_user_password.isChecked() else 'no')
        text += '* Prevent ECW : {}<br/>\n'.format('yes' if self.safe_ecw.isChecked() else 'no')
        text += '</details>\n'
        return text

    def save_settings(self):
        """ Save settings checkboxes. """
        QgsSettings().setValue(Settings.key(Settings.BeginnerMode), not self.radio_normal.isChecked())
        QgsSettings().setValue(Settings.key(Settings.AllowParentFolder), self.radio_allow_parent_folder.isChecked())
        QgsSettings().setValue(Settings.key(Settings.NumberParentFolder), self.safe_number_parent.value())
        QgsSettings().setValue(Settings.key(Settings.PreventDrive), self.safe_other_drive.isChecked())
        QgsSettings().setValue(Settings.key(Settings.PreventPgService), self.safe_pg_service.isChecked())
        QgsSettings().setValue(Settings.key(Settings.PreventPgAuthDb), self.safe_pg_auth_db.isChecked())
        QgsSettings().setValue(Settings.key(Settings.ForcePgUserPass), self.safe_pg_user_password.isChecked())
        QgsSettings().setValue(Settings.key(Settings.PreventEcw), self.safe_ecw.isChecked())

    def allow_navigation(self, allow_navigation: bool, message: str = ''):
        """ Allow the navigation or not in the UI. """
        for i in range(0, self.mOptionsListWidget.count()):

            item = self.mOptionsListWidget.item(i)

            if i in (Panels.Information, Panels.Settings, Panels.Training):
                # These panels are always accessible
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
                continue

            if allow_navigation:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
            else:
                item.setFlags(item.flags() & ~ Qt.ItemFlag.ItemIsEnabled)

        if allow_navigation:
            self.label_warning_project.setVisible(False)
            self.label_warning_project.set_text('')
        else:
            self.label_warning_project.setVisible(True)
            self.label_warning_project.set_text(message)

        if not allow_navigation:
            self.refresh_helper_target_version(None)

    def refresh_helper_target_version(self, version=Optional[LwcVersions]):
        """ Refresh the helper about target version. """
        if not version:
            msg = tr('Unknown')
        else:
            msg = str(version.value)

        self.label_current_lwc.setText(f'<strong>{msg}</strong>')

    def panel_changed(self):
        """ When the panel on the right has changed. """
        self.plausible.request_stat_event()
        if self.mOptionsStackedWidget.currentWidget() == self.page_settings:
            self.lizmap_cloud_instance()

    def select_unknown_features_group(self):
        """ Select features where one group from the feature does not math one of the server. """
        groups = self.helper_list_group.text()
        if not groups:
            return

        layer = self.helper_layer_group.currentLayer()
        if not layer:
            return

        field = self.helper_field_group.currentField()
        if not field:
            return

        groups = ','.join(["'{}'".format(f) for f in groups.split(',')])
        expression = (
            "not("
            "  array_all("
            "    array({groups}),"
            "    string_to_array(\"{field}\")"
            "  )"
            ")"
        ).format(field=field, groups=groups)
        layer.removeSelection()
        LOGGER.debug("Expression used for checking groups not on the server :\n" + expression)
        layer.selectByExpression(expression)
        count = layer.selectedFeatureCount()
        self.display_message_bar(
            tr("Debug"),
            tr("{count} feature(s) having at least one group not on the server").format(
                count=count),
            Qgis.MessageLevel.Info if count >= 1 else Qgis.MessageLevel.Success
        )

    def fix_project_ssl(self):
        """ Fix the current project about SSL. """
        self.enabled_ssl_button(False)
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            count = fix_ssl(self.project, force=False)

        if count >= 2:
            msg = tr('{} layers updated').format(count)
        else:
            msg = tr('{} layer updated').format(count)
        self.display_message_bar("SSL", msg, Qgis.MessageLevel.Success)

    def fix_project_estimated_md(self):
        """ Fix the current project about estimated metadata. """
        self.enabled_estimated_md_button(False)
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            count = len(use_estimated_metadata(self.project, fix=True))

        if count >= 2:
            msg = tr('{} layers updated').format(count)
        else:
            msg = tr('{} layer updated').format(count)
        self.display_message_bar(tr("Estimated metadata"), msg, Qgis.MessageLevel.Success)

    def fix_project_trust(self):
        """ Fix the current project trust metadata. """
        self.enabled_trust_project(False)
        project_trust_layer_metadata(self.project, True)
        self.display_message_bar(tr("Trust project"), tr('Trust project is enabled'), Qgis.MessageLevel.Success)

    def fix_simplify_geom_provider(self):
        """ Fix the current layers simplify geom. """
        self.enabled_simplify_geom(False)
        with OverrideCursor(Qt.CursorShape.WaitCursor):
            count = len(simplify_provider_side(self.project, fix=True))

        if count >= 2:
            msg = tr('{} layers updated').format(count)
        else:
            msg = tr('{} layer updated').format(count)
        self.display_message_bar(tr("Simplify geometry on the provider side"), msg, Qgis.MessageLevel.Success)

    def activateWindow(self):
        """ When the dialog displayed, to trigger functions in the plugin when the dialog is opening. """
        self.check_project_thumbnail()
        self.check_action_file_exists()
        LOGGER.info("Opening the Lizmap dialog.")
        super().activateWindow()
