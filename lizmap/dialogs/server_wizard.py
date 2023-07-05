__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import configparser
import json
import logging
import sys

from base64 import b64encode
from enum import IntEnum, auto
from functools import partial
from typing import Optional, Tuple

from qgis.core import (
    Qgis,
    QgsAbstractDatabaseProviderConnection,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsBlockingNetworkRequest,
    QgsDataSourceUri,
    QgsProviderConnectionException,
    QgsProviderRegistry,
)
from qgis.gui import QgsPasswordLineEdit
from qgis.PyQt.QtCore import QRegExp, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QRegExpValidator
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)
from qgis.utils import OverrideCursor, iface

from lizmap.definitions.definitions import UNSTABLE_VERSION_PREFIX
from lizmap.definitions.online_help import online_help
from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.version import version

if Qgis.QGIS_VERSION_INT >= 32200:
    from lizmap.server_dav import WebDav

from lizmap.tools import lizmap_user_folder, qgis_version

LOGGER = logging.getLogger('Lizmap')
THUMBS = " 👍"
DEBUG = True


class WizardPages(IntEnum):
    """ Enum for all pages in the wizard. """
    UrlPage = auto()
    LoginPasswordPage = auto()
    NamePage = auto()
    MasterPasswordPage = auto()
    AddOrNotPostgresqlPage = auto()
    PostgresqlPage = auto()
    SuggestionNewFolder = auto()
    CreateNewFolderDav = auto()
    LizmapNewRepository = auto()


class UrlPage(QWizardPage):

    """ Server URL page. """

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.setTitle(tr("URL of the instance"))

        self.url = url

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel(tr(
            'If you are using Lizmap Web Client ≥ 3.6, visit your administration panel, then "Server information" and '
            'copy/paste the URL of your instance.'))
        label.setWordWrap(True)
        # noinspection PyArgumentList
        layout.addWidget(label)

        label = QLabel(tr(
            'Do not use any URL redirection. For instance, '
            '<a href="https://demo.lizmap.com/">https://demo.lizmap.com/</a> is a redirection to '
            '<a href="https://demo.lizmap.com/lizmap/">https://demo.lizmap.com/lizmap/</a>. Only the second one will '
            'work. Your URL must not contain ".php" extension at the end.'
        ))
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        # noinspection PyArgumentList
        layout.addWidget(label)

        self.url_label = QLabel(tr("URL"))
        self.url_edit = QLineEdit()
        # noinspection PyUnresolvedReferences
        self.url_edit.textChanged.connect(self.isComplete)
        self.registerField("url*", self.url_edit)
        url = tr(
            'The URL of the Lizmap instance. You can visit the administration panel, then "Server information" tab and '
            'then click the copy/paste button.'
        )
        self.url_label.setToolTip(url)
        self.url_edit.setToolTip(url)
        # noinspection PyArgumentList
        layout.addWidget(self.url_label)
        # noinspection PyArgumentList
        layout.addWidget(self.url_edit)

        self.result_url = QLabel()
        self.result_url.setWordWrap(True)
        # noinspection PyArgumentList
        layout.addWidget(self.result_url)

    def isComplete(self) -> bool:
        """ Form validation before the next step. """
        result = super().isComplete()
        if not result:
            return False

        url = QUrl(self.wizard().current_url())
        if not self.url_valid(url):
            self.result_url.setText(tr("URL is not valid"))
            return False

        self.result_url.setText("")
        return True

    def initializePage(self) -> None:
        """ Creation of the page. """
        if self.url:
            self.url_edit.setText(self.url)

    @staticmethod
    def url_valid(url: QUrl) -> bool:
        """ Check if the URL provided looks correct. """
        # noinspection PyUnresolvedReferences
        if not url.scheme().startswith('http'):
            return False

        if 'php' in url.path():
            return False

        return True


