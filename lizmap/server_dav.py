__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging

from base64 import b64encode
from collections import namedtuple
from pathlib import Path
from typing import Optional, Tuple, Union
from xml.dom.minidom import parseString

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsExternalStorage,
    QgsNetworkAccessManager,
    QgsProject,
)
from qgis.PyQt.QtCore import QDateTime, QEventLoop, QLocale, Qt, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from lizmap.definitions.definitions import RepositoryComboData, ServerComboData
from lizmap.dialogs.main import LizmapDialog
from lizmap.toolbelt.i18n import tr

LOGGER = logging.getLogger("Lizmap")

PropFindFileResponse = namedtuple(
    'PropFindFile',
    [
        'http_code', 'etag', 'content_length', 'last_modified', 'last_modified_pretty', 'href'
    ])

PropFindDirResponse = namedtuple(
    'PropFindDir',
    [
        'http_code', 'quota_used_bytes', 'quota_available_bytes', 'last_modified', 'last_modified_pretty', 'href'
    ])


class WebDav:

    def __init__(self, dav_server: str = None, auth_id: str = None):
        """ Constructor. """
        super().__init__()
        # Either from the dialog
        self.parent: Optional[LizmapDialog] = None

        # Or from constructor
        self._dav_server = dav_server
        self._auth_id = auth_id

        # Only used for testing, it must come from the UI otherwise.
        self._user = None
        self._password = None
        self._repository = None

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

        self.thumbnail_path = None
        self.thumbnail_status = None
        self.thumbnail = None

        self.action_path = None
        self.action_status = None
        self.action = None

        self.media_path = None
        self.media_status = None
        self.media = None

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

        return self.url_slash(self._dav_server)

    @staticmethod
    def url_slash(url: str) -> str:
        """ Append slash to the URL at the end if needed. """
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
        server = self.url_slash(self.parent.server_combo.currentData(ServerComboData.ServerUrl.value))
        server += 'index.php/view/map?repository={repository}&project={project}'.format(
            repository=self.parent.current_repository(RepositoryComboData.Id),
            project=Path(self.qgs_path).stem
        )
        return server

    def thumbnail_url(self) -> str:
        """ Returns the URL to the thumbnail in the web browser. """
        server = self.url_slash(self.parent.server_combo.currentData(ServerComboData.ServerUrl.value))
        server += 'index.php/view/media/illustration?repository={repository}&project={project}'.format(
            repository=self.parent.current_repository(RepositoryComboData.Id),
            project=Path(self.qgs_path).stem
        )
        return server

    def media_url(self, media: str) -> str:
        """ Returns the URL to the media in the web browser. """
        server = self.url_slash(self.parent.server_combo.currentData(ServerComboData.ServerUrl.value))
        server += 'index.php/view/media/getMedia?repository={repository}&project={project}&path={media}'.format(
            repository=self.parent.current_repository(RepositoryComboData.Id),
            project=Path(self.qgs_path).stem,
            media=media
        )
        return server

    def setup_webdav_dialog(self, dialog: LizmapDialog = None) -> bool:
        """ Setting up the WebDAV connection. """
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
        LOGGER.debug("WebDAV is ready : {}".format(self.dav_server))
        return True

    def send_all_project_files(self) -> Tuple[bool, str, str]:
        """ Send all files related to the project : qgs, cfg and thumbnail. """
        url = self.dav_repository_url()
        if not url:
            return False, '', ''

        LOGGER.info("SEND files to {}".format(url))

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
            LOGGER.error("Error while sending the Lizmap configuration file : " + error)
            return False, error, ''

        url = self.project_url()
        LOGGER.info("Project published on {}".format(url))
        return True, '', url

    def send_thumbnail(self) -> tuple[bool, str]:
        """ Send the thumbnail to the WebDAV server. """
        if not self.parent:
            return False, ''

        self.thumbnail_path = self.parent.thumbnail_file()
        if not self.thumbnail_path:
            return False, ''

        url = self.dav_repository_url()
        if not url:
            return False, ''

        loop = QEventLoop()
        LOGGER.debug(f"Local path {self.thumbnail_path} to {url} with token {self.auth_id}")
        self.thumbnail = self.webdav.store(str(self.thumbnail_path), url, self.auth_id, Qgis.ActionStart.Deferred)
        self.thumbnail.stored.connect(loop.quit)
        self.thumbnail.store()
        loop.exec_()

        error = self.thumbnail.errorString()
        if error:
            LOGGER.error("Error while sending the thumbnail : " + error)
            return False, error

        return True, self.thumbnail_url()

    def send_action(self) -> tuple[bool, str]:
        """ Send the thumbnail to the WebDAV server. """
        if not self.parent:
            return False, ''

        self.action_path = self.parent.action_file()
        if not self.action_path or not self.action_path.exists():
            return False, ''

        url = self.dav_repository_url()
        if not url:
            return False, ''

        loop = QEventLoop()
        LOGGER.debug(f"Local path {self.action_path} to {url} with token {self.auth_id}")
        self.action = self.webdav.store(str(self.action_path), url, self.auth_id, Qgis.ActionStart.Deferred)
        self.action.stored.connect(loop.quit)
        self.action.store()
        loop.exec_()

        error = self.action.errorString()
        if error:
            LOGGER.error("Error while sending the thumbnail : " + error)
            return False, error

        return True, ''

    def send_media(self, file_path: Path) -> tuple[bool, str]:
        """ Send the media to the WebDAV server. """
        if not self.parent:
            return False, ''

        url = self.dav_repository_url()
        if not url:
            return False, tr('No repository URL')

        url += 'media/'

        loop = QEventLoop()
        LOGGER.debug(f"Local path {file_path} to {url} with token {self.auth_id}")
        self.media = self.webdav.store(str(file_path), url, self.auth_id, Qgis.ActionStart.Deferred)
        self.media.stored.connect(loop.quit)
        self.media.store()
        loop.exec_()

        error = self.media.errorString()
        if error:
            LOGGER.error("Error while sending the media : " + error)
            return False, error

        return True, ''

    # def backup_qgs(self) -> Tuple[bool, str]:
    #     """ Make a backup of the QGS file with an auth ID. """
    #     if not self.auth_id:
    #         return False, 'Missing auth ID'
    #
    #     if self.parent and not self.parent.current_repository():
    #         return False, 'Missing repository'
    #     directory = self.parent.current_repository(RepositoryComboData.Path)
    #     user, password = self.extract_auth_id(self.auth_id)
    #     file_name = Path(self.qgs_path).name
    #     return self.backup_qgs_basic(directory, user, password, file_name)
    #
    # def backup_qgs_basic(
    #         self, directory: str, user: str, password: str, filename: str) -> Tuple[bool, Optional[str]]:
    #     """ Make a backup of the QGS file with login and password. """
    #     network_request = QNetworkRequest()
    #     network_request.setRawHeader(b"Authorization", self._token(user, password))
    #     # noinspection PyArgumentList
    #     destination = QUrl(self.dav_server + "{}/{}.backup".format(directory, filename)).path()
    #     network_request.setRawHeader(b"Destination", destination.encode("utf8"))
    #     # noinspection PyArgumentList
    #     network_request.setUrl(QUrl(self.dav_server + directory + '/' + filename))
    #
    #     reply = self._custom_blocking_request(network_request, 'MOVE')
    #
    #     if reply.error() == QNetworkReply.NoError:
    #         return True, ''
    #
    #     if reply.error() == QNetworkReply.ContentNotFoundError:
    #         return False, 'The file does not exist on the server.'
    #
    #     LOGGER.error(reply.errorString())
    #     return False, self.xml_reply_from_dav(reply)

    def check_exists_qgs(self) -> Tuple[bool, Optional[str]]:
        """ Check if the project exists on the server. """
        result, error_msg = self.file_stats_qgs()
        if result and "200" in result.http_code:
            return True, ''

        return False, error_msg

    def file_stats_qgs(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Fetch file stats on the server about QGS file. """
        if self.qgs_path:
            file_name = Path(self.qgs_path).name
        else:
            # Only used for tests
            file_name = self._file
        return self._file_stats(file_name)

    def file_stats_cfg(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Fetch file stats on the server about CFG file. """
        return self._file_stats(Path(self.cfg_path).name)

    def file_stats_thumbnail(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Fetch file stats on the server about thumbnail. """
        self.thumbnail_path = self.parent.thumbnail_file()
        if not self.thumbnail_path:
            return None, 'No thumbnail was set'
        return self._file_stats(self.thumbnail_path.name)

    def file_stats_action(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Fetch file stats on the server about action. """
        return self._file_stats(self.action_path.name)

    def file_stats_media(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Fetch file stats on the server about media folder. """
        return self._file_stats("media")

    def _file_stats(self, filename: str) -> Tuple[Optional[PropFindFileResponse], Optional[str]]:
        """ Get file stats on a file. """
        if self.auth_id:
            user, password = self.extract_auth_id(self.auth_id)
        elif self._user:
            # Only for tests
            user, password = self._user, self._password
        else:
            return None, 'Missing auth ID'

        if self.parent and self.parent.current_repository(RepositoryComboData.Path):
            directory = self.parent.current_repository(RepositoryComboData.Path)
        elif self._repository:
            # Only for tests
            directory = self._repository
        else:
            return None, 'Missing repository'

        network_request = QNetworkRequest()
        network_request.setRawHeader(b"Authorization", self._token(user, password))

        directory = self.url_slash(directory)

        # noinspection PyArgumentList
        network_request.setUrl(QUrl(self.dav_server + directory + filename))

        reply = self._custom_blocking_request(network_request, 'PROPFIND')

        data = reply.readAll()
        content = data.data().decode('utf8')
        if reply.error() == QNetworkReply.NoError:
            # No error occurred, return the parsed response without any error message
            return self.parse_propfind_response(content), ''

        if reply.error() == QNetworkReply.ContentNotFoundError:
            # The file doesn't exist on the server
            # Return None and empty error message
            return None, ''

        LOGGER.error(reply.errorString())
        # Return None but try to parse the error message
        return None, self.xml_reply_from_dav(reply)

    def make_dir(self, directory: str) -> Tuple[bool, Optional[str]]:
        """ Make a remote directory with an auth ID. """
        if self.auth_id:
            user, password = self.extract_auth_id(self.auth_id)
        elif self._user:
            # Only for tests
            user, password = self._user, self._password
        else:
            return False, 'Missing auth ID'
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

        # noinspection PyBroadException
        try:
            xml_dom = parseString(content)
            root = xml_dom.firstChild
            item = root.getElementsByTagName("s:message")
            for i in item[0].childNodes:
                return i.data
        except Exception:
            return f'{content} - {reply.errorString()}'

    @classmethod
    def parse_propfind_response(cls, xml_data: str) -> Union[PropFindFileResponse, PropFindDirResponse]:
        """ Parse a response from a PROPFIND request. """
        xml_dom = parseString(xml_data)
        root = xml_dom.firstChild

        # HTTP
        node = root.getElementsByTagName("d:status")[0]
        http = node.childNodes[0].data

        # Href
        node = root.getElementsByTagName("d:href")[0]
        href = node.childNodes[0].data

        # Last modified
        node = root.getElementsByTagName("d:getlastmodified")[0]
        last_modified = node.childNodes[0].data

        qdate = QDateTime.fromString(last_modified, Qt.DateFormat.RFC2822Date)
        date_string = qdate.toString(QLocale().dateFormat(QLocale.ShortFormat))
        date_string += " "
        date_string += qdate.toString("hh:mm:ss")

        # Collections
        node = root.getElementsByTagName("d:resourcetype")
        if node[0].getElementsByTagName("d:collection"):
            is_dir = True
        else:
            is_dir = False

        if is_dir:
            # Quota used
            node = root.getElementsByTagName("d:quota-used-bytes")[0]
            quota_used = node.childNodes[0].data

            # Quota available
            node = root.getElementsByTagName("d:quota-available-bytes")[0]
            quota_available = node.childNodes[0].data

            return PropFindDirResponse(http, quota_used, quota_available, last_modified, date_string, href)
        else:
            # Length
            node = root.getElementsByTagName("d:getcontentlength")[0]
            length = node.childNodes[0].data

            # Etag
            node = root.getElementsByTagName("d:getetag")[0]
            etag = node.childNodes[0].data.strip('"')

            return PropFindFileResponse(http, etag, length, last_modified, date_string, href)

    def _for_test(self, user: str, password: str, repository: str, file_name: str):
        """ Only for testing purpose. """
        self._user = user
        self._password = password
        self._repository = repository
        self._file = file_name
