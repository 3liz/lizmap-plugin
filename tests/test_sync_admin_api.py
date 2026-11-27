"""Test the creation of a repository with the administration API of Lizmap Web Client.

Tests using a server are skipped unless these environment variables are set, with a Lizmap Web Client
3.10 or newer, and the WebDAV module to prepare an existing directory:

* ``LIZMAP_SYNC_SERVER_URL``: URL of Lizmap Web Client, ``http://127.0.0.1:9023/``,
* ``LIZMAP_SYNC_DAV_ROOT_URL``: URL of the root of the repositories in WebDAV, ``http://127.0.0.1:9023/dav.php/``,
* ``LIZMAP_SYNC_USER`` and ``LIZMAP_SYNC_PASSWORD``: an administrator.
"""

import os

import pytest

from qgis.core import QgsFeedback
from qgis.PyQt.QtWidgets import QDialogButtonBox, QPushButton

from lizmap.sync.backends.admin_api import PATH_AVAILABLE, PATH_RESERVED, LizmapAdminApi, repository_key
from lizmap.sync.backends.base import BackendError
from lizmap.sync.backends.webdav import WebDavBackend
from lizmap.sync.gui.new_repository_dialog import NewRepositoryDialog
from lizmap.toolbelt.strings import random_string

SERVER_URL = os.getenv("LIZMAP_SYNC_SERVER_URL", "")
DAV_ROOT_URL = os.getenv("LIZMAP_SYNC_DAV_ROOT_URL", "")
USER = os.getenv("LIZMAP_SYNC_USER", "")
PASSWORD = os.getenv("LIZMAP_SYNC_PASSWORD", "")


class FakeApi:
    """Administration API in memory."""

    def __init__(self, error: BackendError | None = None):
        """Record the created repositories.

        :param error: Error raised by the creation, if any.
        """
        self.error = error
        self.created: list[tuple[str, str, str, bool]] = []

    def create_repository(
        self, key: str, label: str, folder: str, create_directory: bool, feedback: QgsFeedback | None = None
    ):
        """Create a repository, or fail.

        :param key: Identifier.
        :param label: Label.
        :param folder: Directory.
        :param create_directory: Create the directory.
        :param feedback: Not used.
        """
        if self.error:
            raise self.error
        self.created.append((key, label, folder, create_directory))


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Urbanism", "urbanism"),
        ("Plan local d'urbanisme 2026", "plan_local_d_urbanisme_2026"),
        ("  Réseaux / eau  ", "reseaux_eau"),
        ("É", "e"),
        ("???", ""),
    ],
)
def test_repository_key(label, expected):
    """Test the identifier suggested from the label."""
    assert repository_key(label) == expected


def ok_button(dialog: NewRepositoryDialog) -> QPushButton:
    """The OK button of the dialog.

    :param dialog: The dialog.
    :return: The button.
    """
    return dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)


def test_new_repository_dialog():
    """Test the suggestions, the validation and the creation in the dialog."""
    api = FakeApi()
    paths = {"tests": PATH_RESERVED, "old_project": PATH_AVAILABLE}
    dialog = NewRepositoryDialog(None, api, paths, ["tests"])
    assert not ok_button(dialog).isEnabled()
    # Only the directories not used by a repository are proposed
    assert [dialog.folder.itemText(i) for i in range(dialog.folder.count())] == ["", "old_project"]

    # The identifier and the directory follow the label
    dialog.label.setText("Urbanism")
    dialog.label.textEdited.emit("Urbanism")
    assert dialog.key.text() == "urbanism"
    assert dialog.folder.currentText() == "urbanism"
    assert dialog.create_directory
    assert ok_button(dialog).isEnabled()
    assert "will be created" in dialog.info.text()

    # Errors
    dialog.key.setText("tests")
    dialog.key.textEdited.emit("tests")
    assert not ok_button(dialog).isEnabled()
    assert "already exists" in dialog.info.text()
    dialog.key.setText("urba")
    dialog.key.textEdited.emit("urba")
    dialog.folder.setEditText("tests")
    assert "already used" in dialog.info.text()

    # An existing directory, not created
    dialog.folder.setEditText("old_project")
    assert not dialog.create_directory
    assert "existing directory" in dialog.info.text()

    # The label doesn't change the identifier nor the directory anymore
    dialog.label.setText("Other")
    dialog.label.textEdited.emit("Other")
    assert dialog.key.text() == "urba"

    dialog.accept()
    assert api.created == [("urba", "Other", "old_project", False)]
    assert dialog.created_key == "urba"


def test_new_repository_dialog_error():
    """Test an error of the server, the dialog stays open with the message."""
    api = FakeApi(BackendError("Repository 'urba' : The repository 'urba' already exists.", 409))
    dialog = NewRepositoryDialog(None, api, {}, [])
    dialog.label.setText("Urba")
    dialog.label.textEdited.emit("Urba")
    dialog.accept()
    assert dialog.created_key is None
    assert "already exists" in dialog.info.text()


@pytest.fixture
def api() -> LizmapAdminApi:
    """The administration API of the test server.

    :return: The API.
    """
    if not SERVER_URL:
        pytest.skip("LIZMAP_SYNC_SERVER_URL is not set")
    return LizmapAdminApi(SERVER_URL, credentials=(USER, PASSWORD))


def test_admin_api(api: LizmapAdminApi):
    """Test the paths and the creation of repositories on a server."""
    paths = api.paths()
    assert paths
    assert set(paths.values()) <= {PATH_AVAILABLE, PATH_RESERVED}

    # A new directory
    key = f"sync_{random_string(8)}"
    api.create_repository(key, "Sync test", key, create_directory=True)
    assert api.paths()[key] == PATH_RESERVED

    # The same identifier again
    with pytest.raises(BackendError) as error:
        api.create_repository(key, "Sync test", f"{key}_bis", create_directory=True)
    assert error.value.http_status == 409
    assert "already exists" in str(error.value)

    # An existing directory, created with WebDAV
    folder = f"sync_{random_string(8)}"
    WebDavBackend(DAV_ROOT_URL, credentials=(USER, PASSWORD)).make_directory(folder)
    assert api.paths()[folder] == PATH_AVAILABLE
    api.create_repository(folder, "Sync existing", folder, create_directory=False)
    assert api.paths()[folder] == PATH_RESERVED

    # Without the rights
    other = LizmapAdminApi(SERVER_URL, credentials=(USER, "wrong"))
    with pytest.raises(BackendError) as error:
        other.paths()
    assert error.value.http_status == 401
