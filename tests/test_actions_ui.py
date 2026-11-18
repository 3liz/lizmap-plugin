"""Tests for the actions panel and the action edition dialog."""

import json

from pathlib import Path

import pytest

from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QLabel, QMessageBox, QPushButton, QTableWidget, QWidget

from lizmap.actions.config import Action, ActionCallback, read_actions
from lizmap.actions.definitions import ActionGeometry, ActionScope, CallbackMethod, StyleKey
from lizmap.actions.edition_dialog import ActionEditionDialog, color_to_text, option_value_from_text
from lizmap.actions.panel import ActionsPanel

from .compat import TestCase


def postgresql_layer(name: str) -> QgsVectorLayer:
    """Create a PostgreSQL layer, not valid because there is no database, but with the postgres provider.

    :param name: The layer name.
    :return: The layer.
    """
    uri = f'dbname=\'lizmap\' host=localhost port=1 table="public"."{name}" (geom)'
    return QgsVectorLayer(uri, name, "postgres")


@pytest.fixture()
def project() -> QgsProject:
    """Project with two PostgreSQL layers.

    :return: The project, cleared after the test.
    """
    project = QgsProject.instance()
    project.addMapLayer(postgresql_layer("roads"))
    project.addMapLayer(postgresql_layer("nodes"))
    yield project
    project.clear()


def layer_id(project: QgsProject, name: str) -> str:
    """ID of a layer in the project.

    :param project: The project.
    :param name: The layer name.
    :return: The layer ID.
    """
    return project.mapLayersByName(name)[0].id()


def complete_action(project: QgsProject) -> Action:
    """Action in the layer scope, using all the properties.

    :param project: The project.
    :return: The action.
    """
    roads = layer_id(project, "roads")
    return Action(
        name="merge",
        title="Merge the roads",
        scope=ActionScope.Layer,
        icon="icon-road",
        description="Merge two roads",
        confirm="Are you sure ?",
        layers=[roads],
        geometry=ActionGeometry.Line,
        options={"road_a": -1, "road_list": "-1,-2", "ratio": 0.5},
        style={
            StyleKey.FillColor: "rgba(255,0,0,0.4)",
            StyleKey.StrokeColor: "blue",
            StyleKey.StrokeWidth: 4,
        },
        callbacks=[ActionCallback(CallbackMethod.Zoom), ActionCallback(CallbackMethod.Redraw, roads)],
    )


def panel(project: QgsProject) -> ActionsPanel:
    """Actions panel with its own widgets.

    :param project: The project.
    :return: The panel.
    """
    parent = QWidget()
    widgets = [QPushButton(parent) for _ in range(6)]
    actions_panel = ActionsPanel(parent, QTableWidget(parent), *widgets, QLabel(parent), project)
    # Keep a reference to the parent widget
    actions_panel.parent_for_tests = parent
    return actions_panel


class TestEditionHelpers(TestCase):
    """Conversion of the values typed in the dialog."""

    def test_option_value(self):
        """Numbers are converted, other texts are kept."""
        self.assertEqual(-1, option_value_from_text("-1"))
        self.assertEqual(0.5, option_value_from_text("0.5"))
        self.assertEqual("007", option_value_from_text("007"))
        self.assertEqual("-1,-2", option_value_from_text("-1,-2"))
        self.assertEqual("", option_value_from_text(""))

    def test_color(self):
        """Colors are written as rgb or rgba."""
        self.assertEqual("rgb(255,0,0)", color_to_text(QColor(255, 0, 0)))
        self.assertEqual("rgba(255,0,0,0.4)", color_to_text(QColor(255, 0, 0, 102)))


class TestActionEditionDialog(TestCase):
    """Dialog to create or edit an action."""

    def test_round_trip(self, project: QgsProject):
        """An action loaded in the dialog is the same when read back."""
        action = complete_action(project)
        dialog = ActionEditionDialog(None, project, action)
        self.assertEqual(action, dialog.action())
        self.assertListEqual([], dialog.validation_errors())

    def test_changed_style(self, project: QgsProject):
        """A changed color is written as rgba, a value not set is removed."""
        action = complete_action(project)
        dialog = ActionEditionDialog(None, project, action)
        dialog.style_widgets[StyleKey.StrokeColor].setColor(QColor(0, 0, 255, 128))
        dialog.style_widgets[StyleKey.FillColor].setToNull()
        dialog.style_widgets[StyleKey.CircleRadius].setValue(6)
        self.assertDictEqual(
            {StyleKey.StrokeColor: "rgba(0,0,255,0.5)", StyleKey.StrokeWidth: 4, StyleKey.CircleRadius: 6},
            dialog.current_style(),
        )

    def test_scope(self, project: QgsProject):
        """Layers and geometry are only kept for the scopes using them."""
        action = complete_action(project)
        dialog = ActionEditionDialog(None, project, action)

        dialog.scope.setCurrentIndex(dialog.scope.findData(ActionScope.Feature))
        self.assertIsNone(dialog.action().geometry)
        self.assertFalse(dialog.geometry.isEnabled())

        dialog.scope.setCurrentIndex(dialog.scope.findData(ActionScope.Project))
        self.assertListEqual([], dialog.action().layers)
        self.assertFalse(dialog.layers.isEnabled())

    def test_errors(self, project: QgsProject):
        """The dialog is not accepted if the action has errors, warnings are not blocking."""
        dialog = ActionEditionDialog(None, project, None, other_names=["merge"])
        dialog.name.setText("merge")
        dialog.scope.setCurrentIndex(dialog.scope.findData(ActionScope.Feature))
        dialog.accept()

        # Name already used, no title, no layer
        self.assertEqual(3, len(dialog.validation_errors()))
        self.assertTrue(dialog.error.isVisibleTo(dialog))
        self.assertNotEqual(ActionEditionDialog.DialogCode.Accepted, dialog.result())

    def test_new_action(self, project: QgsProject):
        """A new action is built from the form."""
        dialog = ActionEditionDialog(None, project)
        dialog.name.setText("center_buffer")
        dialog.title.setText("Buffer")
        dialog.add_option("buffer_size", "")
        dialog.options.item(0, 1).setText("500")
        dialog.add_callback()

        action = dialog.action()
        self.assertEqual(ActionScope.Project, action.scope)
        self.assertEqual("icon-star", action.icon)
        self.assertDictEqual({"buffer_size": 500}, action.options)
        self.assertListEqual([ActionCallback(CallbackMethod.Zoom)], action.callbacks)
        self.assertListEqual([], dialog.validation_errors())


