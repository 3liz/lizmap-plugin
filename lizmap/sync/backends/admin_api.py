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

# Right to view a repository, given to the groups chosen when it's created
RIGHT_VIEW = "lizmap.repositories.view"
# Group of the administrators, allowed by default to view a new repository
ADMINS_GROUP = "admins"
# Type of the private group of each user, not proposed
PRIVATE_GROUP_TYPE = 2

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

    def repository_keys(self, feedback: QgsFeedback | None = None) -> list[str]:
        """List the identifiers of all repositories, even those the user can't view.

        :param feedback: To cancel the request.
        :return: The identifiers.
        :raises BackendError: If the request failed.
        """
        response = self._send(
            "GET", QUrl(self.base_url + "repositories"), headers={"Accept": "application/json"}
        )
        self._check(response, (200,), "Repositories")
        try:
            data = json.loads(response.body)
        except ValueError as e:
            raise BackendError(f"Repositories : {e}") from e
        return [str(item["key"]) for item in data if isinstance(item, dict) and "key" in item]

    def groups(self, feedback: QgsFeedback | None = None) -> dict[str, str]:
        """List the groups of users, without the private group of each user.

        :param feedback: To cancel the request.
        :return: Name by identifier of the group.
        :raises BackendError: If the request failed.
        """
        response = self._send("GET", QUrl(self.base_url + "groups"), headers={"Accept": "application/json"})
        self._check(response, (200,), "Groups")
        try:
            data = json.loads(response.body)
        except ValueError as e:
            raise BackendError(f"Groups : {e}") from e
        return {
            str(group["id_aclgrp"]): str(group.get("name") or group["id_aclgrp"])
            for group in data
            if isinstance(group, dict)
            and "id_aclgrp" in group
            and group.get("grouptype") != PRIVATE_GROUP_TYPE
        }

    def _post_form(self, url: str, fields: dict[str, str], action: str, feedback: QgsFeedback | None = None):
        """Send a form, like a web form.

        :param url: The URL.
        :param fields: The fields of the form.
        :param action: Description of the request, for the error message.
        :param feedback: To cancel the request.
        :raises BackendError: With the message of the server if the request failed.
        """
        data = QByteArray(urlencode(fields).encode("utf-8"))
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        try:
            response = self._send(
                "POST",
                QUrl(url),
                headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
                body=buffer,
                feedback=feedback,
            )
        finally:
            buffer.close()
        self._check(response, (200, HTTP_CREATED), action)

    def create_repository(
        self, key: str, label: str, folder: str, create_directory: bool, feedback: QgsFeedback | None = None
    ):
        """Create a repository.

        Nobody can see it until a group gets the right to view it, see ``add_right``.

        :param key: Identifier of the repository, lowercase letters, digits and "_".
        :param label: Label of the repository.
        :param folder: Name of the directory, in the root of the repositories.
        :param create_directory: True to create the directory, False to use an existing one.
        :param feedback: To cancel the request.
        :raises BackendError: With the message of the server, 409 if it already exists.
        """
        fields = {
            "label": label,
            "path": f"{folder}/",
            "allowUserDefinedThemes": "false",
            "createDirectory": "true" if create_directory else "false",
        }
        url = self.base_url + "repositories/" + quote(key, safe="")
        self._post_form(url, fields, f"Repository '{key}'", feedback)

    def add_right(self, key: str, group: str, right: str = RIGHT_VIEW, feedback: QgsFeedback | None = None):
        """Give a right on a repository to a group.

        :param key: Identifier of the repository.
        :param group: Identifier of the group.
        :param right: The right, the right to view the repository by default.
        :param feedback: To cancel the request.
        :raises BackendError: With the message of the server, 403 without the right to update repositories.
        """
        url = self.base_url + "repositories/" + quote(key, safe="") + "/rights"
        self._post_form(url, {"group": group, "right": right}, f"Right '{right}' for '{group}'", feedback)
