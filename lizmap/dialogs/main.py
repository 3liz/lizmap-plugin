"""
/***************************************************************************
 lizmapDialog
                 A QGIS plugin
 Publication plugin for Lizmap web application, by 3liz.com
                -------------------
    begin        : 2011-11-01
    copyright      : (C) 2011 by 3liz
    email        : info@3liz.com
 ***************************************************************************/

/****** BEGIN LICENSE BLOCK *****
 Version: MPL 1.1/GPL 2.0/LGPL 2.1

 The contents of this file are subject to the Mozilla Public License Version
 1.1 (the "License"); you may not use this file except in compliance with
 the License. You may obtain a copy of the License at
 http://www.mozilla.org/MPL/

 Software distributed under the License is distributed on an "AS IS" basis,
 WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 for the specific language governing rights and limitations under the
 License.

 The Original Code is 3liz code,

 The Initial Developer of the Original Code are René-Luc D'Hont rldhont@3liz.com
 and Michael Douchin mdouchin@3liz.com
 Portions created by the Initial Developer are Copyright (C) 2011
 the Initial Developer. All Rights Reserved.

 Alternatively, the contents of this file may be used under the terms of
 either of the GNU General Public License Version 2 or later (the "GPL"),
 or the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 in which case the provisions of the GPL or the LGPL are applicable instead
 of those above. If you wish to allow use of your version of this file only
 under the terms of either the GPL or the LGPL, and not to allow others to
 use your version of this file under the terms of the MPL, indicate your
 decision by deleting the provisions above and replace them with the notice
 and other provisions required by the GPL or the LGPL. If you do not delete
 the provisions above, a recipient may use your version of this file under
 the terms of any one of the MPL, the GPL or the LGPL.

 ***** END LICENSE BLOCK ***** */
"""
from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QSizePolicy, QSpacerItem

try:
    from qgis.PyQt.QtWebKitWidgets import QWebView
    WEBKIT_AVAILABLE = True
except ModuleNotFoundError:
    WEBKIT_AVAILABLE = False
from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QLabel

from lizmap.definitions.definitions import LwcVersions, ServerComboData
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui
from lizmap.tools import format_qgis_version

FORM_CLASS = load_ui('ui_lizmap.ui')


class LizmapDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super().__init__(parent)
        self.setupUi(self)

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
                tr('QGIS server version behind QGIS desktop version'),
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
