"""Tests for the Lizmap actions configuration."""

import json

from pathlib import Path

import pytest

from qgis.core import QgsProject, QgsVectorLayer

from lizmap.actions.config import (
    Action,
    ActionCallback,
    ActionFormatError,
    LegacyActionFormatError,
    action_file_path,
    actions_from_json,
    actions_to_json,
    read_actions,
    validate_actions,
    write_actions,
)
from lizmap.actions.definitions import ActionGeometry, ActionScope, CallbackMethod, StyleKey

from .compat import TestCase

# Layer IDs used in the action file from Lizmap Web Client tests
PARENT_LAYER_ID = "parent_layer_d3dc849b_9622_4ad0_8401_ef7d75950111"
TRAMWAY_LAYER_ID = "tramway_lines_4215fd0b_5136_4c19_b3ee_d1617f8df8ea"


def postgresql_layer(name: str) -> QgsVectorLayer:
    """Create a PostgreSQL layer, not valid because there is no database, but with the postgres provider.

    :param name: The layer name.
    :return: The layer.
    """
    uri = f'dbname=\'lizmap\' host=localhost port=1 table="public"."{name}" (geom)'
    return QgsVectorLayer(uri, name, "postgres")


@pytest.fixture()
def project(data: Path) -> QgsProject:
    """Project with two PostgreSQL layers and one GeoJSON layer.

    :param data: Path of the test data folder.
    :return: The project, cleared after the test.
    """
    project = QgsProject.instance()
    pg_layer = postgresql_layer("parent_layer")
    other_pg_layer = postgresql_layer("tramway_lines")
    file_layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
    for layer in (pg_layer, other_pg_layer, file_layer):
        project.addMapLayer(layer)
    yield project
    project.clear()


def feature_action(layer_id: str) -> Action:
    """Valid action in the feature scope.

    :param layer_id: The layer ID.
    :return: The action.
    """
    return Action(
        name="buffer",
        title="Buffer",
        scope=ActionScope.Feature,
        icon="icon-leaf",
        layers=[layer_id],
    )


