__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import logging

from base64 import b64encode
from typing import Tuple

from qgis.core import (
    QgsApplication,
    QgsAuthMethodConfig,
    QgsBlockingNetworkRequest,
)
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui
from lizmap.tools import qgis_version

FORM_CLASS = load_ui('ui_form_server.ui')
LOGGER = logging.getLogger('Lizmap')


class LizmapServerInfoForm(QDialog, FORM_CLASS):

    def __init__(self, parent, existing: list, url: str = '', auth_id: str = '', name: str = ''):
        """ Constructor. """
        # noinspection PyArgumentList
        QDialog.__init__(self, parent=parent)
        self.parent = parent
        self.setupUi(self)
        self.auth_manager = QgsApplication.authManager()
        self.existing = existing

        # If url and auth_id are defined, we are editing a server
        self.auth_id = auth_id
        if url:
            self.url.setText(url)
            self.name_placeholder()
            self.update_existing_credentials()
            self.name.setText(name)

        # Tooltip
        url = tr(
            'The URL of the Lizmap instance. You can visit the administration panel, then "Server information" tab and '
            'then click the copy/paste button.'
        )
        self.url.setToolTip(url)
        self.label_url.setToolTip(url)

        name = tr("The name that you want to see in the plugin. It's only a alias to help you.")
        self.name.setToolTip(name)
        self.label_name.setToolTip(name)

        login = tr("The login used to connect in your web browser.")
        self.login.setToolTip(login)
        self.label_login.setToolTip(login)

        password = tr("The password used to connect in your web browser.")
        self.password.setToolTip(password)
        self.label_password.setToolTip(password)

        # Signals
        self.url.textChanged.connect(self.name_placeholder)
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.button_box.button(QDialogButtonBox.Help).clicked.connect(self.click_help)
        self.validate()

    def update_existing_credentials(self):
        """ Set login and password in the UI if needed and possible. """
        if not self.auth_manager.masterPasswordIsSet():
            return

        conf = QgsAuthMethodConfig()
        self.auth_manager.loadAuthenticationConfig(self.auth_id, conf, True)
        if conf.id():
            self.login.setText(conf.config('username'))
            self.password.setText(conf.config('password'))
            return

        # The credentials have been removed from the password database
        # Must do something
        return

    @classmethod
    def automatic_name(cls, name: str) -> str:
        """ Transform the URL to make a shorter alias. """
        name = name.strip()
        name = name.replace("https://", "")
        name = name.replace("http://", "")

        if name.endswith('/'):
            name = name[0:-1]

        return name

    def name_placeholder(self):
        """ Set the placeholder for the name. """
        self.name.setPlaceholderText(self.automatic_name(self.current_url()))

    @staticmethod
    def clean_data(data) -> str:
        """ Clean input data from forms. """
        return data.strip()

    def current_url(self) -> str:
        """ Cleaned input URL. """
        url = self.url.text()

        if not url.endswith('/'):
            url += '/'

        return url

    def current_name(self) -> str:
        """ Cleaned input name. """
        user_input = self.clean_data(self.name.text())
        if user_input:
            return user_input

        return self.name.placeholderText()

    def current_login(self) -> str:
        """ Cleaned input login. """
        return self.clean_data(self.login.text())

    def current_password(self) -> str:
        """ Cleaned input password. """
        return self.clean_data(self.password.text())

    def accept(self):
        """ When the user press OK. """
        result = self.validate()
        if not result:
            return

        url = self.current_url()
        login = self.current_login()
        password = self.current_password()

        result, message = self.request_check_url(url, login, password)
        if not result:
            QMessageBox.critical(
                self.parent,
                tr('Lizmap Web Client error'),
                tr("It's not possible to fetch the metadata from this Lizmap instance.")
                + "<br><br>"
                + message,
                QMessageBox.Ok)
            return

        if not self.auth_manager.masterPasswordIsSet():
            result = QMessageBox.warning(
                self.parent,
                tr('QGIS Authentication'),
                tr(
                    "It's the first time you are using the QGIS native authentication database. When pressing the OK "
                    "button, you will be prompted for another password to secure your password manager. "
                    "This password is <b>not</b> related to Lizmap, only to <b>your QGIS current profile on this "
                    "computer</b> to unlock your password manager. "
                    "This password is not recoverable. Read more on the <a href=\""
                    "https://docs.qgis.org/latest/en/docs/user_manual/auth_system/auth_overview.html#master-password"
                    "\">QGIS documentation</a>."
                ),
                QMessageBox.Ok | QMessageBox.Cancel
            )
            if result == QMessageBox.Cancel:
                return

        config = QgsAuthMethodConfig()
        config.setUri(url)
        config.setName(login)
        config.setMethod('Basic')
        config.setConfig('username', login)
        config.setConfig('password', password)
        config.setConfig('realm', QUrl(self.current_url()).host())
        if self.auth_id:
            # Edit
            config.setId(self.auth_id)
            if qgis_version() < 32000:
                self.auth_manager.removeAuthenticationConfig(self.auth_id)
                result = self.auth_manager.storeAuthenticationConfig(config)
            else:
                result = self.auth_manager.storeAuthenticationConfig(config, True)
        else:
            # Creation
            self.auth_id = self.auth_manager.uniqueConfigId()
            config.setId(self.auth_id)
            result = self.auth_manager.storeAuthenticationConfig(config)

        if not result[0]:
            LOGGER.warning(
                "Saving configuration with login/password ID {} = {}".format(self.auth_id, result[1]))
            QMessageBox.critical(
                self.parent,
                tr('QGIS Authentication'),
                tr("We couldn't save the login/password into the QGIS authentication database : ")
                + result[1],
                QMessageBox.Ok)
            return

        LOGGER.info(
            "Saving configuration with login/password ID {} = OK".format(self.auth_id))

        self.done(QDialog.Accepted)

    def validate(self) -> bool:
        """ Check the form validity. """
        url = self.current_url()
        login = self.login.text()
        password = self.password.text()
        if not url or not login or not password:
            self.error.setText(tr("All fields are required."))
            self.error.setVisible(True)
            return False

        if ".php" in self.current_url():
            # Example : http://localhost:8080/index.php/view
            self.error.setText(tr(
                "The URL mustn't contain the \".php\".\n"
                "For instance, \"http://mydomain.com/index.php/view\" must be \"http://mydomain.com/\"."))
            self.error.setVisible(True)
            return False

        # Check for existing server in the JSON
        url = url.strip()
        url = url.rstrip('/')
        for server in self.existing:
            existing_server = server.get('url').rstrip('/')
            if url == existing_server:
                self.error.setText(tr(
                    "The URL is already in your existing list of Lizmap servers.\n"
                    "You should edit or remove the other server."))
                self.error.setVisible(True)
                return False

        if not QUrl(url).isValid():
            self.error.setText(tr("The URL is not valid."))
            self.error.setVisible(True)
            return False

        # Check the server / login validity
        # It cannot be done here, because we need the auth_cfg
        # TODO

        self.error.setVisible(False)
        return True

    @staticmethod
    def request_check_url(url: str, login: str, password: str) -> Tuple[bool, str]:
        """ Check the URL and given login. """

        if not url.endswith('/'):
            url += '/'

        if ' ' in url:
            return False, tr(
                "The URL provided is not correct. It contains spaces. Please check that the URL is correct and leads "
                "to the Lizmap Web Client home page."
            )

        url = '{}index.php/view/app/metadata'.format(url)

        net_req = QNetworkRequest()
        net_req.setUrl(QUrl(url))
        token = b64encode(f"{login}:{password}".encode())
        net_req.setRawHeader(b"Authorization", b"Basic %s" % token)
        request = QgsBlockingNetworkRequest()
        error = request.get(net_req)
        if error == QgsBlockingNetworkRequest.NetworkError:
            return False, tr("Network error")
        elif error == QgsBlockingNetworkRequest.ServerExceptionError:
            return False, tr("Server exception error")
        elif error == QgsBlockingNetworkRequest.TimeoutError:
            return False, tr("Timeout error")
        elif error != QgsBlockingNetworkRequest.NoError:
            return False, tr("Unknown error")

        response = request.reply().content()
        try:
            content = json.loads(response.data().decode('utf-8'))
        except json.JSONDecodeError:
            return False, tr('Not a JSON document, is-it the correct URL ?')

        info = content.get('info')
        if not info:
            return False, tr('No "info" in the JSON document')

        lizmap_version = info.get('version')
        if lizmap_version.startswith(('3.1', '3.2', '3.3', '3.4')):
            # Wait for EOL QGIS 3.10 because linked to LWC 3.5
            return True, ''

        # For other versions, we continue to see the access
        qgis_info = content.get('qgis_server_info')
        if not qgis_info:
            return False, 'Missing QGIS server info in the response, is-it the correct URL ?'

        error = qgis_info.get('error')
        if error:
            if error == "NO_ACCESS":
                if lizmap_version.startswith(('3.5', '3.6.0')):
                    message = tr("The given user does not have the right <b>Lizmap Admin access</b>.")
                    message += "<br><br>"
                    message += tr('Right') + " : lizmap.admin.access"
                else:
                    message = tr("The given user does not have the right <b>View the detailed server information</b>.")
                    message += "<br><br>"
                    message += tr('Right') + " : lizmap.admin.server.information.view"
                return False, message
            elif error == 'WRONG_CREDENTIALS':
                message = tr(
                    "Either the login or the password is wrong. Please check your credentials. It must be your login "
                    "you use in your web-browser.")
                return False, message
        return True, ''

    @staticmethod
    def click_help():
        """ Open the online help about this form. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(
            QUrl('https://docs.lizmap.com/current/en/publish/lizmap_plugin/information.html'))
