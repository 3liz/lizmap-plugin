__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QPixmap
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from lizmap.definitions.definitions import LwcVersions
from lizmap.definitions.online_help import online_lwc_help
from lizmap.definitions.qgis_settings import Settings
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.resources import load_ui, resources_path

LOGGER = logging.getLogger('Lizmap')
FORM_CLASS = load_ui('ui_news.ui')


class BaseNewsDialog(QDialog, FORM_CLASS):

    def __init__(self, link: str):
        # noinspection PyArgumentList
        QDialog.__init__(self)
        self.setupUi(self)
        self.link = link

        self.logo.setText('')
        pixmap = QPixmap(resources_path('icons', 'logo.png'))
        # noinspection PyUnresolvedReferences
        pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio)
        self.logo.setPixmap(pixmap)

        self.open_link.clicked.connect(self.open_website)

        accept_button = self.button_box.button(QDialogButtonBox.Ignore)
        accept_button.clicked.connect(self.accept)

    def open_website(self):
        """ Open the link. """
        # noinspection PyArgumentList
        QDesktopServices.openUrl(QUrl(self.link))


class NewVersionDialog(BaseNewsDialog):

    @classmethod
    def check_version(cls, lwc_version: LwcVersions, count_server: int) -> bool:
        """ Check according to previous versions if we can display the dialog. """
        if lwc_version <= LwcVersions.Lizmap_3_6:
            # 3.6 has been released before this feature to display a news
            # Too old to advertise the link
            return False

        if count_server == 0:
            # We display only if the user has one server
            # It means the user is already a user of Lizmap
            # So we can advertise this new version
            return False

        versions: list = QgsSettings().value(Settings.key(Settings.SeenChangelog), type=list)
        if lwc_version.value in versions:
            # Already seen this changelog
            return False

        return True

    @classmethod
    def append_version(cls, lwc_version: LwcVersions):
        """ Append the LWC version to the list of seen. """
        versions: list = QgsSettings().value(Settings.key(Settings.SeenChangelog), type=list)
        if lwc_version.value in versions:
            return

        versions.append(lwc_version.value)
        QgsSettings().setValue(Settings.key(Settings.SeenChangelog), versions)

    def __init__(self, lwc_version: LwcVersions, link: str):
        # noinspection PyArgumentList
        super().__init__(link)
        self.setWindowTitle(tr('New version {}').format(lwc_version.value))

        text = '<html><head/><body><p><span style=" font-size:16pt;">{} {}</span></p></body></html>'.format(
            tr("New release of Lizmap Web Client"),
            lwc_version.value
        )
        self.label_main.setText(text)

        self.label_description.setText(tr(
            "This new version has been released recently. Please visit the website about the visual changelog to "
            "discover <strong>some new features</strong> in this version."
        ).format(lwc_version.value))

        self.open_link.setText(tr("Open the visual changelog"))

        self.append_version(lwc_version)


class NewConfigDialog(BaseNewsDialog):

    def __init__(self):
        link = str(online_lwc_help("publish/quick_start/index.html"))
        # noinspection PyArgumentList
        super().__init__(link)
        self.setWindowTitle(tr('New Lizmap project'))

        text = '<html><head/><body><p><span style=" font-size:16pt;">{}</span></p></body></html>'.format(
            tr("First Lizmap configuration for this project"),
        )
        self.label_main.setText(text)

        self.label_description.setText(tr(
            "As this is a new project aimed to be published on Lizmap, you might encounter in the next step some "
            "'blockers' for generating the Lizmap configuration file. Please read the next panel carefully. You will "
            "find some auto-fix tools to optimize your project. Read the error description in the last column of the "
            "table, in the tooltip."
        ))

        self.open_link.setText(tr("Open the quick start guide"))