class TestActionsFile(TestCase):
    """Read and write the action configuration file."""

    def test_action_file_path(self):
        """The action file is next to the QGS file."""
        self.assertEqual(Path("/data/project.qgs.action"), action_file_path("/data/project.qgs"))

    def test_read_lwc_file(self, data: Path):
        """Read the action file used by Lizmap Web Client tests."""
        actions = read_actions(data.joinpath("actions.qgs.action"))
        self.assertEqual(4, len(actions))

        # Feature scope, with all properties
        action = actions[0]
        self.assertEqual("buffer_500", action.name)
        self.assertEqual(ActionScope.Feature, action.scope)
        self.assertListEqual([PARENT_LAYER_ID, TRAMWAY_LAYER_ID], action.layers)
        self.assertEqual("Do you really want to show the buffer ?", action.confirm)
        self.assertDictEqual({"buffer_size": 500, "other_param": "yes"}, action.options)
        self.assertEqual("blue", action.style[StyleKey.StrokeColor])
        self.assertEqual(6, action.style[StyleKey.CircleRadius])
        self.assertListEqual(
            [
                ActionCallback(CallbackMethod.Zoom),
                ActionCallback(CallbackMethod.Select, PARENT_LAYER_ID),
                ActionCallback(CallbackMethod.Redraw, PARENT_LAYER_ID),
            ],
            action.callbacks,
        )

        # Project scope with a geometry to draw
        self.assertEqual(ActionScope.Project, actions[2].scope)
        self.assertEqual(ActionGeometry.Point, actions[2].geometry)

    def test_round_trip(self, data: Path):
        """The content is the same after reading and writing the Lizmap Web Client file."""
        content = data.joinpath("actions.qgs.action").read_text(encoding="utf8")
        exported = actions_to_json(actions_from_json(content))
        self.assertListEqual(json.loads(content), json.loads(exported))

    def test_missing_file(self, tmp_path: Path):
        """No action if the file does not exist."""
        self.assertListEqual([], read_actions(tmp_path.joinpath("missing.qgs.action")))

    def test_legacy_format(self):
        """The format for LWC < 3.7, an object with layer IDs as keys, is not supported."""
        content = json.dumps({PARENT_LAYER_ID: [{"name": "buffer", "title": "Buffer"}]})
        with self.assertRaises(LegacyActionFormatError):
            actions_from_json(content)

    def test_invalid_content(self):
        """Invalid JSON or invalid actions raise an error."""
        invalid = (
            "[",
            '"text"',
            '["text"]',
            '[{"title": "No name", "scope": "project"}]',
            '[{"name": "a", "scope": "map"}]',
            '[{"name": "a", "scope": "project", "geometry": "hexagon"}]',
            '[{"name": "a", "scope": "project", "options": []}]',
            '[{"name": "a", "scope": "project", "callbacks": ["zoom"]}]',
        )
        for content in invalid:
            with self.assertRaises(ActionFormatError, msg=content):
                actions_from_json(content)

    def test_unknown_callback(self, project: QgsProject):
        """A callback unknown by Lizmap Web Client does not prevent reading the file, but it is removed."""
        content = json.dumps(
            [
                {
                    "name": "a",
                    "title": "A",
                    "scope": "project",
                    "icon": "icon-star",
                    "callbacks": [{"method": "center"}, {"method": "zoom"}],
                }
            ]
        )
        actions = actions_from_json(content)
        self.assertListEqual([ActionCallback(CallbackMethod.Zoom)], actions[0].callbacks)
        self.assertListEqual(["center"], actions[0].ignored_callbacks)

        # Only a warning, the action still works in Lizmap Web Client
        issues = validate_actions(actions, project)
        self.assertEqual(1, len(issues))
        self.assertTrue(issues[0].warning)

        exported = json.loads(actions_to_json(actions))[0]
        self.assertListEqual([{"method": "zoom"}], exported["callbacks"])

    def test_unknown_keys_dropped(self):
        """Keys unknown by the plugin are not written back."""
        content = json.dumps(
            [
                {
                    "name": "a",
                    "title": "A",
                    "scope": "project",
                    "icon": "icon-star",
                    "custom": "value",
                    "style": {"fill-color": "red", "text-font": "Arial"},
                }
            ]
        )
        exported = json.loads(actions_to_json(actions_from_json(content)))[0]
        assert "custom" not in exported
        self.assertDictEqual({"fill-color": "red"}, exported["style"])

    def test_export_by_scope(self):
        """Layers and geometry are only written for the scopes using them."""
        action = Action(
            name="a",
            title="A",
            scope=ActionScope.Project,
            icon="icon-star",
            layers=[PARENT_LAYER_ID],
            geometry=ActionGeometry.Polygon,
            callbacks=[ActionCallback(CallbackMethod.Zoom, PARENT_LAYER_ID)],
        )
        exported = action.to_json()
        assert "layers" not in exported
        self.assertEqual("polygon", exported["geometry"])
        self.assertDictEqual({}, exported["options"])
        self.assertListEqual([{"method": "zoom"}], exported["callbacks"])

        action.scope = ActionScope.Feature
        exported = action.to_json()
        self.assertListEqual([PARENT_LAYER_ID], exported["layers"])
        assert "geometry" not in exported

    def test_write_and_delete(self, tmp_path: Path):
        """The file is written with some actions, and removed without any action."""
        path = tmp_path.joinpath("project.qgs.action")
        action = Action(name="a", title="Ünïcode", scope=ActionScope.Project, icon="icon-star")

        self.assertTrue(write_actions(path, [action]))
        self.assertIn("Ünïcode", path.read_text(encoding="utf8"))
        self.assertListEqual([action], read_actions(path))

        self.assertFalse(write_actions(path, []))
        self.assertFalse(path.exists())

        # No error if there is no file to remove
        self.assertFalse(write_actions(path, []))


