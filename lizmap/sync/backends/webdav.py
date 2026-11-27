"""WebDAV transport, with the Lizmap WebDAV module 1.3 or newer.

Requests are synchronous, with a local event loop, so they must be run in a ``QgsTask`` to keep
the interface responsive. ``QgsNetworkAccessManager`` gives an instance per thread, which applies
the proxy, SSL and timeout settings of QGIS.
"""

from __future__ import annotations

import os
import re

from base64 import b64encode
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from qgis.core import QgsApplication, QgsNetworkAccessManager
from qgis.PyQt.QtCore import QEventLoop, QFile, QIODevice, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest

from lizmap.sync.backends.base import BackendCanceled, BackendError
from lizmap.sync.filters import INTERNAL_PREFIX
from lizmap.sync.manifest import ManifestError, parse_manifest_json

if TYPE_CHECKING:
    from pathlib import Path

    from qgis.core import QgsFeedback

    from lizmap.sync.manifest import RemoteManifest

# Features of the WebDAV module needed by the synchronisation
REQUIRED_FEATURES = ("manifest", "sha256", "atomic-put", "fs-errors", "delete-empty-only")

# Header asking the server to delete a directory only if it's empty
EMPTY_ONLY_HEADER = {"X-Lizmap-Delete": "empty-only"}

# Prefix of local temporary files during a download, always excluded from the synchronisation
DOWNLOAD_PREFIX = INTERNAL_PREFIX + "download-"

# HTTP status of a MKCOL on an existing directory
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_NOT_FOUND = 404

_SABRE_MESSAGE = re.compile(r"<s:message>(.*?)</s:message>", re.DOTALL)


def encode_path(path: str) -> str:
    """Encode a relative path for an URL, segment by segment.

    :param path: Relative path, with "/" as separator.
    :return: The percent-encoded path.
    """
    return "/".join(quote(segment, safe="") for segment in path.split("/"))


@dataclass(frozen=True)
class WebDavServer:
    """WebDAV capabilities of a Lizmap server, read from its metadata.

    :param url: URL of the WebDAV root, with a trailing slash.
    :param projects_path: Directory of the repositories, relative to the WebDAV root.
    :param features: Features of the WebDAV module.
    :param manifest_version: Version of the manifest format, empty if not supported.
    :param checksum_max_size: Files bigger than this size don't have a checksum, None for no limit.
    """

    url: str
    projects_path: str
    features: tuple[str, ...]
    manifest_version: str
    checksum_max_size: int | None

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any] | None) -> WebDavServer | None:
        """Read the WebDAV capabilities from the metadata of the server.

        :param metadata: The JSON metadata of Lizmap Web Client.
        :return: The capabilities, None if the WebDAV module is not available for the user.
        """
        webdav = (metadata or {}).get("webdav")
        if not isinstance(webdav, dict) or not webdav.get("url"):
            return None

        features = webdav.get("features")
        max_size = webdav.get("checksum_max_size")
        return cls(
            url=str(webdav["url"]).rstrip("/") + "/",
            projects_path=str(webdav.get("projects_path") or ""),
            features=tuple(str(f) for f in features) if isinstance(features, list) else (),
            manifest_version=str(webdav.get("manifest_version") or ""),
            checksum_max_size=max_size if isinstance(max_size, int) else None,
        )

    @property
    def supports_sync(self) -> bool:
        """Tell if the WebDAV module is recent enough for the synchronisation.

        :return: True if all required features and the manifest version 1 are available.
        """
        return all(f in self.features for f in REQUIRED_FEATURES) and self.manifest_version.startswith("1.")

    def repository_url(self, repository_path: str) -> str:
        """URL of a Lizmap repository directory.

        :param repository_path: Path of the repository, from the metadata of the server.
        :return: The URL, with a trailing slash.
        :raises ValueError: If the repository is not in the root directory of the repositories,
            it can't be reached with WebDAV.
        """
        if not repository_path or repository_path.startswith("/") or ".." in repository_path.split("/"):
            raise ValueError(f"The repository path '{repository_path}' can't be reached with WebDAV.")

        relative = f"{self.projects_path.strip('/')}/{repository_path.strip('/')}".strip("/")
        return self.url + encode_path(relative) + "/"


@dataclass
class _Response:
    """Response of a request.

    :param status: HTTP status.
    :param body: Body, empty if written in a file.
    :param etag: Value of the ETag header, if any.
    """

    status: int
    body: bytes
    etag: str | None


