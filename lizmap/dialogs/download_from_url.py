__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import logging
import tempfile

from enum import Enum
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsBlockingNetworkRequest,
    QgsFileDownloader,
    QgsProject,
)
from qgis.gui import QgsAuthConfigSelect
from qgis.PyQt.QtCore import QEventLoop, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from qgis.utils import OverrideCursor, iface


class UriType(Enum):
    Finder = 1
    Nautilus = 2
    Dolphin = 3
    WinScp = 4
    Gvfs = 5


LOGGER = logging.getLogger('Lizmap')


class DownloadProject(QDialog):

    def __init__(self, auth_id: str = None):
        # noinspection PyArgumentList
        QDialog.__init__(self)
        self.setMinimumWidth(800)
        layout = QVBoxLayout()

        self.auth = QgsAuthConfigSelect(self)
        if not auth_id:
            auth_id = "x70445w"

        if auth_id:
            self.auth.setConfigId(auth_id)
        self.project_url = QLineEdit(self)
        self.project_url.textChanged.connect(self.update_server)
        self.server_url = QLineEdit(self)

        debug_project = "https://demo.lizmap.com/lizmap/index.php/view/map?repository=features&project=observations"
        debug_project = "http://localhost:9023/index.php/view/map?repository=tests&project=fire_hydrant_actions"

        self.project_url.setPlaceholderText(debug_project)

        self.update_server()

        # noinspection PyArgumentList
        layout.addWidget(QLabel("Authentification perso"))
        # noinspection PyArgumentList
        layout.addWidget(self.auth)

        # noinspection PyArgumentList
        layout.addWidget(QLabel("Project URL"))
        # noinspection PyArgumentList
        layout.addWidget(self.project_url)

        # noinspection PyArgumentList
        layout.addWidget(QLabel("Server URL"))
        # noinspection PyArgumentList
        layout.addWidget(self.server_url)

        temp_dir = tempfile.TemporaryDirectory()

        # noinspection PyArgumentList
        layout.addWidget(QLabel("Destination"))
        self.directory = QLineEdit(self)
        self.directory.setPlaceholderText(temp_dir.name)
        # noinspection PyArgumentList
        layout.addWidget(self.directory)

        # noinspection PyArgumentList
        self.webdav_label_win = QLabel("WebDav URI (Mac, Finder, Curl)")
        self.webdav_label_win.setVisible(False)
        layout.addWidget(self.webdav_label_win)
        self.webdav_uri_win = QLineEdit(self)
        self.webdav_uri_win.setReadOnly(True)
        self.webdav_uri_win.setVisible(False)
        # noinspection PyArgumentList
        layout.addWidget(self.webdav_uri_win)

        # noinspection PyArgumentList
        self.webdav_label_gnome = QLabel("WebDav URI (Nautilus)")
        self.webdav_label_gnome.setVisible(False)
        layout.addWidget(self.webdav_label_gnome)
        self.webdav_uri_gnome = QLineEdit(self)
        self.webdav_uri_gnome.setReadOnly(True)
        self.webdav_uri_gnome.setVisible(False)
        # noinspection PyArgumentList
        layout.addWidget(self.webdav_uri_gnome)

        # noinspection PyArgumentList
        self.webdav_label_gvfs = QLabel("WebDav URI (GVFS)")
        self.webdav_label_gvfs.setVisible(False)
        layout.addWidget(self.webdav_label_gvfs)
        self.webdav_uri_gvfs = QLineEdit(self)
        self.webdav_uri_gvfs.setReadOnly(True)
        self.webdav_uri_gvfs.setVisible(False)
        # noinspection PyArgumentList
        layout.addWidget(self.webdav_uri_gvfs)

        # noinspection PyArgumentList
        self.webdav_label_kde = QLabel("WebDav URI (Dolphin KDE)")
        self.webdav_label_kde.setVisible(False)
        layout.addWidget(self.webdav_label_kde)
        self.webdav_uri_kde = QLineEdit(self)
        self.webdav_uri_kde.setReadOnly(True)
        self.webdav_uri_kde.setVisible(False)
        # noinspection PyArgumentList
        layout.addWidget(self.webdav_uri_kde)

        # noinspection PyArgumentList
        self.webdav_label_winscp = QLabel("WebDav URI (WinSCP, CyberDuck)")
        self.webdav_label_winscp.setVisible(False)
        layout.addWidget(self.webdav_label_winscp)
        self.webdav_uri_winscp = QLineEdit(self)
        self.webdav_uri_winscp.setReadOnly(True)
        self.webdav_uri_winscp.setVisible(False)
        # noinspection PyArgumentList
        layout.addWidget(self.webdav_uri_winscp)

        self.button_file_browser = QPushButton("Navigateur de fichier")
        self.button_file_browser.setVisible(False)
        self.button_file_browser.clicked.connect(self.open_file_browser)
        self.button_file_browser.setIcon(QIcon(":/images/themes/default/mIconFolderOpen.svg"))
        layout.addWidget(self.button_file_browser)

        self.button_box = QDialogButtonBox()
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        # noinspection PyArgumentList
        layout.addWidget(self.button_box)

        self.setLayout(layout)

        accept_button = self.button_box.button(QDialogButtonBox.Ok)
        accept_button.clicked.connect(self.download)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        cancel_button.clicked.connect(self.reject)

        self.destination = None

    def update_server(self):
        """ Update base URL of the server. """
        server_metadata = self.project_url.text()
        if not server_metadata:
            server_metadata = self.project_url.placeholderText()

        result = server_metadata.split('index.php')
        if not result:
            return

        self.server_url.setText(result[0])

    def _uri(self, webdav_url: str, uri_type: UriType) -> str:
        """ Different kind of URI. """
        auth_id = self.auth.configId()
        conf = QgsAuthMethodConfig()
        QgsApplication.authManager().loadAuthenticationConfig(auth_id, conf, True)
        if not conf.id():
            return ''

        parsed_result = urlparse(webdav_url)
        url = parsed_result.netloc + parsed_result.path

        user = conf.config('username')
        _ = conf.config('password')

        if uri_type == UriType.Nautilus:
            # https://en.wikipedia.org/wiki/Uniform_Resource_Identifier
            # user:password
            uri = f'davs://{user}@{url}'
        elif uri_type == UriType.Finder:
            uri = f'https://{url}'
        elif uri_type == UriType.Dolphin:
            uri = f'webdav://{url}'
        elif uri_type == UriType.Gvfs:
            # Remove last trailing slash
            escaped = parsed_result.path[0:-1]
            escaped = escaped.replace('/', '%2F')
            uri = (
                f"/run/user/1000/gvfs/dav:"
                f"host={parsed_result.hostname},"
                f"ssl=true,"
                f"user={user},"
                f"prefix={escaped}"
            )
        else:
            uri = url

        return uri

    def update_uri_gui(self, webdav_url: str):
        """ Update all URI for the webdav server. """
        # self.webdav_label_win.setVisible(True)
        # self.webdav_uri_win.setText(self._uri(webdav_url, UriType.Finder))
        # self.webdav_uri_win.setVisible(True)

        self.webdav_label_gnome.setVisible(True)
        self.webdav_uri_gnome.setText(self._uri(webdav_url, UriType.Nautilus))
        self.webdav_uri_gnome.setVisible(True)

        # self.webdav_label_winscp.setVisible(True)
        # self.webdav_uri_winscp.setText(self._uri(webdav_url, UriType.WinScp))
        # self.webdav_uri_winscp.setVisible(True)
        #
        # self.webdav_label_gvfs.setVisible(True)
        # self.webdav_uri_gvfs.setText(self._uri(webdav_url, UriType.Gvfs))
        # self.webdav_uri_gvfs.setVisible(True)
        #
        # self.webdav_label_kde.setVisible(True)
        # self.webdav_uri_kde.setText(self._uri(webdav_url, UriType.Dolphin))
        # self.webdav_uri_kde.setVisible(True)

        # Only a single button with GVFS for now
        # self.button_file_browser.setVisible(True)
        # self.button_file_browser.setToolTip(self._uri(webdav_url, UriType.Gvfs))

    def open_file_browser(self):
        """ Try to open the file browser. """
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.button_file_browser.toolTip()))

    def download(self):
        """ Download files. """
        server_metadata = self.server_url.text()
        if not server_metadata:
            server_metadata = self.server_url.placeholderText()
        if not server_metadata.endswith('/'):
            server_metadata += '/'
        server_metadata += 'index.php/view/app/metadata'

        if not self.auth.configId():
            return

        with OverrideCursor(Qt.WaitCursor):
            net_req = QNetworkRequest()
            # noinspection PyArgumentList
            net_req.setUrl(QUrl(server_metadata))
            net_req.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
            request = QgsBlockingNetworkRequest()
            request.setAuthCfg(self.auth.configId())
            request.get(net_req)
            response = request.reply().content()
            content = json.loads(response.data().decode('utf-8'))

            if not content:
                iface.messageBar().pushMessage(
                    title='Lizmap',
                    text='Erreur lors du téléchargement',
                    level=Qgis.Critical,
                    duration=5,
                )
                self.close()
                return

            project_url = self.project_url.text()
            if not project_url:
                project_url = self.project_url.placeholderText()

            result = urlparse(project_url)
            qs = parse_qs(result.query)
            repo_id = qs['repository'][0]
            project_id = qs['project'][0]

            repository = content['repositories'][repo_id]

            if not content.get('webdav'):
                iface.messageBar().pushMessage(
                    title='Lizmap',
                    text='Pas de webdav sur le serveur',
                    level=Qgis.Critical,
                    duration=5,
                )
                return

            webdav_url = content['webdav']['url']
            if not webdav_url.endswith('/'):
                webdav_url += '/'

            self.update_uri_gui(webdav_url)

            dav_project_path = content['webdav']['projects_path']
            if dav_project_path:
                if not dav_project_path.endswith('/'):
                    dav_project_path += '/'
                webdav_url += dav_project_path

            webdav_url += repository['path']
            if not webdav_url.endswith('/'):
                webdav_url += '/'

            webdav_url += project_id

            files = (webdav_url + '.qgs.cfg', webdav_url + '.qgs')

            output = self.directory.text()
            if not output:
                output = self.directory.placeholderText()
            output_dir = Path(output)
            if not output_dir.exists():
                output_dir.mkdir()

            self.destination = output_dir

            for file in files:

                if file.endswith('.qgs'):
                    destination_file = output_dir.joinpath(project_id + '.qgs')
                else:
                    destination_file = output_dir.joinpath(project_id + '.qgs.cfg')

                downloader = QgsFileDownloader(
                    QUrl(file), str(destination_file), delayStart=True, authcfg=self.auth.configId())
                loop = QEventLoop()
                downloader.downloadExited.connect(loop.quit)
                downloader.downloadError.connect(self.error)
                downloader.downloadCanceled.connect(self.canceled)
                downloader.downloadCompleted.connect(self.completed)
                downloader.startDownload()
                loop.exec_()

                if destination_file.exists() and file.endswith('.qgs'):
                    QgsProject.instance().read(str(destination_file))

        # self.close()

    @staticmethod
    def error(messages: str):
        """Store the messages error"""
        iface.messageBar().pushMessage(
            title='Lizmap',
            text=messages,
            level=Qgis.Critical,
            duration=5,
        )
        return

    @staticmethod
    def canceled():
        """Display the status in logger"""
        iface.messageBar().pushMessage(
            title='Lizmap',
            text="Cancelled",
            level=Qgis.Warning,
            duration=5,
        )
        return

    def completed(self):
        """Display the status in logger"""
        iface.messageBar().pushMessage(
            title='Lizmap',
            text="Got it <a href='file://{}'>{}</a>".format(self.destination, self.destination),
            level=Qgis.Success,
            duration=10,
        )
        return