class TestActionsValidation(TestCase):
    """Validate the actions against Lizmap Web Client rules and the project."""

    def test_valid(self, project: QgsProject):
        """A complete action is valid."""
        layer_id = project.mapLayersByName("parent_layer")[0].id()
        action = feature_action(layer_id)
        action.icon = "media/icons/buffer.svg"
        action.options = {"buffer_size": 500, "unit": "m"}
        action.style = {StyleKey.FillColor: "rgba(173,216,230,0.8)", StyleKey.StrokeWidth: 2.5}
        action.callbacks = [
            ActionCallback(CallbackMethod.Zoom),
            ActionCallback(CallbackMethod.Redraw, layer_id),
        ]
        self.assertListEqual([], validate_actions([action], project))

    def test_name_title_icon(self, project: QgsProject):
        """Name, title and icon are checked."""
        action = Action(name="my.action", title=" ", scope=ActionScope.Project, icon="star")
        issues = validate_actions([action], project)
        self.assertEqual(3, len(issues))
        self.assertTrue(all(issue.action == "my.action" for issue in issues))

    def test_unique_name(self, project: QgsProject):
        """The name must be unique in the file, even with different scopes."""
        layer_id = project.mapLayersByName("parent_layer")[0].id()
        project_action = Action(name="buffer", title="Buffer", scope=ActionScope.Project, icon="icon-star")
        issues = validate_actions([feature_action(layer_id), project_action], project)
        self.assertEqual(1, len(issues))

    def test_layers(self, project: QgsProject):
        """Layers are mandatory and must be PostgreSQL layers in the project."""
        file_layer_id = project.mapLayersByName("lines")[0].id()
        self.assertEqual(1, len(validate_actions([feature_action(file_layer_id)], project)))
        self.assertEqual(1, len(validate_actions([feature_action("unknown_layer_id")], project)))

        action = feature_action(file_layer_id)
        action.layers = []
        self.assertEqual(1, len(validate_actions([action], project)))

    def test_geometry(self, project: QgsProject):
        """A geometry to draw is not possible in the feature scope."""
        layer_id = project.mapLayersByName("parent_layer")[0].id()
        action = feature_action(layer_id)
        action.geometry = ActionGeometry.Point
        self.assertEqual(1, len(validate_actions([action], project)))

        action.scope = ActionScope.Layer
        self.assertListEqual([], validate_actions([action], project))

    def test_options(self, project: QgsProject):
        """Option keys must be valid SQL identifiers with scalar values."""
        action = Action(name="a", title="A", scope=ActionScope.Project, icon="icon-star")
        action.options = {
            "buffer size": 1,
            "valid": True,
            "list": [1],
        }
        issues = validate_actions([action], project)
        self.assertEqual(3, len(issues))
        self.assertFalse(any(issue.warning for issue in issues))

    def test_reserved_option(self, project: QgsProject):
        """An option cannot use the name of a parameter sent by Lizmap Web Client."""
        action = Action(name="a", title="A", scope=ActionScope.Project, icon="icon-star")
        action.options = {"feature_id": -1, "line_order": 0}
        issues = validate_actions([action], project)
        self.assertEqual(1, len(issues))
        self.assertFalse(issues[0].warning)

    def test_style(self, project: QgsProject):
        """Colors must be texts and widths positive numbers."""
        action = Action(name="a", title="A", scope=ActionScope.Project, icon="icon-star")
        action.style = {
            StyleKey.FillColor: 12,
            StyleKey.StrokeColor: "",
            StyleKey.StrokeWidth: -1,
            StyleKey.CircleRadius: "6",
        }
        self.assertEqual(4, len(validate_actions([action], project)))

    def test_callbacks(self, project: QgsProject):
        """Select and redraw callbacks need a layer in the project."""
        action = Action(name="a", title="A", scope=ActionScope.Project, icon="icon-star")
        action.callbacks = [
            ActionCallback(CallbackMethod.Select),
            ActionCallback(CallbackMethod.Redraw, "unknown_layer_id"),
            ActionCallback(CallbackMethod.Zoom),
        ]
        self.assertEqual(2, len(validate_actions([action], project)))