class LoginPasswordPage(QWizardPage):

    """ Login and password for the server. """

    def __init__(self, auth_id, parent=None):
        super().__init__(parent)
        self.setTitle(tr("Login and password of the instance"))

        self.auth_id = auth_id

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel(tr(
            'Login and password are the ones you are using in your web browser, to connect to the administration '
            'interface.'
        ))
        label.setWordWrap(True)
        # noinspection PyArgumentList
        layout.addWidget(label)

        self.login_label = QLabel(tr("Login"))
        self.login_edit = QLineEdit()
        # noinspection PyUnresolvedReferences
        self.login_edit.textChanged.connect(self.isComplete)
        self.registerField("login*", self.login_edit)
        login = tr("The login used to connect in your web browser.")
        self.login_label.setToolTip(login)
        self.login_edit.setToolTip(login)
        # noinspection PyArgumentList
        layout.addWidget(self.login_label)
        # noinspection PyArgumentList
        layout.addWidget(self.login_edit)

        self.password_label = QLabel(tr("Password"))
        self.password_edit = QgsPasswordLineEdit()
        # noinspection PyUnresolvedReferences
        self.password_edit.textChanged.connect(self.isComplete)
        self.registerField("password*", self.password_edit)
        password = tr("The password used to connect in your web browser.")
        self.password_label.setToolTip(password)
        self.password_edit.setToolTip(password)
        # noinspection PyArgumentList
        layout.addWidget(self.password_label)
        # noinspection PyArgumentList
        layout.addWidget(self.password_edit)

        self.result_login_password = QLabel()
        self.result_login_password.setWordWrap(True)
        # noinspection PyArgumentList
        layout.addWidget(self.result_login_password)

    def initializePage(self) -> None:
        """ Page creation. """
        if not self.auth_id:
            return

        conf = QgsAuthMethodConfig()
        QgsApplication.authManager().loadAuthenticationConfig(self.auth_id, conf, True)
        if conf.id():
            self.login_edit.setText(conf.config('username'))
            self.password_edit.setText(conf.config('password'))
            return

        # The credentials have been removed from the password database
        # Must do something
        return

    def nextId(self) -> int:
        """ Next ID, only if the URL is correct. """
        if self.wizard().page(WizardPages.UrlPage).result_url.text() != '':
            # The URL is not valid
            self.wizard().restart()
            return WizardPages.UrlPage

        return WizardPages.NamePage


class NamePage(QWizardPage):

    """ Alias for the server. """

    def __init__(self, name: str = '', parent=None):
        super().__init__(parent)
        self.setTitle(tr("Name of your instance"))

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.name = name

        self.name_label = QLabel(tr(
            "The name is only used by you, to have your own alias for display in QGIS desktop."))
        self.name_edit = QLineEdit()
        self.registerField("name*", self.name_edit)
        name = tr("The name that you want to see in the plugin. It's only a alias to help you.")
        self.name_label.setToolTip(name)
        self.name_edit.setToolTip(name)
        # noinspection PyArgumentList
        layout.addWidget(self.name_label)
        # noinspection PyArgumentList
        layout.addWidget(self.name_edit)

    def initializePage(self) -> None:
        """ Page creation. """
        if self.name:
            self.name_edit.setText(self.name)
        else:
            self.name_edit.setText(self.automatic_name(self.field('url')))

    @classmethod
    def automatic_name(cls, name: str) -> str:
        """ Transform the URL to make a shorter alias. """
        if not name:
            return ''
        name = name.strip()
        name = name.replace("https://", "")
        name = name.replace("http://", "")

        if name.endswith('/'):
            name = name[0:-1]

        return name


