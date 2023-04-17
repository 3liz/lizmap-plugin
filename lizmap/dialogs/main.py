__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import sys

from qgis.core import Qgis, QgsApplication, QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QDialog,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QSpacerItem,
)

try:
    from qgis.PyQt.QtWebKitWidgets import QWebView
    WEBKIT_AVAILABLE = True
except ModuleNotFoundError:
    WEBKIT_AVAILABLE = False

from lizmap.definitions.definitions import LwcVersions, ServerComboData
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui, resources_path
from lizmap.qt_style_sheets import STYLESHEET
from lizmap.tools import format_qgis_version

FORM_CLASS = load_ui('ui_lizmap.ui')


class LizmapDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)
        self.project = QgsProject.instance()

        self.label_lizmap_logo.setText('')
        pixmap = QPixmap(resources_path('icons', 'logo.png'))
        # noinspection PyUnresolvedReferences
        pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio)
        self.label_lizmap_logo.setPixmap(pixmap)

        if WEBKIT_AVAILABLE:
            self.dataviz_viewer = QWebView()
        else:
            self.dataviz_viewer = QLabel(tr('You must install Qt Webkit to enable this feature.'))
        self.html_content.layout().addWidget(self.dataviz_viewer)

        if Qgis.QGIS_VERSION_INT >= 31400:
            from qgis.gui import QgsFeaturePickerWidget
            self.dataviz_feature_picker = QgsFeaturePickerWidget()
        else:
            self.dataviz_feature_picker = QLabel(tr("You must install QGIS 3.16 to enable the dataviz preview."))

        self.feature_picker_layout.addWidget(self.dataviz_feature_picker)
        self.feature_picker_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # IGN and google
        self.inIgnKey.textChanged.connect(self.check_ign_french_free_key)
        self.inIgnKey.textChanged.connect(self.check_api_key_address)
        self.inGoogleKey.textChanged.connect(self.check_api_key_address)

        # Layer tree
        self.layer_tree.headerItem().setText(0, tr('List of layers'))

        self.setup_icons()

    def check_api_key_address(self):
        """ Check the API key is provided for the address search bar. """
        provider = self.liExternalSearch.currentData()
        if provider in ('google', 'ign'):
            if provider == 'google':
                key = self.inGoogleKey.text()
            else:
                provider = 'IGN'
                key = self.inIgnKey.text()

            if not key:
                QMessageBox.critical(
                    self,
                    tr('Address provider'),
                    tr('You have selected "{}" for the address search bar.').format(provider)
                    + "\n\n"
                    + tr(
                        'However, you have not provided any API key for this provider. Please add one in the '
                        '"Basemaps" panel to use this provider.'
                    ),
                    QMessageBox.Ok
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

    def check_qgis_version(self):
        """ Compare QGIS desktop and server versions. """
        current = format_qgis_version(Qgis.QGIS_VERSION_INT)
        qgis_desktop = (current[0], current[1])

        metadata = self.server_combo.currentData(ServerComboData.JsonMetadata.value)
        try:
            qgis_server = metadata.get('qgis_server_info').get('metadata').get('version').split('.')
            qgis_server = (int(qgis_server[0]), int(qgis_server[1]))
        except AttributeError:
            # Maybe returning LWC 3.4 or LWC 3.5 without server plugin
            return

        if qgis_server < qgis_desktop:
            QMessageBox.warning(
                self,
                tr('QGIS server version is lower than QGIS desktop version'),
                tr('Current QGIS server selected : ')
                + '<b>{}.{}</b>'.format(qgis_server[0], qgis_server[1])
                + "<br>"
                + tr('Current QGIS desktop : ')
                + '<b>{}.{}</b>'.format(qgis_desktop[0], qgis_desktop[1])
                + "<br><br>"
                + tr('Your QGIS desktop is writing QGS project in the future compare to QGIS server.')
                + "<br>"
                + tr(
                    'You are strongly encouraged to upgrade your QGIS server. You will have issues when your QGIS '
                    'server will read your QGS project made with this version of QGIS desktop.'),
                QMessageBox.Ok
            )

    def current_lwc_version(self) -> LwcVersions:
        """ Return the current LWC version from the server combobox. """
        version = self.server_combo.currentData(ServerComboData.LwcVersion.value)
        if version:
            return version

        # This is temporary
        return LwcVersions.Lizmap_3_2

    def current_repository(self) -> str:
        """ Fetch the current directory on the server if available. """
        if not self.repository_combo.isVisible():
            return ''

        return self.repository_combo.currentData()

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

        current = self.server_combo.currentData(ServerComboData.ServerUrl.value)
        if not current:
            return

        if not current.endswith('/'):
            current += '/'

        metadata = self.server_combo.currentData(ServerComboData.JsonMetadata.value)
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
            self.repository_combo.setItemData(index, repository_id, Qt.ToolTipRole)

        # Restore the previous value if possible
        previous = self.project.customVariables().get('lizmap_repository')
        if not previous:
            return

        index = self.repository_combo.findData(previous)
        if not index:
            return

        self.repository_combo.setCurrentIndex(index)

    def setup_icons(self):
        """ Setup icons in the left menu. """
        i = 0

        # Information
        icon = QIcon()
        icon.addFile(resources_path('icons', '03-metadata-white'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '03-metadata-dark'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Map options
        icon = QIcon()
        icon.addFile(resources_path('icons', '15-baselayer-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '15-baselayer-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Layers
        icon = QIcon()
        icon.addFile(resources_path('icons', '02-switcher-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '02-switcher-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Base layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '02-switcher-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '02-switcher-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Layouts
        icon = QIcon()
        icon.addFile(resources_path('icons', '08-print-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '08-print-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Locate by layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '04-locate-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '04-locate-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Attribute table
        icon = QIcon()
        icon.addFile(resources_path('icons', '11-attribute-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '11-attribute-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Layer editing
        icon = QIcon()
        icon.addFile(resources_path('icons', '10-edition-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '10-edition-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Tooltip layer
        icon = QIcon()
        icon.addFile(resources_path('icons', '16-tooltip-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '16-tooltip-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Filter data with form
        icon = QIcon()
        icon.addFile(resources_path('icons', 'filter-icon-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', 'filter-icon-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Filter layer by user
        icon = QIcon()
        icon.addFile(resources_path('icons', '12-user-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '12-user-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Dataviz
        icon = QIcon()
        icon.addFile(resources_path('icons', 'dataviz-icon-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', 'dataviz-icon-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Time manager
        icon = QIcon()
        icon.addFile(resources_path('icons', '13-timemanager-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', '13-timemanager-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Atlas
        icon = QIcon()
        icon.addFile(resources_path('icons', 'atlas-icon-white.png'), mode=QIcon.Normal)
        icon.addFile(resources_path('icons', 'atlas-icon-dark.png'), mode=QIcon.Selected)
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Log
        # noinspection PyCallByClass,PyArgumentList
        icon = QIcon(QgsApplication.iconPath('mMessageLog.svg'))
        self.mOptionsListWidget.item(i).setIcon(icon)
        i += 1

        # Set stylesheet for QGroupBox
        if sys.platform.startswith('win'):
            style = ['0', '0', '0', '5%']
            margin = '4.0'
        else:
            style = ['225', '225', '225', '90%']
            margin = '2.5'
        style = STYLESHEET.format(*style, margin)

        self.gb_tree.setStyleSheet(style)
        self.gb_layerSettings.setStyleSheet(style)
        self.gb_ftp.setStyleSheet(style)
        self.gb_project_thumbnail.setStyleSheet(style)
        self.gb_visibleTools.setStyleSheet(style)
        self.gb_Scales.setStyleSheet(style)
        self.gb_extent.setStyleSheet(style)
        self.gb_externalLayers.setStyleSheet(style)
        self.gb_lizmapExternalBaselayers.setStyleSheet(style)
        self.gb_generalOptions.setStyleSheet(style)
        self.gb_interface.setStyleSheet(style)
        self.gb_baselayersOptions.setStyleSheet(style)
