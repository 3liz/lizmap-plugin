"""Administration API of Lizmap Web Client, to create a repository.

The creation of a repository is available since Lizmap Web Client 3.10, for a user with the rights
"lizmap.admin.repositories.view" and "lizmap.admin.repositories.create".
"""

from __future__ import annotations

import json
import re
import unicodedata

from typing import TYPE_CHECKING
from urllib.parse import quote, urlencode

from qgis.PyQt.QtCore import QBuffer, QByteArray, QIODevice, QUrl

from lizmap.sync.backends.base import BackendError
from lizmap.sync.backends.http import HttpClient

if TYPE_CHECKING:
    from qgis.core import QgsFeedback

# Rules of Lizmap Web Client for the identifier and the directory of a repository
REPOSITORY_KEY = re.compile(r"^[a-z0-9_]+$")
REPOSITORY_FOLDER = re.compile(r"^[a-zA-Z0-9_]+$")

# Status of the directories in the root of the repositories
PATH_AVAILABLE = "Available"
PATH_RESERVED = "Reserved"

HTTP_CREATED = 201
HTTP_NOT_FOUND = 404
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403


def repository_key(label: str) -> str:
    """Suggest the identifier of a repository from its label.

    :param label: The label, such as "Réseaux 2026".
    :return: The identifier, such as "reseaux_2026", may be empty.
    """
    # Accents removed, "é" gives "e"
    decomposed = unicodedata.normalize("NFKD", label.lower())
    ascii_label = decomposed.encode("ascii", errors="ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_label).strip("_")


class LizmapAdminApi(HttpClient):
    """Administration API of a Lizmap server.

    :param server_url: URL of Lizmap Web Client.
    :param auth_id: QGIS authentication configuration, with the Lizmap login and password.
    :param credentials: Login and password, used only when there isn't any authentication configuration.
    """

    def __init__(
        self, server_url: str, auth_id: str | None = None, credentials: tuple[str, str] | None = None
    ):
        super().__init__(auth_id, credentials)
        self.base_url = server_url.rstrip("/") + "/api.php/admin/"

    def paths(self, feedback: QgsFeedback | None = None) -> dict[str, str]:
        """List the directories in the root of the repositories.

        :param feedback: To cancel the request.
        :return: Status by directory name: "Available", or "Reserved" if already used by a repository.
        :raises BackendError: 404 if the API is not available, 401 or 403 without the rights.
        """
        response = self._send("GET", QUrl(self.base_url + "paths"), headers={"Accept": "application/json"})
        self._check(response, (200,), "Directories of the repositories")
        try:
            data = json.loads(response.body)
        except ValueError as e:
            raise BackendError(f"Directories of the repositories : {e}") from e
        if not isinstance(data, dict):
            return {}
        return {str(path).strip("/"): str(status) for path, status in data.items()}

    def create_repository(
        self, key: str, label: str, folder: str, create_directory: bool, feedback: QgsFeedback | None = None
    ):
        """Create a repository.

        :param key: Identifier of the repository, lowercase letters, digits and "_".
        :param label: Label of the repository.
        :param folder: Name of the directory, in the root of the repositories.
        :param create_directory: True to create the directory, False to use an existing one.
        :param feedback: To cancel the request.
        :raises BackendError: With the message of the server, 409 if it already exists.
        """
        body = urlencode(
            {
                "label": label,
                "path": f"{folder}/",
                "allowUserDefinedThemes": "false",
                "createDirectory": "true" if create_directory else "false",
            }
        ).encode("utf-8")

        # The form is sent like a web form
        data = QByteArray(body)
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        try:
            response = self._send(
                "POST",
                QUrl(self.base_url + "repositories/" + quote(key, safe="")),
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
                body=buffer,
                feedback=feedback,
            )
        finally:
            buffer.close()
        self._check(response, (200, HTTP_CREATED), f"Repository '{key}'")