def _error_message(body: bytes, default: str) -> str:
    """Extract the message of an error returned by the server.

    :param body: Body of the response, an XML error from Sabre if possible.
    :param default: Message to use if the body doesn't contain any message.
    :return: The message.
    """
    match = _SABRE_MESSAGE.search(body.decode("utf-8", errors="replace"))
    if match and match.group(1).strip():
        return match.group(1).strip()
    return default


class WebDavBackend:
    """A directory on the server, reached with WebDAV.

    :param root_url: URL of the directory, such as ``WebDavServer.repository_url()``.
    :param auth_id: QGIS authentication configuration, with the Lizmap login and password.
    :param credentials: Login and password, used only when there isn't any authentication configuration,
        for instance in tests.
    """

    def __init__(self, root_url: str, auth_id: str | None = None, credentials: tuple[str, str] | None = None):
        self.root_url = root_url.rstrip("/") + "/"
        self.auth_id = auth_id
        self.credentials = credentials

    def url(self, path: str = "", directory: bool = False) -> QUrl:
        """Build the URL of a path.

        :param path: Relative path, empty for the root directory.
        :param directory: Add a trailing slash, for a directory.
        :return: The URL.
        """
        url = self.root_url + encode_path(path) if path else self.root_url
        if directory and not url.endswith("/"):
            url += "/"
        return QUrl(url)

    def _send(
        self,
        verb: str,
        url: QUrl,
        headers: dict[str, str] | None = None,
        body: QIODevice | None = None,
        output: QIODevice | None = None,
        feedback: QgsFeedback | None = None,
    ) -> _Response:
        """Send a request and wait for the response.

        :param verb: HTTP method.
        :param url: The URL.
        :param headers: Extra HTTP headers.
        :param body: Body to send, read progressively.
        :param output: Where to write the body of the response, progressively. In memory if None.
        :param feedback: To cancel the request and follow the progress.
        :return: The response, whatever its HTTP status.
        :raises BackendCanceled: If the user canceled.
        :raises BackendError: For a network error, without HTTP status.
        """
        if feedback and feedback.isCanceled():
            raise BackendCanceled()

        # Headers and authentication
        request = QNetworkRequest(url)
        for key, value in (headers or {}).items():
            request.setRawHeader(key.encode("ascii"), value.encode("utf-8"))
        if self.auth_id:
            QgsApplication.authManager().updateNetworkRequest(request, self.auth_id)
        elif self.credentials:
            token = b64encode(":".join(self.credentials).encode("utf-8"))
            request.setRawHeader(b"Authorization", b"Basic " + token)
        if body is not None:
            request.setHeader(QNetworkRequest.KnownHeaders.ContentLengthHeader, body.size())

        reply = QgsNetworkAccessManager.instance().sendCustomRequest(request, verb.encode("ascii"), body)
        chunks: list[bytes] = []

        def read():
            """Read the available data of the response."""
            data = reply.readAll()
            if output is not None:
                output.write(data)
            else:
                chunks.append(bytes(data))

        def progress(done: int, total: int):
            """Report the progress of the transfer.

            :param done: Bytes already transferred.
            :param total: Total bytes, -1 or 0 if unknown.
            """
            if feedback and total > 0:
                feedback.setProgress(100.0 * done / total)

        # Wait for the end of the request, reading the response progressively
        loop = QEventLoop()
        reply.readyRead.connect(read)
        reply.finished.connect(loop.quit)
        reply.uploadProgress.connect(progress)
        reply.downloadProgress.connect(progress)
        if feedback:
            feedback.canceled.connect(reply.abort)
        if not reply.isFinished():
            loop.exec()
        read()

        try:
            if feedback and feedback.isCanceled():
                raise BackendCanceled()

            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if status is None:
                # No HTTP response at all
                raise BackendError(reply.errorString())

            etag = bytes(reply.rawHeader(b"ETag")).decode("ascii", errors="replace") or None
            return _Response(status=int(status), body=b"".join(chunks), etag=etag)
        finally:
            if feedback:
                feedback.canceled.disconnect(reply.abort)
            reply.deleteLater()

    @staticmethod
    def _check(response: _Response, expected: tuple[int, ...], action: str):
        """Raise an error if the status of the response is not expected.

        :param response: The response.
        :param expected: The expected HTTP statuses.
        :param action: Description of the request, for the message.
        :raises BackendError: If the status is not expected.
        """
        if response.status in expected:
            return
        message = _error_message(response.body, f"HTTP error {response.status}")
        raise BackendError(f"{action} : {message}", response.status)

    def fetch_manifest(self, feedback: QgsFeedback | None = None) -> RemoteManifest:
        """Fetch the recursive listing of the directory.

        :param feedback: To cancel the request.
        :return: The manifest.
        :raises BackendError: If the request failed or the manifest is not valid.
        """
        url = self.url(directory=True)
        url.setQuery("manifest")
        response = self._send("GET", url, headers={"Accept": "application/json"}, feedback=feedback)
        self._check(response, (200,), "Manifest")
        try:
            return parse_manifest_json(response.body)
        except ManifestError as e:
            raise BackendError(str(e)) from e

    def make_directory(self, path: str, feedback: QgsFeedback | None = None):
        """Create a directory, its parent must exist. An existing directory is not an error.

        :param path: Relative path of the directory, empty for the root directory itself.
        :param feedback: To cancel the request.
        :raises BackendError: If the directory can't be created.
        """
        response = self._send("MKCOL", self.url(path, directory=True), feedback=feedback)
        # 405: the directory already exists
        self._check(response, (201, HTTP_METHOD_NOT_ALLOWED), f"Directory '{path}'")

    def upload(
        self, local_file: Path, path: str, etag: str | None, feedback: QgsFeedback | None = None
    ) -> str | None:
        """Send a file, its parent directory must exist.

        The file is sent with a precondition: "If-Match" with the expected ETag when replacing a file,
        "If-None-Match: *" for a new file, so a file modified by someone else is never overwritten.

        :param local_file: The local file to send.
        :param path: Relative path on the server.
        :param etag: ETag of the file to replace, None if the file must not exist yet.
        :param feedback: To cancel the request and follow the progress.
        :return: The ETag of the new file, if given by the server.
        :raises BackendError: If the upload failed, ``is_conflict`` if the file changed in the meantime.
        """
        source = QFile(str(local_file))
        if not source.open(QIODevice.OpenModeFlag.ReadOnly):
            raise BackendError(f"Upload '{path}' : {source.errorString()}")

        headers = {"If-Match": etag} if etag else {"If-None-Match": "*"}
        try:
            response = self._send("PUT", self.url(path), headers=headers, body=source, feedback=feedback)
        finally:
            source.close()

        self._check(response, (200, 201, 204), f"Upload '{path}'")
        return response.etag

    def download(self, path: str, local_file: Path, feedback: QgsFeedback | None = None) -> str | None:
        """Fetch a file. The local file is replaced only once the download is complete.

        :param path: Relative path on the server.
        :param local_file: The local file to write, its parent directory is created if needed.
        :param feedback: To cancel the request and follow the progress.
        :return: The ETag of the downloaded file, if given by the server.
        :raises BackendError: If the download failed.
        """
        local_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = local_file.parent.joinpath(DOWNLOAD_PREFIX + local_file.name)

        output = QFile(str(temporary))
        if not output.open(QIODevice.OpenModeFlag.WriteOnly | QIODevice.OpenModeFlag.Truncate):
            raise BackendError(f"Download '{path}' : {output.errorString()}")

        try:
            try:
                response = self._send("GET", self.url(path), output=output, feedback=feedback)
            finally:
                output.close()
            self._check(response, (200,), f"Download '{path}'")

            # Replace the local file in a single operation
            os.replace(temporary, local_file)
        finally:
            temporary.unlink(missing_ok=True)

        return response.etag

    def delete(self, path: str, etag: str | None, feedback: QgsFeedback | None = None):
        """Delete a file. A file already deleted is not an error.

        :param path: Relative path on the server.
        :param etag: Expected ETag of the file, None to delete it whatever its content.
        :param feedback: To cancel the request.
        :raises BackendError: If the deletion failed, ``is_conflict`` if the file changed in the meantime.
        """
        headers = {"If-Match": etag} if etag else {}
        response = self._send("DELETE", self.url(path), headers=headers, feedback=feedback)
        self._check(response, (200, 204, HTTP_NOT_FOUND), f"Delete '{path}'")

    def delete_empty_directory(self, path: str, feedback: QgsFeedback | None = None):
        """Delete a directory, only if it's empty. A directory already deleted is not an error.

        :param path: Relative path of the directory.
        :param feedback: To cancel the request.
        :raises BackendError: If the directory is not empty (409) or can't be deleted.
        """
        response = self._send(
            "DELETE", self.url(path, directory=True), headers=EMPTY_ONLY_HEADER, feedback=feedback
        )
        self._check(response, (200, 204, HTTP_NOT_FOUND), f"Delete the directory '{path}'")
