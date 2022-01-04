__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import Qgis, QgsApplication, QgsAuthMethodConfig, QgsMessageLog
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from lizmap.qgis_plugin_tools.tools.resources import load_ui

FORM_CLASS = load_ui('ui_form_server.ui')


class LizmapServerInfoForm(QDialog, FORM_CLASS):

    def __init__(self, parent, url='', auth_id=''):
        """ Constructor. """
        # noinspection PyArgumentList
        QDialog.__init__(self, parent=parent)
        self.setupUi(self)

        # If url and auth_id are defined, we are editing a server
        self.auth_id = auth_id
        if url:
            self.url.setText(url)
            auth_manager = QgsApplication.authManager()
            conf = QgsAuthMethodConfig()
            auth_manager.loadAuthenticationConfig(self.auth_id, conf, True)
            if conf.id():
                self.login.setText(conf.config('username'))
                self.password.setText(conf.config('password'))
            else:
                # The credentials have been removed from the password database
                # Must do something
                pass

        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.button_box.button(QDialogButtonBox.Help).clicked.connect(self.click_help)
        self.validate()

    @staticmethod
    def clean_data(data) -> str:
        """ Clean input data from forms. """
        return data.strip()

    def current_url(self) -> str:
        """ Cleaned input URL. """
        return self.clean_data(self.url.text())

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

        login = self.current_login()
        password = self.current_password()

        if not login:
            self.done(QDialog.Accepted)

        auth_manager = QgsApplication.authManager()
        self.auth_id = auth_manager.uniqueConfigId()

        # TODO check if existing account exists for this server or in the JSON
        QgsMessageLog.logMessage(
            "Saving configuration with login/password ID {}".format(self.auth_id), "Lizmap", Qgis.Info)

        config = QgsAuthMethodConfig()
        config.setId(self.auth_id)
        config.setName('{}@{}'.format(login, self.current_url()))
        config.setMethod('Basic')
        config.setConfig('username', login)
        config.setConfig('password', password)
        auth_manager.storeAuthenticationConfig(config)

        self.done(QDialog.Accepted)

    def validate(self) -> bool:
        """ Check the form validity. """
        if not self.current_url():
            self.error.setText("The URL is required.")
            self.error.setVisible(True)
            return False

        login = self.login.text()
        password = self.password.text()

        if login and not password:
            self.error.setText("The password is required if the login is provided.")
            self.error.setVisible(True)
            return False

        self.error.setVisible(False)
        return True

    @staticmethod
    def click_help():
        """ Open the online help about this form. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(
            QUrl('https://docs.lizmap.com/current/en/publish/lizmap_plugin/information.html'))
