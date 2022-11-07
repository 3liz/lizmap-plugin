__copyright__ = 'Copyright 2022, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import Qgis, QgsApplication, QgsAuthMethodConfig, QgsMessageLog
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices, QPixmap
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
            self.update_existing_credentials()

        self.auth_manager = QgsApplication.authManager()
        self.widget_warning_password.setVisible(not self.auth_manager.masterPasswordIsSet())
        self.label_warning.setPixmap(QPixmap(":images/themes/default/mIconWarning.svg"))

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

        self.auth_id = self.auth_manager.uniqueConfigId()

        # TODO check if existing account exists for this server or in the JSON
        QgsMessageLog.logMessage(
            "Saving configuration with login/password ID {}".format(self.auth_id), "Lizmap", Qgis.Info)

        config = QgsAuthMethodConfig()
        config.setId(self.auth_id)
        config.setName('{}@{}'.format(login, self.current_url()))
        config.setMethod('Basic')
        config.setConfig('username', login)
        config.setConfig('password', password)
        self.auth_manager.storeAuthenticationConfig(config)

        self.done(QDialog.Accepted)

    def validate(self) -> bool:
        """ Check the form validity. """
        url = self.current_url()
        login = self.login.text()
        password = self.password.text()
        if not url or not login or not password:
            self.error.setText("All fields are required.")
            self.error.setVisible(True)
            return False

        if ".php" in self.current_url():
            # Example : http://localhost:8080/index.php/view
            self.error.setText(
                "The URL mustn't contain the \".php\".\n"
                "For instance, \"http://mydomain.com/index.php/view\" must be \"http://mydomain.com/\".")
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
