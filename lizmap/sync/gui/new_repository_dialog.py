"""Creation of a Lizmap repository, with the administration API of Lizmap Web Client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.PyQt.QtCore import QRegularExpression, Qt
from qgis.PyQt.QtGui import QRegularExpressionValidator
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)
from qgis.utils import OverrideCursor

from lizmap.sync.backends.admin_api import (
    PATH_AVAILABLE,
    REPOSITORY_FOLDER,
    REPOSITORY_KEY,
    repository_key,
)
from lizmap.sync.backends.base import BackendError
from lizmap.toolbelt.i18n import tr

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from lizmap.sync.backends.admin_api import LizmapAdminApi

RED = "#c62828"


class NewRepositoryDialog(QDialog):
    """Create a repository, in a new directory or in an existing one not used yet.

    :param parent: Parent widget.
    :param api: The administration API of the server.
    :param paths: Directories in the root of the repositories, with their status.
    :param existing_keys: Identifiers of the existing repositories.
    """

    def __init__(
        self,
        parent: QWidget | None,
        api: LizmapAdminApi,
        paths: Mapping[str, str],
        existing_keys: Collection[str],
    ):
        super().__init__(parent)
        self.api = api
        self.paths = dict(paths)
        self.existing_keys = set(existing_keys)
        self.created_key: str | None = None
        # The identifier and the directory follow the label until the user edits them
        self._key_edited = False
        self._folder_edited = False

        self.setWindowTitle(tr("New Lizmap repository"))
        self.setMinimumWidth(450)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.label = QLineEdit()
        self.label.setPlaceholderText(tr("Urbanism"))
        form.addRow(tr("Label"), self.label)

        self.key = QLineEdit()
        self.key.setValidator(QRegularExpressionValidator(QRegularExpression(REPOSITORY_KEY.pattern)))
        self.key.setToolTip(tr('Identifier of the repository: lowercase letters, digits and "_"'))
        form.addRow(tr("Identifier"), self.key)

        # Existing directories not used yet, or a new name
        self.folder = QComboBox()
        self.folder.setEditable(True)
        self.folder.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.folder.addItem("")
        for name, status in sorted(self.paths.items()):
            if status == PATH_AVAILABLE:
                self.folder.addItem(name)
        self.folder.lineEdit().setValidator(
            QRegularExpressionValidator(QRegularExpression(REPOSITORY_FOLDER.pattern))
        )
        self.folder.setToolTip(tr('Directory on the server: letters, digits and "_"'))
        form.addRow(tr("Directory"), self.folder)
        layout.addLayout(form)

        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.label.textEdited.connect(self._label_edited)
        self.key.textEdited.connect(self._key_changed)
        self.folder.editTextChanged.connect(self._folder_changed)
        self._validate()

    def _label_edited(self, label: str):
        """Suggest the identifier and the directory from the label.

        :param label: The new label.
        """
        suggestion = repository_key(label)
        if not self._key_edited:
            self.key.setText(suggestion)
        if not self._folder_edited:
            self.folder.blockSignals(True)
            self.folder.setEditText(suggestion)
            self.folder.blockSignals(False)
        self._validate()

    def _key_changed(self, _text: str):
        """The user edited the identifier, it doesn't follow the label anymore.

        :param _text: The new identifier.
        """
        self._key_edited = True
        self._validate()

    def _folder_changed(self, _text: str):
        """The user edited the directory, it doesn't follow the label anymore.

        :param _text: The new directory.
        """
        self._folder_edited = True
        self._validate()

    @property
    def create_directory(self) -> bool:
        """Tell if the directory must be created.

        :return: False if the directory exists on the server, not used by a repository.
        """
        return self.folder.currentText() not in self.paths

    def _validate(self) -> bool:
        """Check the values, display why they are not valid and enable the OK button.

        :return: True if the values are valid.
        """
        key = self.key.text()
        folder = self.folder.currentText()
        error = None
        if not self.label.text().strip():
            error = tr("Write the label of the repository.")
        elif not REPOSITORY_KEY.match(key):
            error = tr('The identifier must contain only lowercase letters, digits and "_".')
        elif key in self.existing_keys:
            error = tr("A repository with this identifier already exists.")
        elif not REPOSITORY_FOLDER.match(folder):
            error = tr('The directory must contain only letters, digits and "_".')
        elif folder in self.paths and self.paths[folder] != PATH_AVAILABLE:
            error = tr("This directory is already used by another repository.")

        if error:
            self.info.setText(f"<span style='color:{RED}'>{error}</span>")
        elif self.create_directory:
            self.info.setText(tr("The directory <b>{}</b> will be created on the server.").format(folder))
        else:
            self.info.setText(tr("The existing directory <b>{}</b> will be used.").format(folder))

        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(error is None)
        return error is None

    def accept(self):
        """Create the repository, the dialog stays open with the error if it fails."""
        if not self._validate():
            return

        key = self.key.text()
        try:
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                self.api.create_repository(
                    key, self.label.text().strip(), self.folder.currentText(), self.create_directory
                )
        except BackendError as e:
            self.info.setText(f"<span style='color:{RED}'>{e}</span>")
            return

        self.created_key = key
        super().accept()
