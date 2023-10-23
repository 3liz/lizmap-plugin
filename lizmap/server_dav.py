__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from base64 import b64encode
from pathlib import Path
from typing import Optional, Tuple
from xml.dom.minidom import parseString

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsExternalStorage,
    QgsNetworkAccessManager,
    QgsProject,
)
from qgis.PyQt.QtCore import QEventLoop, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from lizmap.definitions.definitions import RepositoryComboData, ServerComboData
from lizmap.dialogs.main import LizmapDialog
from lizmap.qgis_plugin_tools.tools.i18n import tr

LOGGER = logging.getLogger("Lizmap")


class WebDav:

    def __init__(self, dav_server: str = None, auth_id: str = None):
        """ Constructor. """
        super().__init__()
        # Either from the dialog
        self.parent: Optional[LizmapDialog] = None

        # Or from constructor
        self._dav_server = dav_server
        self._auth_id = auth_id

        # noinspection PyArgumentList
        registry = QgsApplication.externalStorageRegistry()
        self.webdav = registry.externalStorageFromType('WebDAV')
        self.webdav: QgsExternalStorage

        self.qgs_path = None
        self.qgs_status = None
        self.qgs = None

        self.cfg_path = None
        self.cfg_status = None
        self.cfg = None

    @property
    def auth_id(self) -> Optional[str]:
        """ Return the auth ID, either from the dialog first, or the one in the constructor. """
        if self.parent:
            return self.parent.server_combo.currentData(ServerComboData.AuthId.value)
        return self._auth_id

    @property
    def dav_server(self) -> Optional[str]:
        """ Return the URL to the DAV server, either from the dialog first, or the one in the constructor. """
        if self.parent:
            metadata = self.parent.server_combo.currentData(ServerComboData.JsonMetadata.value).get('webdav')
            if not metadata:
                # Module not enabled
                return None
            qgis_folder = self.url_slash(
                self.url_slash(metadata.get('url'))
                + metadata.get('projects_path'))
            return qgis_folder

        return self._dav_server

    @staticmethod
    def url_slash(url: str) -> str:
        if not url.endswith('/'):
            url += '/'
        return url

    def dav_repository_url(self) -> Optional[str]:
        """ With webdav, returns the full URL to the repository. """
        url = self.dav_server + self.parent.current_repository(RepositoryComboData.Path)
        if not url:
            # No repository yet
            return None

        return self.url_slash(url)

    def project_url(self) -> str:
        """ Returns the URL to the project in the web browser. """
        server = self.parent.server_combo.currentData(ServerComboData.ServerUrl.value)
        if not server.endswith('/'):
            server += '/'
        server += 'index.php/view/map?repository={repository}&project={project}'.format(
            repository=self.parent.current_repository(RepositoryComboData.Id),
            project=Path(self.qgs_path).stem
        )
        return server

    def setup_webdav_dialog(self, dialog: LizmapDialog = None) -> bool:
        """ Setting up the dav connection. """
        if dialog:
            self.parent = dialog

        assert self.parent

        # noinspection PyArgumentList
        self.qgs_path = QgsProject.instance().fileName()
        self.cfg_path = self.qgs_path + '.cfg'

        if not self.parent.current_repository():
            return False

        if not self.dav_server:
            LOGGER.debug("Webdav is not installed")
            return False

        # If we have the webdav URL, it means the user have 'lizmap.webdav.access'
        LOGGER.debug("Webdav is ready : {}".format(self.dav_server))
        return True

    def send_qgs_and_cfg(self) -> Tuple[bool, str, str]:
        """ Send both files. """
        url = self.dav_repository_url()
        if not url:
            return False, '', ''

        LOGGER.info("SEND two files to {}".format(url))

        loop = QEventLoop()
        LOGGER.debug(f"Local path {self.qgs_path} to {url} with token {self.auth_id}")
        self.qgs = self.webdav.store(self.qgs_path, url, self.auth_id, Qgis.ActionStart.Deferred)
        self.qgs.stored.connect(loop.quit)
        self.qgs.store()
        loop.exec_()

        error = self.qgs.errorString()
        if error:
            LOGGER.error("Error while sending the QGS file : " + error)
            return False, error, ''

        loop = QEventLoop()
        LOGGER.debug(f"Local path {self.cfg_path} to {url} with token {self.auth_id}")
        self.cfg = self.webdav.store(self.cfg_path, url, self.auth_id, Qgis.ActionStart.Deferred)
        self.cfg.stored.connect(loop.quit)
        self.cfg.store()
        loop.exec_()

        error = self.cfg.errorString()
        if error:
            LOGGER.error("Error while sending the CFG file : " + error)
            return False, error, ''

        url = self.project_url()
        LOGGER.info("Project published on {}".format(url))
        return True, '', url

    def backup_qgs(self) -> Tuple[bool, str]:
        """ Make a backup of the QGS file with an auth ID. """
        if not self.auth_id:
            return False, 'Missing auth ID'

        if self.parent and not self.parent.current_repository():
            return False, 'Missing repository'
        directory = self.parent.current_repository(RepositoryComboData.Path)
        user, password = self.extract_auth_id(self.auth_id)
        file_name = Path(self.qgs_path).name
        return self.backup_qgs_basic(directory, user, password, file_name)

    def backup_qgs_basic(
            self, directory: str, user: str, password: str, filename: str) -> Tuple[bool, Optional[str]]:
        """ Make a backup of the QGS file with login and password. """
        network_request = QNetworkRequest()
        network_request.setRawHeader(b"Authorization", self._token(user, password))
        # noinspection PyArgumentList
        destination = QUrl(self.dav_server + "{}/{}.backup".format(directory, filename)).path()
        network_request.setRawHeader(b"Destination", destination.encode("utf8"))
        # noinspection PyArgumentList
        network_request.setUrl(QUrl(self.dav_server + directory + '/' + filename))

        reply = self._custom_blocking_request(network_request, 'MOVE')

        if reply.error() == QNetworkReply.NoError:
            return True, ''

        if reply.error() == QNetworkReply.ContentNotFoundError:
            return False, 'The file does not exist on the server.'

        LOGGER.error(reply.errorString())
        return False, self.xml_reply_from_dav(reply)

    def check_qgs_exist(self) -> Tuple[bool, str]:
        """ Check if the project exists on the server with an auth ID. """
        if not self.auth_id:
            return False, 'Missing auth ID'

        if self.parent and not self.parent.current_repository(RepositoryComboData.Path):
            return False, 'Missing repository'
        directory = self.parent.current_repository(RepositoryComboData.Path)
        user, password = self.extract_auth_id(self.auth_id)
        file_name = Path(self.qgs_path).name
        return self.check_qgs_exists_basic(directory, user, password, file_name)

    def check_qgs_exists_basic(
            self, directory: str, user: str, password: str, filename: str) -> Tuple[bool, Optional[str]]:
        """ Check if the project exists on the server with login and password. """
        network_request = QNetworkRequest()
        network_request.setRawHeader(b"Authorization", self._token(user, password))
        # noinspection PyArgumentList
        network_request.setUrl(QUrl(self.dav_server + directory + '/' + filename))

        reply = self._custom_blocking_request(network_request, 'PROPFIND')

        if reply.error() == QNetworkReply.NoError:
            return True, ''

        if reply.error() == QNetworkReply.ContentNotFoundError:
            # The QGS file doesn't exist on the server
            return False, ''

        LOGGER.error(reply.errorString())
        return False, self.xml_reply_from_dav(reply)

    def make_dir(self, directory: str) -> Tuple[bool, Optional[str]]:
        """ Make a remote directory with an auth ID. """
        if not self.auth_id:
            return False, 'Missing auth ID'
        user, password = self.extract_auth_id(self.auth_id)
        return self.make_dir_basic(directory, user, password)

    def make_dir_basic(self, directory: str, user: str, password: str) -> Tuple[bool, Optional[str]]:
        """ Make a remote directory with a login and password. """
        network_request = QNetworkRequest()
        network_request.setRawHeader(b"Authorization", self._token(user, password))
        # noinspection PyArgumentList
        network_request.setUrl(QUrl(self.dav_server + directory))

        reply = self._custom_blocking_request(network_request, 'MKCOL')
        if reply.error() == QNetworkReply.NoError:
            return True, ''

        return False, self.xml_reply_from_dav(reply)

    @classmethod
    def extract_auth_id(cls, auth_id: str) -> Tuple[str, str]:
        """ Extract user and password from an auth ID. """
        conf = QgsAuthMethodConfig()
        # noinspection PyArgumentList
        QgsApplication.authManager().loadAuthenticationConfig(auth_id, conf, True)
        user = conf.config('username')
        password = conf.config('password')
        return user, password

    @classmethod
    def _custom_blocking_request(cls, request: QNetworkRequest, http: str) -> QNetworkReply:
        """ Make a custom blocking HTTP request. """
        # noinspection PyArgumentList
        network_manager = QgsNetworkAccessManager.instance()
        loop = QEventLoop()
        reply = network_manager.sendCustomRequest(request, http.encode('utf-8'))
        reply: QNetworkReply
        # noinspection PyUnresolvedReferences
        reply.finished.connect(loop.quit)
        loop.exec_()
        return reply

    @classmethod
    def _token(cls, user: str, password: str = None) -> bytes:
        """ Return the encoded token for HTTP requests. """
        token = b64encode(f"{user}:{password}".encode('utf-8')).decode("ascii")
        return "Basic {}".format(token).encode("utf-8")

    @classmethod
    def xml_reply_from_dav(cls, reply: QNetworkReply) -> str:
        """ Read the error message in a reply from the dav server. """
        data = reply.readAll()
        content = data.data().decode('utf8')
        if not content:
            msg = tr(
                "Unknown error from the webdav server. No content has been returned."
            ) + " ; Error from the HTTP request " + reply.errorString()
            return msg

        xml_dom = parseString(content)
        # noinspection PyBroadException
        try:
            root = xml_dom.firstChild
            item = root.getElementsByTagName("s:message")
            for i in item[0].childNodes:
                return i.data
        except Exception:
            return reply.errorString()
