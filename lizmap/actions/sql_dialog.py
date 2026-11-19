"""Dialog helping to write the PostgreSQL functions used by the Lizmap actions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.core import QgsProject, QgsProviderConnectionException
from qgis.gui import QgsCodeEditorSQL
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QGuiApplication
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qgis.utils import OverrideCursor

from lizmap.actions.definitions import ActionScope
from lizmap.actions.sql import (
    GET_DATA_FUNCTION,
    QUERY_TO_GEOJSON_FUNCTION,
    action_branches,
    databases,
    full_script,
    function_definition,
)
from lizmap.toolbelt.i18n import tr

if TYPE_CHECKING:
    from collections.abc import Callable

    from qgis.core import QgsVectorLayer

    from lizmap.actions.config import Action

__copyright__ = "Copyright 2026, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"


class ActionSqlDialog(QDialog):
    """Show the SQL code of the functions used by the actions, to copy it.

    The plugin does not run the SQL code. It only checks if the function lizmap_get_data already exists,
    because it can be used by other projects in the same database and must not be replaced.
    """

    def __init__(
        self,
        parent: QWidget | None,
        project: QgsProject,
        actions: list[Action],
        definition_reader: Callable[[QgsVectorLayer, str], str | None] = function_definition,
    ):
        """Constructor.

        :param parent: The parent widget.
        :param project: The QGIS project, to list the databases.
        :param actions: The actions, one branch is written for each action.
        :param definition_reader: Function reading a function definition in the database of a layer.
        """
        super().__init__(parent)
        self.project = project
        self.actions = actions
        self.definition_reader = definition_reader
        # True if the function lizmap_get_data exists in the selected database
        self.function_exists = False

        self.setWindowTitle(tr("PostgreSQL functions for the actions"))
        self.setMinimumSize(800, 600)
        layout = QVBoxLayout(self)

        help_label = QLabel(
            tr(
                "Each action runs the PostgreSQL function 'lizmap_get_data', which uses the function "
                "'query_to_geojson'. The SQL code below is an example, with one query per action : it must be "
                "adapted, then run in the database by yourself. The plugin does not modify the database."
            ),
            self,
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        # Database to check
        form = QFormLayout()
        self.database = QComboBox(self)
        for database in databases(project, actions):
            self.database.addItem(database.label, database.layer)
        self.database.currentIndexChanged.connect(self.check_database)
        form.addRow(tr("Database"), self.database)
        layout.addLayout(form)

        # The project scope does not use the database of a layer
        if any(action.scope == ActionScope.Project for action in actions):
            project_label = QLabel(
                tr(
                    "Actions in the 'project' scope use the default database of Lizmap Web Client, set in the "
                    "file 'profiles.ini.php' on the server : the functions must exist in this database too."
                ),
                self,
            )
            project_label.setWordWrap(True)
            layout.addWidget(project_label)

        self.status = QLabel(self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        # SQL code
        self.tabs = QTabWidget(self)
        self.full_script = self._editor(full_script(project, actions))
        self.branches = self._editor(action_branches(project, actions))
        self.existing = self._editor("")
        self.tabs.addTab(self.full_script, tr("Complete script"))
        self.tabs.addTab(self.branches, tr("Queries of the actions"))
        self.tabs.addTab(self.existing, tr("Existing function"))
        layout.addWidget(self.tabs)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        copy_button = QPushButton(tr("Copy the current tab"), self)
        copy_button.clicked.connect(self.copy)
        button_box.addButton(copy_button, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.check_database()

    def _editor(self, text: str) -> QgsCodeEditorSQL:
        """Build a read-only SQL editor.

        :param text: The SQL code.
        :return: The editor.
        """
        editor = QgsCodeEditorSQL(self)
        editor.setText(text)
        editor.setReadOnly(True)
        return editor

    def check_database(self):
        """Check if the functions already exist in the selected database, and warn the user."""
        self.function_exists = False
        self.existing.setText("")
        self.tabs.setTabEnabled(self.tabs.indexOf(self.existing), False)

        layer = self.database.currentData()
        if not layer:
            self._set_status(
                tr("There is no PostgreSQL layer in the project, the database cannot be checked."), ""
            )
            return

        # Read the existing functions
        try:
            with OverrideCursor(Qt.CursorShape.WaitCursor):
                get_data = self.definition_reader(layer, GET_DATA_FUNCTION)
                query_to_geojson = self.definition_reader(layer, QUERY_TO_GEOJSON_FUNCTION)
        except QgsProviderConnectionException as e:
            self._set_status(tr("The database cannot be checked : {}").format(e), "orange")
            return

        if not get_data:
            self._set_status(
                tr(
                    "The function 'lizmap_get_data' does not exist in this database, "
                    "the complete script can be used."
                ),
                "green",
            )
            self.tabs.setCurrentWidget(self.full_script)
            return

        # The function exists, it must not be replaced
        self.function_exists = True
        self.existing.setText(get_data)
        self.tabs.setTabEnabled(self.tabs.indexOf(self.existing), True)
        self.tabs.setCurrentWidget(self.branches)
        message = tr(
            "The function 'lizmap_get_data' already exists in this database. It may be used by other projects : "
            "do not run the complete script, it would replace the existing function. Add the queries of the "
            "actions in the existing function instead, with new names if they are already used."
        )
        if not query_to_geojson:
            message += " " + tr(
                "The function 'query_to_geojson' does not exist, it is in the complete script."
            )
        self._set_status(message, "red")

    def _set_status(self, message: str, color: str):
        """Display the result of the database check.

        :param message: The message.
        :param color: The CSS color of the message, empty for the default color.
        """
        self.status.setText(message)
        self.status.setStyleSheet(f"QLabel {{ color : {color}; }}" if color else "")

    def copy(self):
        """Copy the SQL code of the current tab in the clipboard."""
        QGuiApplication.clipboard().setText(self.tabs.currentWidget().text())