class MasterPasswordPage(QWizardPage):

    """ Save credentials in the QGIS password manager. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(tr("QGIS Password manager"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        # noinspection PyArgumentList
        layout.addWidget(QLabel(tr("Lizmap will now save your login and password in the QGIS password manager.")))
        label_warning = QLabel(tr(
            "It's the first time you are using the QGIS native authentication database. When pressing the Next "
            "button, you will be prompted for another password to secure your password manager. "
            "This password is <b>not</b> related to Lizmap, only to <b>your QGIS current profile on this "
            "computer</b> to unlock your password manager. "
            "This password is not recoverable. Read more on the <a href=\""
            "https://docs.qgis.org/latest/en/docs/user_manual/auth_system/auth_overview.html#master-password"
            "\">QGIS documentation</a>."
        ))
        label_warning.setOpenExternalLinks(True)
        label_warning.setWordWrap(True)
        # noinspection PyArgumentList
        layout.addWidget(label_warning)

        if QgsApplication.authManager().masterPasswordIsSet():
            label_warning.setVisible(False)
        else:
            label_warning.setVisible(True)

        self.result_master_password = QLabel()
        self.result_master_password.setWordWrap(True)
        # noinspection PyArgumentList
        layout.addWidget(self.result_master_password)

    def nextId(self) -> int:
        """ Next page, according to lizmap.com hosting. """
        parent_wizard = self.wizard()
        parent_wizard: ServerWizard
        if not parent_wizard.is_lizmap_dot_com:
            # Finished
            LOGGER.debug("After saving the auth ID, it's finished")
            return -1

        LOGGER.debug("After saving the auth ID, go the PostgreSQL page.")
        return WizardPages.AddOrNotPostgresqlPage


class AddOrNotPostgresqlPage(QWizardPage):

    """ Question for PostgreSQL connection. """

    def __init__(self, parent=None):
        super().__init__(parent)
        LOGGER.debug("Page : Add the PostgreSQL connection delivered with Lizmap")
        self.setTitle(tr("PostgreSQL"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        # noinspection PyArgumentList
        layout.addWidget(QLabel(tr("Would you like to add the PostgreSQL connection provided with your instance ?")))
        # noinspection PyArgumentList
        layout.addWidget(QLabel(tr("It's recommended as it will set up the connection with optimized parameters.")))

        self.no = QRadioButton(tr("No"))
        self.yes = QRadioButton(tr("Yes (recommended)"))
        self.yes.setChecked(True)

        # noinspection PyArgumentList
        layout.addWidget(self.yes)
        # noinspection PyArgumentList
        layout.addWidget(self.no)

        self.registerField("postgresql_no", self.no)
        self.registerField("postgresql_yes", self.yes)

        # noinspection PyUnresolvedReferences
        self.yes.toggled.connect(self.isComplete)
        # noinspection PyUnresolvedReferences
        self.no.toggled.connect(self.isComplete)

    def isComplete(self) -> bool:
        """ Form validation before the next step. """

        if self.field("postgresql_no"):
            if not self.wizard().has_repository and self.wizard().dav_url:
                # Webdav repository
                self.setFinalPage(False)
                self.wizard().button(QWizard.NextButton).setVisible(True)
            else:
                # Finish
                self.setFinalPage(True)
                self.wizard().button(QWizard.NextButton).setVisible(False)
        else:
            # Add PG
            self.wizard().button(QWizard.NextButton).setVisible(True)
            self.setFinalPage(False)

        return super().isComplete()

    def nextId(self) -> int:
        """ Next step. """
        if self.field("postgresql_yes"):
            return WizardPages.PostgresqlPage

        if self.wizard().has_repository:
            return -1

        if not self.wizard().dav_url:
            return -1

        return WizardPages.SuggestionNewFolder


# noinspection PyArgumentList
class PostgresqlPage(QWizardPage):

    """ Wizard for the PostgreSQL connection. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(tr("Adding a PostgreSQL connection"))
        self.setSubTitle("PostgreSQL database provided with the Lizmap instance")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Helper
        label = QLabel(tr(
            'Fill your host, login and database name. Other fields should be correct already, but you should check. It '
            'might be a little bit different for your own instance.'
        ))
        label.setWordWrap(True)
        # noinspection PyArgumentList
        layout.addWidget(label)

        # Connection name
        self.pg_name_label = QLabel(tr("Name"))
        self.pg_name_edit = QLineEdit()
        self.registerField("pg_name*", self.pg_name_edit)
        # noinspection PyArgumentList
        layout.addWidget(self.pg_name_label)
        # noinspection PyArgumentList
        layout.addWidget(self.pg_name_edit)

        # Host
        self.host_label = QLabel(tr("Host"))
        self.host_edit = QLineEdit()
        self.registerField("pg_host*", self.host_edit)
        # noinspection PyArgumentList
        layout.addWidget(self.host_label)
        # noinspection PyArgumentList
        layout.addWidget(self.host_edit)

        # Port
        self.port_label = QLabel(tr("Port"))
        self.port_edit = QSpinBox()
        self.port_edit.setValue(5432)
        self.port_edit.setMinimum(1)
        self.port_edit.setMaximum(65535)
        self.registerField("pg_port*", self.port_edit)
        # noinspection PyArgumentList
        layout.addWidget(self.port_label)
        # noinspection PyArgumentList
        layout.addWidget(self.port_edit)

        # DB name
        self.db_name_label = QLabel(tr("Database name"))
        self.db_name_edit = QLineEdit()
        self.registerField("pg_db_name*", self.db_name_edit)
        # noinspection PyArgumentList
        layout.addWidget(self.db_name_label)
        # noinspection PyArgumentList
        layout.addWidget(self.db_name_edit)

        # User
        self.pg_user_label = QLabel(tr("User"))
        self.pg_user_edit = QLineEdit()
        self.registerField("pg_user*", self.pg_user_edit)
        # noinspection PyArgumentList
        layout.addWidget(self.pg_user_label)
        # noinspection PyArgumentList
        layout.addWidget(self.pg_user_edit)

        # Password
        self.pg_password_label = QLabel(tr("Password"))
        self.pg_password_edit = QgsPasswordLineEdit()
        # noinspection PyUnresolvedReferences
        self.pg_password_edit.textChanged.connect(self.isComplete)
        self.registerField("pg_password*", self.pg_password_edit)
        password = tr("The password used to connect to your PostgreSQL database")
        self.pg_password_label.setToolTip(password)
        self.pg_password_edit.setToolTip(password)
        # noinspection PyArgumentList
        layout.addWidget(self.pg_password_label)
        # noinspection PyArgumentList
        layout.addWidget(self.pg_password_edit)

        # Result
        self.skip_db = QCheckBox()
        self.skip_db.setText(tr("Skip the database creation if a failure happen again."))
        self.skip_db.setVisible(False)
        self.registerField("skip_db", self.skip_db)

        self.skip_db_label = QLabel(tr(
            "If checked and if it fails again, you will need to use the native QGIS dialog to set-up your connection. "
            "Remember to not use the QGIS password manager for storing login and password about PostGIS, instead use "
            "a plain text storage, by checking both buttons 'Store' for login and password. We also recommend checking "
            "'Use estimated table metadata' and 'Also list tables with no geometry'."))
        self.skip_db_label.setVisible(False)
        self.skip_db_label.setWordWrap(True)

        self.result_pg = QLabel()
        self.result_pg.setWordWrap(True)
        # noinspection PyArgumentList
        layout.addWidget(self.result_pg)
        layout.addWidget(self.skip_db)
        layout.addWidget(self.skip_db_label)

    def initializePage(self) -> None:
        """ Page creation. """
        self.pg_name_edit.setText(self.field("name").replace('/', '-'))
        self.port_edit.setValue(5432)
        # self.pg_user_edit.setText(self.field("login"))
        self.pg_password_edit.setText(self.field("password"))

    def nextId(self) -> int:
        """ Next ID. """
        if self.wizard().has_repository:
            # Finished
            return -1

        return WizardPages.SuggestionNewFolder


