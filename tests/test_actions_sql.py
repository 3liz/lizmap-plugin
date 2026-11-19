"""Tests for the helper writing the PostgreSQL functions of the actions."""

import pytest

from qgis.core import QgsProject, QgsProviderConnectionException, QgsVectorLayer

from lizmap.actions.config import Action
from lizmap.actions.definitions import ActionGeometry, ActionScope
from lizmap.actions.sql import (
    GET_DATA_FUNCTION,
    action_branch,
    action_branches,
    databases,
    full_script,
)
from lizmap.actions.sql_dialog import ActionSqlDialog

from .compat import TestCase


def postgresql_layer(name: str, database: str = "gis", key: str = "gid") -> QgsVectorLayer:
    """Create a PostgreSQL layer, not valid because there is no database, but with the postgres provider.

    :param name: The layer and table name.
    :param database: The database name.
    :param key: The primary key.
    :return: The layer.
    """
    uri = f"dbname='{database}' host=localhost port=1 key='{key}' table=\"roads\".\"{name}\" (the_geom)"
    return QgsVectorLayer(uri, name, "postgres")


@pytest.fixture()
def project() -> QgsProject:
    """Project with two PostgreSQL layers in a database, and one in another database.

    :return: The project, cleared after the test.
    """
    project = QgsProject.instance()
    project.addMapLayer(postgresql_layer("roads"))
    project.addMapLayer(postgresql_layer("nodes"))
    project.addMapLayer(postgresql_layer("cities", database="other"))
    yield project
    project.clear()


def layer_id(project: QgsProject, name: str) -> str:
    """ID of a layer in the project.

    :param project: The project.
    :param name: The layer name.
    :return: The layer ID.
    """
    return project.mapLayersByName(name)[0].id()


class TestActionsSql(TestCase):
    """SQL code generated for the actions."""

    def test_feature_branch(self, project: QgsProject):
        """The feature query uses the primary key and the geometry column of the layer."""
        action = Action(
            name="merge",
            title="Merge l'objet à 100%",
            scope=ActionScope.Feature,
            icon="icon-star",
            layers=[layer_id(project, "roads")],
            options={"buffer_size": 100},
        )
        sql = action_branch(project, action, True)
        self.assertTrue(sql.startswith("    IF action_name = 'merge' THEN"))
        self.assertIn("-- Layers : roads", sql)
        self.assertIn("parameters->>'buffer_size'", sql)
        self.assertIn("WHERE gid::text = %1$L", sql)
        self.assertIn("the_geom AS geom", sql)
        # Quotes and percent signs are escaped for the format() string
        self.assertIn("''Merge l''''objet à 100%%'' AS message", sql)

    def test_other_scopes(self, project: QgsProject):
        """Layer and project queries, the project one using the drawn geometry if any."""
        layer = Action(
            name="hull",
            title="Hull",
            scope=ActionScope.Layer,
            icon="icon-star",
            layers=[layer_id(project, "roads")],
        )
        center = Action(name="center", title="Center", scope=ActionScope.Project, icon="icon-star")
        drawn = Action(
            name="drawn",
            title="Drawn",
            scope=ActionScope.Project,
            icon="icon-star",
            geometry=ActionGeometry.Polygon,
        )
        sql = action_branches(project, [layer, center, drawn])
        self.assertIn("    IF action_name = 'hull' THEN", sql)
        self.assertIn("ST_ConvexHull(ST_Collect(the_geom))", sql)
        self.assertIn("    ELSIF action_name = 'center' THEN", sql)
        self.assertIn("', map_center);", sql)
        self.assertIn("', wkt);", sql)

    def test_full_script(self, project: QgsProject):
        """The script creates both functions, even without action."""
        for actions in ([], [Action(name="a", title="A", scope=ActionScope.Project, icon="icon-star")]):
            sql = full_script(project, actions)
            self.assertIn("CREATE OR REPLACE FUNCTION public.query_to_geojson(datasource text)", sql)
            self.assertIn("CREATE OR REPLACE FUNCTION public.lizmap_get_data(parameters json)", sql)
            self.assertIn("RETURN NULL;", sql)

    def test_databases(self, project: QgsProject):
        """One entry per database, the one used by the actions first."""
        action = Action(
            name="a",
            title="A",
            scope=ActionScope.Feature,
            icon="icon-star",
            layers=[layer_id(project, "cities")],
        )
        result = databases(project, [action])
        self.assertListEqual(["other (localhost:1)", "gis (localhost:1)"], [d.label for d in result])


class TestActionSqlDialog(TestCase):
    """Dialog showing the SQL code, with a warning if the function already exists."""

    def test_function_missing(self, project: QgsProject):
        """Without existing function, the complete script is proposed."""
        dialog = ActionSqlDialog(None, project, [], definition_reader=lambda *_: None)
        self.assertFalse(dialog.function_exists)
        self.assertEqual(dialog.full_script, dialog.tabs.currentWidget())
        self.assertFalse(dialog.tabs.isTabEnabled(dialog.tabs.indexOf(dialog.existing)))

    def test_function_exists(self, project: QgsProject):
        """With an existing function, the user is warned and the existing code is displayed."""
        existing = "CREATE OR REPLACE FUNCTION public.lizmap_get_data(parameters json) ..."

        def reader(_layer: QgsVectorLayer, signature: str) -> str | None:
            """Only lizmap_get_data exists.

            :param _layer: The layer, not used.
            :param signature: The function signature.
            :return: The definition, or None.
            """
            return existing if signature == GET_DATA_FUNCTION else None

        dialog = ActionSqlDialog(None, project, [], definition_reader=reader)
        self.assertTrue(dialog.function_exists)
        self.assertEqual(existing, dialog.existing.text())
        self.assertEqual(dialog.branches, dialog.tabs.currentWidget())
        self.assertIn("already exists", dialog.status.text())
        self.assertIn("query_to_geojson", dialog.status.text())

    def test_connection_error(self, project: QgsProject):
        """A connection error is displayed."""

        def reader(*_) -> None:
            """Raise a connection error.

            :raises QgsProviderConnectionException: Always.
            """
            raise QgsProviderConnectionException("connection refused")

        dialog = ActionSqlDialog(None, project, [], definition_reader=reader)
        self.assertFalse(dialog.function_exists)
        self.assertIn("connection refused", dialog.status.text())
