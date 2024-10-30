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
from qgis.PyQt.QtNetwork import QHttpMultiPart, QNetworkReply, QNetworkRequest

from lizmap.definitions.definitions import RepositoryComboData, ServerComboData
from lizmap.dialogs.main import LizmapDialog
from lizmap.saas import webdav_properties
from lizmap.toolbelt.i18n import tr
from lizmap.toolbelt.strings import path_to_url

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
        self._local_file = None

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

        self.media_status = None
        self.media = None

        self.generic_status = None
        self.generic = None

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
            metadata = webdav_properties(self.parent.server_combo.currentData(ServerComboData.JsonMetadata.value))
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

    def server_url(self) -> Optional[str]:
        """ URL from the server. """
        return self.url_slash(self.parent.server_combo.currentData(ServerComboData.ServerUrl.value))

    def project_url(self) -> str:
        """ Returns the URL to the project in the web browser. """
        server = self.server_url() + 'index.php/view/map?repository={repository}&project={project}'.format(
            repository=self.parent.current_repository(RepositoryComboData.Id),
            project=Path(self.qgs_path).stem
        )
        return server

    def thumbnail_url(self) -> str:
        """ Returns the URL to the thumbnail in the web browser. """
        server = (
                self.server_url()
                + 'index.php/view/media/illustration?repository={repository}&project={project}'.format(
                    repository=self.parent.current_repository(RepositoryComboData.Id),
                    project=Path(self.qgs_path).stem
                )
        )
        return server

    def media_url(self, media: str) -> str:
        """ Returns the URL to the media in the web browser. """
        server = (
            self.server_url()
            + 'index.php/view/media/getMedia?repository={repository}&project={project}&path={media}'.format(
                repository=self.parent.current_repository(RepositoryComboData.Id),
                project=Path(self.qgs_path).stem,
                media=media
            )
        )
        return server

    def setup_webdav_dialog(self, dialog: LizmapDialog = None) -> bool:
        """ Setting up the WebDAV connection. """
        if dialog:
            self.parent = dialog

        assert self.parent

        self.config_project()

        # if not self.parent.current_repository():
        #     # TODO check why do we have this check
        #     # The webdav can exist without any current repository !
        #     # It's tricky because the list repository is filled later
        #     return False

        if not self.dav_server:
            LOGGER.debug("Webdav is not installed")
            return False

        # If we have the webdav URL, it means the user have 'lizmap.webdav.access'
        LOGGER.debug("WebDAV is ready : {}".format(self.dav_server))
        return True

    def config_project(self):
        """ Set the current project. """
        # noinspection PyArgumentList
        self.qgs_path = QgsProject.instance().fileName()
        self.cfg_path = self.qgs_path + '.cfg'

    def send_all_project_files(self) -> Tuple[bool, str, str]:
        """ Send all files related to the project : qgs, cfg and thumbnail. """
        self.config_project()
        url = self.dav_repository_url()
        if not url:
            return False, '', ''

        LOGGER.info("SEND files to {}".format(url))

        loop = QEventLoop()
        LOGGER.debug(f"Local path {self.qgs_path} to {url} with token {self.auth_id}")
        self.qgs = self.webdav.store(self.qgs_path, url, self.auth_id, Qgis.ActionStart.Deferred)
        self.qgs.stored.connect(loop.quit)
        self.qgs.store()
        loop.exec()

        error = self.qgs.errorString()
        if error:
            LOGGER.error("Error while sending the QGS file : " + error)
            return False, error, ''

        loop = QEventLoop()
        LOGGER.debug(f"Local path {self.cfg_path} to {url} with token {self.auth_id}")
        self.cfg = self.webdav.store(self.cfg_path, url, self.auth_id, Qgis.ActionStart.Deferred)
        self.cfg.stored.connect(loop.quit)
        self.cfg.store()
        loop.exec()

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
        loop.exec()

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
        loop.exec()

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
        loop.exec()

        error = self.media.errorString()
        if error:
            LOGGER.error("Error while sending the media : " + error)
            return False, error

        return True, ''

    def remove_qgs(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Remove QGS file. """
        self.config_project()
        if self.qgs_path:
            file_name = Path(self.qgs_path).name
        else:
            # Only used for tests
            file_name = self._local_file
        return self.remove_file(file_name)

    def remove_cfg(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Remove CFG file. """
        self.config_project()
        return self.remove_file(Path(self.cfg_path).name)

    def remove_thumbnail(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Remove thumbnail file. """
        self.thumbnail_path = self.parent.thumbnail_file()
        if not self.thumbnail_path:
            return None, tr('No thumbnail found on the local file system, not checking on the server.')
        return self.remove_file(self.thumbnail_path.name)

    def remove_action(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Remove action file. """
        self.action_path = self.parent.action_file()
        if not self.action_path or not self.action_path.exists():
            return None, tr('No action found on the local file system, not checking on the server.')
        return self.remove_file(self.action_path.name)

    def remove_file(self, remote_path: str):
        """ Remove a remote file path. """
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
        network_request.setUrl(QUrl(self.dav_server + directory + remote_path))

        reply = self._custom_blocking_request(network_request, 'DELETE')
        data = reply.readAll()
        content = data.data().decode('utf8')

        return True, content

    def put_file(self, file_path: Path, remote_path: Path):
        """ Send a generic file.

        :param file_path: Local file path to send.
        :param remote_path: The path on the WebDAV.
        """
        if self.parent and self.parent.current_repository(RepositoryComboData.Path):
            directory = self.parent.current_repository(RepositoryComboData.Path)
        elif self._repository:
            # Only for tests
            directory = self._repository
        else:
            return None, 'Missing repository'

        # directory = self.url_slash(directory)

        # self.make_dirs_recursive(Path(remote_path).parent, True)

        # print("Settings")
        # print(f"LOCAL PATH : {file_path}")
        # print(f"LOCAL ROOT : {local_root_path}")
        # print(f"REMOTE : {remote_path}")
        # print(f"DAV : {self.dav_server}")
        # print(f"REMOTE FULL : {self.dav_server + remote_path}")
        # print(f"DIRECTORY : {directory}")
        # print("End settings")

        remote_server = self.dav_server + directory + path_to_url(remote_path)

        loop = QEventLoop()
        LOGGER.debug(f"Local path {file_path} to {remote_server} with token {self.auth_id}")
        self.generic = self.webdav.store(str(file_path), remote_server, self.auth_id, Qgis.ActionStart.Deferred)
        self.generic.stored.connect(loop.quit)
        self.generic.store()
        loop.exec()

        error = self.generic.errorString()
        if error:
            LOGGER.error("Error while sending the generic file : " + error)
            return False, error

        return True, ''
        #
        # loop = QEventLoop()
        #
        # self.qgs = self.webdav.store(str(file_path), self.dav_server + remote_path, self.auth_id, Qgis.ActionStart.Deferred)
        # self.qgs.stored.connect(loop.quit)
        # self.qgs.store()
        # loop.exec_()
        #
        # error = self.qgs.errorString()
        # return error
        #
        # network_request = QNetworkRequest()
        # network_request.setRawHeader(b"Authorization", self._token(user, password))
        # # noinspection PyArgumentList
        # network_request.setUrl(QUrl(self.dav_server + remote_path))
        # # print(network_request.url())
        #
        # qt_file = QFile(str(file_path))
        # if qt_file.open(QFile.ReadOnly):
        #     data = qt_file.readAll()
        #     file_size = qt_file.size()
        #     qt_file.close()
        # else:
        #     return False, 'File is not open, error in the code'
        #
        # # print(data)
        # multi_part = QHttpMultiPart(QHttpMultiPart.FormDataType)
        # # network_request.set
        # file_part = QHttpPart()
        # # file_part.setHeader(QNetworkRequest.ContentDispositionHeader, "form-data")
        # file_part.setHeader(QNetworkRequest.ContentTypeHeader, "text/plain")
        # # file_part.setHeader(QNetworkRequest.ContentDispositionHeader, "form-data; name=\"file\"; filename=\"file.txt\"")
        # file_part.setHeader(QNetworkRequest.ContentLengthHeader, file_size)
        # file_part.setBody(data)
        # multi_part.append(file_part)
        #
        # reply = self._custom_blocking_request(network_request, 'POST', multi_part)
        #
        # data = reply.readAll()
        # content = data.data().decode('utf8')
        #
        # return True, content
        #
        # if reply.error() == QNetworkReply.NoError:
        #     # No error occurred, return the parsed response without any error message
        #     return self.parse_propfind_response(content), ''
        #
        # # noinspection PyArgumentList
        # network_request.setUrl(QUrl(self.dav_server + directory + filename))
        #
        # url += remote_path
        #
        # # print("BOB")
        # # print(file_path)
        # # print(remote_path)
        #
        # return True, ''

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
        self.config_project()
        if self.qgs_path:
            file_name = Path(self.qgs_path).name
        else:
            # Only used for tests
            file_name = self._local_file
        return self.file_stats(file_name)

    def file_stats_cfg(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Fetch file stats on the server about CFG file. """
        self.config_project()
        return self.file_stats(Path(self.cfg_path).name)

    def file_stats_thumbnail(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Fetch file stats on the server about thumbnail. """
        self.thumbnail_path = self.parent.thumbnail_file()
        if not self.thumbnail_path:
            return None, tr('No thumbnail found on the local file system, not checking on the server.')
        return self.file_stats(self.thumbnail_path.name)

    def file_stats_action(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Fetch file stats on the server about action. """
        self.action_path = self.parent.action_file()
        if not self.action_path or not self.action_path.exists():
            return None, tr('No action found on the local file system, not checking on the server.')
        return self.file_stats(self.action_path.name)

    def file_stats_media(self) -> Tuple[Optional[PropFindFileResponse], str]:
        """ Fetch file stats on the server about media folder. """
        return self.file_stats("media")

    def file_stats(self, filename: str) -> Tuple[Optional[PropFindFileResponse], Optional[str]]:
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
        # print(network_request.url())
        reply = self._custom_blocking_request(network_request, 'PROPFIND')

        data = reply.readAll()
        content = data.data().decode('utf8')
        if reply.error() == QNetworkReply.NetworkError.NoError:
            # No error occurred, return the parsed response without any error message
            return self.parse_propfind_response(content), ''

        if reply.error() == QNetworkReply.NetworkError.ContentNotFoundError:
            # The file doesn't exist on the server
            # Return None and empty error message
            return None, ''

        LOGGER.error(reply.errorString())
        # Return None but try to parse the error message
        return None, self.xml_reply_from_dav(reply)

    def make_dirs_recursive(self, directory: Path, exists_ok: bool = True) -> Tuple[bool, Optional[str]]:
        """ Make a remote directory with an auth ID. """
        # print(directory)
        if self.auth_id:
            user, password = self.extract_auth_id(self.auth_id)
        elif self._user:
            # Only for tests
            user, password = self._user, self._password
        else:
            return False, 'Missing auth ID'
        return self.make_dirs_recursive_basic(directory, exists_ok, user, password)

    def make_dirs_recursive_basic(self, file_path: Path, exists_ok: bool, user: str, password: str):
        """ Make all dirs if necessary. """
        if self.parent and self.parent.current_repository(RepositoryComboData.Path):
            directory = self.parent.current_repository(RepositoryComboData.Path)
        elif self._repository:
            # Only for tests
            directory = self._repository
        else:
            return None, 'Missing repository'

        directory = self.url_slash(directory)

        # result, msg = self.make_dir_basic(directory, exists_ok, user, password)
        # if not result:
        #     return False, msg

        # First create recursively all needed directories
        parents = list(file_path.parents)
        parents.reverse()
        for folder in parents:
            result, msg = self.make_dir_basic(directory + str(folder), exists_ok, user, password)
            if not result:
                return False, msg

        if file_path.suffix:
            return True, ''
        return self.make_dir_basic(directory + str(file_path), exists_ok, user, password)

    def make_dir(self, directory: str, exists_ok: bool = False) -> Tuple[bool, Optional[str]]:
        """ Make a remote directory with an auth ID. """
        if self.auth_id:
            user, password = self.extract_auth_id(self.auth_id)
        elif self._user:
            # Only for tests
            user, password = self._user, self._password
        else:
            return False, 'Missing auth ID'
        return self.make_dir_basic(directory, exists_ok, user, password)

    def make_dir_basic(self, directory: str, exists_ok: bool, user: str, password: str) -> Tuple[bool, Optional[str]]:
        """ Make a remote directory with a login and password. """
        network_request = QNetworkRequest()
        network_request.setRawHeader(b"Authorization", self._token(user, password))
        # noinspection PyArgumentList
        network_request.setUrl(QUrl(self.dav_server + directory))

        reply = self._custom_blocking_request(network_request, 'MKCOL')
        if reply.error() == QNetworkReply.NetworkError.NoError:
            return True, ''

        error = self.xml_reply_from_dav(reply)

        if error == 'The resource you tried to create already exists':
            return exists_ok, error

        return False, error

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
    def _custom_blocking_request(cls, request: QNetworkRequest, http: str, multi_part: QHttpMultiPart = None) -> QNetworkReply:
        """ Make a custom blocking HTTP request. """
        # noinspection PyArgumentList
        network_manager = QgsNetworkAccessManager.instance()
        loop = QEventLoop()
        reply = network_manager.sendCustomRequest(request, http.encode('utf-8'), multi_part)
        reply: QNetworkReply
        # noinspection PyUnresolvedReferences
        reply.finished.connect(loop.quit)
        loop.exec()
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

        # Transform from UTC to local timezone
        qdate = QDateTime.fromString(last_modified, Qt.DateFormat.RFC2822Date)
        qdate.setTimeSpec(Qt.UTC)
        qdate_locale = qdate.toLocalTime()
        date_string = qdate_locale.toString(QLocale().dateFormat(QLocale.ShortFormat))
        date_string += " "
        date_string += qdate_locale.toString("hh:mm:ss")

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
        self._local_file = file_name