class TestActionsPanel(TestCase):
    """Panel listing the actions in the main dialog."""

    def test_load_and_save(self, project: QgsProject, tmp_path: Path):
        """The file is only written if the actions have been changed, and removed without action."""
        path = tmp_path.joinpath("project.qgs.action")
        path.write_text(json.dumps([complete_action(project).to_json()]), encoding="utf8")
        content = path.read_text(encoding="utf8")

        actions_panel = panel(project)
        actions_panel.load(path)
        self.assertEqual(1, actions_panel.table.rowCount())
        self.assertEqual("roads", actions_panel.table.item(0, 3).text())
        self.assertFalse(actions_panel.has_errors())

        # No change, the file is not written
        self.assertFalse(actions_panel.save())
        self.assertEqual(content, path.read_text(encoding="utf8"))

        # Duplicate, then move up the copy
        actions_panel.table.selectRow(0)
        actions_panel.duplicate_action()
        actions_panel.move_up()
        self.assertListEqual(["merge_copy", "merge"], [a.name for a in actions_panel.actions])
        self.assertTrue(actions_panel.save())
        self.assertListEqual(["merge_copy", "merge"], [a.name for a in read_actions(path)])

        # Remove all actions, the file is removed
        actions_panel.remove_action()
        actions_panel.remove_action()
        self.assertListEqual([], actions_panel.actions)
        self.assertTrue(actions_panel.save())
        self.assertFalse(path.exists())

    def test_add_and_edit(self, project: QgsProject, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Actions returned by the dialog are added or replaced."""
        actions_panel = panel(project)
        actions_panel.load(tmp_path.joinpath("project.qgs.action"))

        action = complete_action(project)
        monkeypatch.setattr(actions_panel, "_open_dialog", lambda *_: action)
        actions_panel.add_action()
        self.assertListEqual([action], actions_panel.actions)

        edited = complete_action(project)
        edited.title = "New title"
        monkeypatch.setattr(actions_panel, "_open_dialog", lambda *_: edited)
        actions_panel.edit_action()
        self.assertEqual("New title", actions_panel.actions[0].title)
        self.assertTrue(actions_panel.dirty)

    def test_errors(self, project: QgsProject, tmp_path: Path):
        """Errors are displayed and reported, for instance a layer removed from the project."""
        path = tmp_path.joinpath("project.qgs.action")
        action = complete_action(project)
        action.layers = ["removed_layer_id"]
        path.write_text(json.dumps([action.to_json()]), encoding="utf8")

        actions_panel = panel(project)
        actions_panel.load(path)
        self.assertTrue(actions_panel.has_errors())
        self.assertIn("removed_layer_id", actions_panel.issues_label.text())

    def test_unreadable_file(self, project: QgsProject, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """A legacy file is only replaced after a confirmation."""
        path = tmp_path.joinpath("project.qgs.action")
        path.write_text(json.dumps({"layer_id": []}), encoding="utf8")

        actions_panel = panel(project)
        actions_panel.load(path)
        assert actions_panel.read_error is not None
        self.assertListEqual([], actions_panel.actions)

        # The user refuses to replace the file
        action = complete_action(project)
        monkeypatch.setattr(actions_panel, "_open_dialog", lambda *_: action)
        monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.No)
        actions_panel.add_action()
        self.assertListEqual([], actions_panel.actions)
        self.assertFalse(actions_panel.save())

        # The user accepts
        monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
        actions_panel.add_action()
        self.assertTrue(actions_panel.save())
        self.assertListEqual([action], read_actions(path))

    def test_project_not_saved(self, project: QgsProject):
        """No action can be added if the project is not saved."""
        actions_panel = panel(project)
        actions_panel.load(None)
        self.assertFalse(actions_panel.table.isEnabled())
        actions_panel.add_action()
        self.assertListEqual([], actions_panel.actions)
