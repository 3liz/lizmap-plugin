"""HTTP client shared by the requests to the Lizmap server: authentication, errors, transfers.

Requests are synchronous, with a local event loop, so they must be run in a ``QgsTask`` to keep
the interface responsive, except short ones. ``QgsNetworkAccessManager`` gives an instance per thread,
which applies the proxy, SSL and timeout settings of QGIS.
"""

from __future__ import annotations

import json
import re

from base64 import b64encode
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qgis.core import QgsApplication, QgsNetworkAccessManager
from qgis.PyQt.QtCore import QEventLoop, QIODevice, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from lizmap.sync.backends.base import BackendCanceled, BackendError

if TYPE_CHECKING:
    from qgis.core import QgsFeedback

_SABRE_MESSAGE = re.compile(r"<s:message>(.*?)</s:message>", re.DOTALL)


@dataclass
class Response:
    """Response of a request.

    :param status: HTTP status.
    :param body: Body, empty if written in a file.
    :param etag: Value of the ETag header, if any.
    :param length: Value of the Content-Length header, if any.
    :param received: Number of bytes of the body received.
    """

    status: int
    body: bytes
    etag: str | None
    length: int | None = None
    received: int = 0


def error_message(body: bytes, default: str) -> str:
    """Extract the message of an error returned by the server.

    :param body: Body of the response: an XML error from the WebDAV server, or a JSON error from the API.
    :param default: Message to use if the body doesn't contain any message.
    :return: The message.
    """
    text = body.decode("utf-8", errors="replace")
    match = _SABRE_MESSAGE.search(text)
    if match and match.group(1).strip():
        return match.group(1).strip()
    try:
        data = json.loads(text)
    except ValueError:
        return default
    if isinstance(data, dict) and isinstance(data.get("message"), str) and data["message"].strip():
        return data["message"].strip()
    return default


def _is_network_error(error: QNetworkReply.NetworkError) -> bool:
    """Tell if an error of a reply comes from the network, not from an HTTP status.

    Errors from 1 to 199 are connection and proxy errors, such as an interrupted connection.
    Errors from 201 are HTTP statuses, such as 404, handled with the status of the response.

    :param error: Error of the reply.
    :return: True for a network error.
    """
    code = error.value if hasattr(error, "value") else int(error)
    return 0 < code < 200


class HttpClient:
    """Requests to the Lizmap server, authenticated.

    :param auth_id: QGIS authentication configuration, with the Lizmap login and password.
    :param credentials: Login and password, used only when there isn't any authentication configuration,
        for instance in tests.
    """

    def __init__(self, auth_id: str | None = None, credentials: tuple[str, str] | None = None):
        self.auth_id = auth_id
        self.credentials = credentials

    def _send(
        self,
        verb: str,
        url: QUrl,
        headers: dict[str, str] | None = None,
        body: QIODevice | None = None,
        output: QIODevice | None = None,
        feedback: QgsFeedback | None = None,
    ) -> Response:
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

        # Without cookies: only the credentials authenticate the request, never a session opened before
        request.setAttribute(
            QNetworkRequest.Attribute.CookieLoadControlAttribute, QNetworkRequest.LoadControl.Manual
        )
        request.setAttribute(
            QNetworkRequest.Attribute.CookieSaveControlAttribute, QNetworkRequest.LoadControl.Manual
        )

        reply = QgsNetworkAccessManager.instance().sendCustomRequest(request, verb.encode("ascii"), body)
        chunks: list[bytes] = []
        received = [0]

        def read():
            """Read the available data of the response."""
            data = reply.readAll()
            received[0] += len(data)
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
            if status is None or _is_network_error(reply.error()):
                # No HTTP response at all, or a connection interrupted during the transfer
                raise BackendError(reply.errorString())

            etag = bytes(reply.rawHeader(b"ETag")).decode("ascii", errors="replace") or None
            length = reply.header(QNetworkRequest.KnownHeaders.ContentLengthHeader)
            return Response(
                status=int(status),
                body=b"".join(chunks),
                etag=etag,
                length=int(length) if length is not None else None,
                received=received[0],
            )
        finally:
            if feedback:
                feedback.canceled.disconnect(reply.abort)
            reply.deleteLater()

    @staticmethod
    def _check(response: Response, expected: tuple[int, ...], action: str):
        """Raise an error if the status of the response is not expected.

        :param response: The response.
        :param expected: The expected HTTP statuses.
        :param action: Description of the request, for the message.
        :raises BackendError: If the status is not expected.
        """
        if response.status in expected:
            return
        message = error_message(response.body, f"HTTP error {response.status}")
        raise BackendError(f"{action} : {message}", response.status)