class SuggestionNewFolderPage(QWizardPage):

    """ Question for the first folder. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(tr("Create the first folder"))
        self.setSubTitle(tr("A folder can contain one or many QGIS projects"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        helper = QLabel(tr(
            "It seems it's your first time on this Lizmap instance, because you don't have any repository set up on "
            "this server yet."
        ))
        helper.setWordWrap(True)
        layout.addWidget(helper)

        # noinspection PyArgumentList
        layout.addWidget(QLabel(tr("Do you want to create your first folder ?")))

        self.no = QRadioButton(tr("No"))
        self.yes = QRadioButton(tr("Yes (recommended)"))
        self.yes.setChecked(True)

        # noinspection PyArgumentList
        layout.addWidget(self.yes)
        # noinspection PyArgumentList
        layout.addWidget(self.no)

        self.registerField("dav_no", self.no)
        self.registerField("dav_yes", self.yes)

        # noinspection PyUnresolvedReferences
        self.yes.toggled.connect(self.isComplete)
        # noinspection PyUnresolvedReferences
        self.no.toggled.connect(self.isComplete)

    def isComplete(self) -> bool:
        """ Form validation before the next step. """

        if self.field("dav_no"):
            self.setFinalPage(True)
            self.wizard().button(QWizard.NextButton).setVisible(False)
        else:
            self.wizard().button(QWizard.NextButton).setVisible(True)
            self.setFinalPage(False)
        return super().isComplete()


class CreateNewFolderDavPage(QWizardPage):

    """ Wizard for the first folder creation. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(tr("First folder"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        helper = QLabel(tr(
            "A folder can contain one or many QGIS projects. Usually people create a folder for a common theme for a "
            "set of QGIS projects, such as \"Urbanism\"."
        ))
        helper.setWordWrap(True)
        layout.addWidget(helper)
        layout.addWidget(QLabel(tr("This is only some suggestions, feel free to edit the name you would like.")))

        helper_2 = QLabel(tr("This will create a proper folder on the file system."))
        helper_2.setWordWrap(True)
        layout.addWidget(helper_2)

        horizontal = QHBoxLayout()

        self.test_button = QPushButton(tr("test"))
        self.cadastre_button = QPushButton(tr("cadastre"))
        self.urbanisme_button = QPushButton(tr("urbanisme"))

        self.test_button.clicked.connect(partial(self.add_suggestion, self.test_button.text()))
        self.cadastre_button.clicked.connect(partial(self.add_suggestion, self.cadastre_button.text()))
        self.urbanisme_button.clicked.connect(partial(self.add_suggestion, self.urbanisme_button.text()))

        horizontal.addWidget(self.test_button)
        horizontal.addWidget(self.cadastre_button)
        horizontal.addWidget(self.urbanisme_button)
        layout.addLayout(horizontal)

        self.custom_name = QLineEdit()
        regexp = QRegExp("^[a-z0-9]+$")
        validator = QRegExpValidator(regexp, self.custom_name)
        self.custom_name.setValidator(validator)
        layout.addWidget(self.custom_name)
        self.registerField("folder_name", self.custom_name)

        self.create_button = QPushButton(tr("Create"))
        layout.addWidget(self.create_button)
        self.create_button.clicked.connect(self.create_remote_directory)

        self.result = QLabel()
        self.result.setWordWrap(True)
        layout.addWidget(self.result)

    def add_suggestion(self, suggestion):
        """ Add the suggestion. """
        self.custom_name.setText(suggestion)

    def create_remote_directory(self):
        """ Create a remote directory using webdav protocol. """
        self.result.setText(tr("Wait") + '…')

        parent_wizard = self.wizard()
        parent_wizard: ServerWizard
        dav_url = parent_wizard.dav_url
        auth_id = parent_wizard.auth_id

        LOGGER.debug("Creating a folder called '{}' on {}".format(self.custom_name.text(), dav_url))
        with OverrideCursor(Qt.WaitCursor):
            server_dav = WebDav(dav_url, auth_id)
            result, msg = server_dav.make_dir(self.custom_name.text())

        if result:
            self.result.setText(tr("Folder created") + " " + THUMBS)
            return

        self.label_result_folder.setText(msg)


class LizmapNewRepositoryPage(QWizardPage):

    """ Web-browser step for the Lizmap repository creation. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(tr("Create a Lizmap repository"))

        layout = QVBoxLayout()
        self.setLayout(layout)

        step_1 = QLabel(
            "1. " + tr("Set-up your folder \"{}\" to be recognised as a Lizmap repository in your web browser.").format(
                self.field("folder_name")
            )
        )
        step_1.setWordWrap(True)
        layout.addWidget(step_1)

        self.open_web_browser = QPushButton(tr("Open your web browser to finalise the repository creation"))
        self.open_web_browser.clicked.connect(self.open_browser)
        layout.addWidget(self.open_web_browser)

        step_2 = QLabel(tr(
            "When you have finalized the repository creation in your web browser, you can continue the process."))
        step_2.setWordWrap(True)
        layout.addWidget(step_2)

        self.check_repository = QPushButton(
            "2. " + tr("Check if the new repository is detected"))
        self.check_repository.clicked.connect(self.refresh_list)
        layout.addWidget(self.check_repository)

        self.result = QLabel()
        self.result.setWordWrap(True)
        layout.addWidget(self.result)

    def open_browser(self):
        """ Open the web browser. """
        # noinspection PyArgumentList
        url = QUrl('{}/admin.php/admin/maps/createSection'.format(self.wizard().current_url()))
        QDesktopServices.openUrl(url)

    def refresh_list(self):
        """ Check the newly created repository. """
        self.result.setText(tr("Wait") + '…')

        request = QNetworkRequest()
        request.setUrl(QUrl(self.wizard().url_metadata(self.wizard().current_url())))
        network_request = QgsBlockingNetworkRequest()
        network_request.setAuthCfg(self.wizard().auth_id)

        with OverrideCursor(Qt.WaitCursor):
            network_request.get(request)

        response = network_request.reply().content()
        repositories = json.loads(response.data().decode('utf-8')).get('repositories')
        for repo_id, data in repositories.items():
            if data['path'] == self.field("folder_name") + '/':
                self.result.setText(tr("Found it") + " " + THUMBS)
                break
        else:
            self.result.setText(
                tr("The folder <b>{}</b> has not been found as a valid Lizmap repository.".format(
                    self.field("folder_name")))
            )


class ServerWizard(QWizard):

    """ Main wizard class. """

    def __init__(self, parent=None, existing: list = None, url: str = '', auth_id: str = None, name: str = ''):
        # noinspection PyArgumentList
        super().__init__(parent)
        self.setWindowTitle(tr("Lizmap Web Client instance"))
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage)
        self.setOption(QWizard.HaveHelpButton)

        self.setMinimumSize(800, 550)

        self.auth_id = auth_id
        self.server_info = None
        self.is_lizmap_dot_com = False
        self.has_repository = None
        self.dav_url = None
        self.dav_path = None

        if existing is None:
            existing = []

        self.existing = existing

        # If url and auth_id are defined, we are editing a server
        self.auth_id = auth_id

        # noinspection PyUnresolvedReferences
        self.helpRequested.connect(self.open_online_help)

        self.setPage(WizardPages.UrlPage, UrlPage(url))
        self.setPage(WizardPages.LoginPasswordPage, LoginPasswordPage(auth_id))
        self.setPage(WizardPages.NamePage, NamePage(name))
        self.setPage(WizardPages.MasterPasswordPage, MasterPasswordPage())
        self.setPage(WizardPages.AddOrNotPostgresqlPage, AddOrNotPostgresqlPage())
        self.setPage(WizardPages.PostgresqlPage, PostgresqlPage())
        self.setPage(WizardPages.SuggestionNewFolder, SuggestionNewFolderPage())
        self.setPage(WizardPages.CreateNewFolderDav, CreateNewFolderDavPage())
        self.setPage(WizardPages.LizmapNewRepository, LizmapNewRepositoryPage())

    @staticmethod
    def open_online_help() -> None:
        """ Open the online help about this form. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(online_help('publish/lizmap_plugin/information.html'))

    def validateCurrentPage(self):
        """Specific rules for page validation. """
        if self.currentId() == WizardPages.LoginPasswordPage:
            self.page(WizardPages.UrlPage).result_url.setText('')
            self.currentPage().result_login_password.setText(tr("Fetching") + "…")

            with OverrideCursor(Qt.WaitCursor):
                flag, message, url_valid = self.request_check_url(
                    self.field('url'),
                    self.field('login'),
                    self.field('password'))
            if flag:
                self.currentPage().result_login_password.setText(THUMBS)
                return True

            # The config was not correct, let's check which panel

            if not url_valid:
                # The URL was not a JSON file, so we return true and the nextId will take care of it
                # Even with bad login & password
                self.page(WizardPages.UrlPage).result_url.setText(tr('The URL was not valid : {}').format(
                    self.field('url')))
                self.currentPage().result_login_password.setText("")
                return True

            # Only login & password were not correct
            self.page(WizardPages.UrlPage).result_url.setText("")
            self.currentPage().result_login_password.setText(message)
            return False

        elif self.currentId() == WizardPages.MasterPasswordPage:
            result = self.save_auth_id()
            LOGGER.debug("Saving to the authentication database is : {} valid".format("" if result else "not"))
            return result

        elif self.currentId() == WizardPages.PostgresqlPage:
            skip_db_saving = self.field("skip_db")
            if not self.test_pg():
                if skip_db_saving:
                    # Second attempt, we skip
                    return True
                else:
                    return False

            return self.save_pg()

        return super().validateCurrentPage()

    @staticmethod
    def clean_data(data) -> str:
        """ Clean input data from forms. """
        return data.strip()

    def current_url(self) -> str:
        """ Cleaned input URL. """
        url = self.trailing_slash(self.clean_data(self.field('url')))
        return url

    def current_name(self) -> str:
        """ Cleaned input name. """
        return self.clean_data(self.field("name"))

    def current_login(self) -> str:
        """ Cleaned input login. """
        return self.clean_data(self.field("login"))

    def save_auth_id(self) -> bool:
        """ Save login and password in the QGIS password manager. """
        url = self.current_url()
        login = self.current_login()
        password = self.field('password')

        auth_manager = QgsApplication.authManager()

        config = QgsAuthMethodConfig()
        config.setUri(url)
        config.setName(login)
        config.setMethod('Basic')
        config.setConfig('username', login)
        config.setConfig('password', password)
        # noinspection PyArgumentList,PyUnresolvedReferences
        config.setConfig('realm', QUrl(url).host())
        if self.auth_id:
            LOGGER.debug("Edit current information authentication ID : {}".format(self.auth_id))
            # Edit
            config.setId(self.auth_id)
            if qgis_version() < 32000:
                auth_manager.removeAuthenticationConfig(self.auth_id)
                result = auth_manager.storeAuthenticationConfig(config)
            else:
                result = auth_manager.storeAuthenticationConfig(config, True)
        else:
            # Creation
            self.auth_id = auth_manager.uniqueConfigId()
            LOGGER.debug("New authentication ID : {}".format(self.auth_id))
            config.setId(self.auth_id)
            result = auth_manager.storeAuthenticationConfig(config)

        if result[0]:
            self.currentPage().result_master_password.setText(THUMBS)
            LOGGER.info(
                "Saving configuration with login/password ID {} = OK".format(self.auth_id))
            return True

        LOGGER.warning(
            "Saving configuration with login/password ID {} = NOK".format(self.auth_id))
        self.currentPage().result_master_password.setText(
            tr("We couldn't save the login/password into the QGIS authentication database : NOK")
        )
        return False

    @classmethod
    def override_url(cls, base_url: str, metadata=True) -> Optional[str]:
        """ Override URL if the file is specified. """
        ini = lizmap_user_folder().joinpath('urls.ini')
        if not ini.exists():
            return None

        # At that stage, there is a trailing slash at the end of the URL, whatever the input is.
        # We can either have [https://ilovecookie.org/] or [https://ilovecookie.org] in the urls.ini
        config = configparser.ConfigParser()
        config.read(ini)
        if base_url not in config.sections():
            if base_url[0:-1] not in config.sections():
                return None

        LOGGER.info("Found a server override for server {}".format(base_url))

        key = 'metadata' if metadata else 'dataviz'
        try:
            return config.get(base_url, key)
        except configparser.NoSectionError:
            return config.get(base_url[0:-1], key)

    @classmethod
    def trailing_slash(cls, url: str) -> str:
        """ Add the trailing slash before URL concatenation. """
        if not url.endswith('/'):
            url += '/'
        return url

    @staticmethod
    def url_metadata(base_url: str) -> str:
        """ Return the URL to fetch metadata from LWC server. """
        override = ServerWizard.override_url(base_url)
        if override:
            return override

        base_url = ServerWizard.trailing_slash(base_url)
        url = '{}index.php/view/app/metadata'.format(base_url)
        return url

    @staticmethod
    def url_dataviz(base_url: str) -> str:
        """ Return the URL to fetch metadata from LWC server. """
        override = ServerWizard.override_url(base_url, False)
        if override:
            return override

        base_url = ServerWizard.trailing_slash(base_url)
        url = '{}index.php/dataviz/service/'.format(base_url)
        return url

    @staticmethod
    def url_server_info(base_url: str) -> str:
        """ Return the URL to the server information panel. """
        base_url = ServerWizard.trailing_slash(base_url)
        url = '{}admin.php/admin/server_information'.format(base_url)
        return url

    def request_check_url(self, url: str, login: str, password: str) -> Tuple[bool, str, bool]:
        """ Check the URL and given login.

        The first boolean is about the server status.
        The latest boolean is about the URL check if it's a JSON document
        """
        url = self.trailing_slash(url)

        if ' ' in url:
            return False, tr(
                "The URL provided is not correct. It contains spaces. Please check that the URL is correct and leads "
                "to the Lizmap Web Client home page."
            ), False

        url = self.url_metadata(url)

        net_req = QNetworkRequest()
        # noinspection PyArgumentList
        net_req.setUrl(QUrl(url))
        token = b64encode(f"{login}:{password}".encode())
        net_req.setRawHeader(b"Authorization", b"Basic %s" % token)
        net_req.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        request = QgsBlockingNetworkRequest()
        error = request.get(net_req)
        if error == QgsBlockingNetworkRequest.NetworkError:
            return False, tr("Network error"), False
        elif error == QgsBlockingNetworkRequest.ServerExceptionError:
            return False, tr("Server exception error") + ". " + tr('Please check the URL'), False
        elif error == QgsBlockingNetworkRequest.TimeoutError:
            return False, tr("Timeout error"), False
        elif error != QgsBlockingNetworkRequest.NoError:
            return False, tr("Unknown error"), False

        response = request.reply().content()
        try:
            content = json.loads(response.data().decode('utf-8'))
        except json.JSONDecodeError:
            return False, tr('Not a JSON document, is-it the correct URL ?'), False

        info = content.get('info')
        if not info:
            return False, tr('No "info" in the JSON document'), False

        lizmap_version = info.get('version')
        if lizmap_version.startswith(('3.1', '3.2', '3.3', '3.4')):
            # Wait for EOL QGIS 3.10 because linked to LWC 3.5
            return True, '', True

        # For other versions, we continue to see the access
        qgis_info = content.get('qgis_server_info')
        if not qgis_info:
            return False, 'Missing QGIS server info in the response, is-it the correct URL ?', True

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
                return False, message, True
            elif error == 'WRONG_CREDENTIALS':
                message = tr(
                    "Either the login or the password is wrong. It must be your login you use in your web-browser.")
                return False, message, True

        self.server_info = content
        self.is_lizmap_dot_com = content.get('hosting', '') == 'lizmap.com'
        self.has_repository = True if len(content.get('repositories', [])) >= 1 else False
        if any(item in version() for item in UNSTABLE_VERSION_PREFIX):
            # Debug for devs
            self.has_repository = False
        self.dav_url = content.get('webdav')
        if Qgis.QGIS_VERSION_INT < 32200:
            # Missing PyQGIS class for managing webdav
            self.dav_url = None
        self.dav_path = content.get('webdav_path')
        return True, '', True

    def _uri(self) -> QgsDataSourceUri:
        """ URI of the current PG credentials. """
        uri = QgsDataSourceUri()
        uri.setConnection(
            self.field("pg_host"),
            str(self.field('pg_port')),
            self.field("pg_db_name"),
            self.field("pg_user"),
            self.field("pg_password"),
            QgsDataSourceUri.SslMode.SslPrefer,
        )
        return uri

    def test_pg(self) -> bool:
        """ Test the connection. """
        uri = self._uri()
        metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
        # noinspection PyTypeChecker
        connection = metadata.createConnection(uri.uri(), {})
        connection: QgsAbstractDatabaseProviderConnection
        try:
            result = connection.executeSql("SELECT 1 AS lizmap_plugin_test")
        except QgsProviderConnectionException:
            # Credentials are wrong
            LOGGER.warning("Wrong credentials about the PostgreSQL database")
        else:
            if len(result) >= 1:
                self.currentPage().result_pg.setText(THUMBS)
                return True

        self.currentPage().result_pg.setText(tr(
            'Error, please check your inputs, or do with the native QGIS connection dialog.'))
        self.currentPage().skip_db.setVisible(True)
        self.currentPage().skip_db_label.setVisible(True)
        return False

    def save_pg(self) -> bool:
        """ Save the current connection in the QGIS browser. """
        name = self.field("pg_name")
        md = QgsProviderRegistry.instance().providerMetadata('postgres')
        conn = md.findConnection(name)
        if conn:
            self.currentPage().result_pg.setText(tr('Connection name is already existing, please choose another one'))
            return False

        self._save_pg(name, self._uri())
        iface.browserModel().reload()
        self.currentPage().result_pg.setText(THUMBS)
        return True

    @classmethod
    def _save_pg(cls, name: str, uri: QgsDataSourceUri) -> bool:
        """ Save a PG connection from a URI. """
        LOGGER.info(
            "Create PG connection '{}' : host {}, database {}, user {}, pass XXXXX, port {}".format(
                name, uri.host(), uri.database(), uri.username(), uri.port())
        )
        config = {
            "saveUsername": True,
            "savePassword": True,
            "estimatedMetadata": True,
            "metadataInDatabase": True,
            "allowGeometrylessTables": True,
            "geometryColumnsOnly": True,
            "dontResolveType": False,
            "publicOnly": False,
        }
        metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
        # noinspection PyTypeChecker
        connection = metadata.createConnection(uri.uri(), config)
        connection: QgsAbstractDatabaseProviderConnection
        connection.store(name)
        return True


if __name__ == '__main__':
    """ For manual tests. """
    app = QApplication(sys.argv)
    wizard = ServerWizard()
    wizard.show()
    sys.exit(app.exec_())
