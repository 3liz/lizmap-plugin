"""Helper to write the PostgreSQL functions used by the Lizmap actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qgis.core import (
    QgsDataSourceUri,
    QgsProject,
    QgsProviderRegistry,
    QgsVectorLayer,
)

from lizmap.actions.definitions import RESERVED_OPTION_KEYS, ActionScope

if TYPE_CHECKING:
    from lizmap.actions.config import Action

__copyright__ = "Copyright 2026, 3Liz"
__license__ = "GPL version 3"
__email__ = "info@3liz.org"

# Function called by Lizmap Web Client, with its signature
GET_DATA_FUNCTION = "public.lizmap_get_data(json)"

# Generic function converting a query to GeoJSON, used by the generated function
QUERY_TO_GEOJSON_FUNCTION = "public.query_to_geojson(text)"

QUERY_TO_GEOJSON_SQL = """-- Returns a valid GeoJSON from any query.
-- The query must return an "id" and a "geom" column, the other columns are the properties.
CREATE OR REPLACE FUNCTION public.query_to_geojson(datasource text)
RETURNS json AS
$$
DECLARE
    sqltext text;
    ajson json;
BEGIN
    sqltext := format('
        SELECT jsonb_build_object(
            ''type'', ''FeatureCollection'',
            ''features'', jsonb_agg(features.feature)
        )::json
        FROM (
            SELECT jsonb_build_object(
                ''type'', ''Feature'',
                ''id'', id,
                ''geometry'', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                ''properties'', to_jsonb(inputs) - ''geom''
            ) AS feature
            FROM (
                SELECT * FROM (%s) foo
            ) AS inputs
        ) AS features
    ', datasource);
    EXECUTE sqltext INTO ajson;
    RETURN ajson;
END;
$$
LANGUAGE plpgsql
VOLATILE STRICT;

COMMENT ON FUNCTION public.query_to_geojson(text) IS 'Generate a valid GeoJSON from a given SQL text query.

The query must return an "id" and a "geom" column, the other columns are written as properties.';
"""


@dataclass
class Database:
    """A PostgreSQL database used by some layers of the project."""

    # Human-readable name, such as 'gis on localhost:5432' or 'service my_service'
    label: str
    # A layer of the project stored in this database, to open a connection
    layer: QgsVectorLayer


def _database_label(uri: QgsDataSourceUri) -> str:
    """Human-readable name of the database of a datasource.

    :param uri: The datasource.
    :return: The service name, or the database name with the host and port.
    """
    if uri.service():
        return f"service '{uri.service()}'"
    return f"{uri.database()} ({uri.host()}:{uri.port() or '5432'})"


def databases(project: QgsProject, actions: list[Action]) -> list[Database]:
    """List the PostgreSQL databases of the project, the ones used by the actions first.

    :param project: The QGIS project.
    :param actions: The actions, to sort the databases.
    :return: The databases, without duplicate.
    """
    used_layer_ids = [
        layer_id for action in actions if action.scope.has_layers() for layer_id in action.layers
    ]

    # PostgreSQL layers, the ones used by the actions first
    layers = [
        layer
        for layer in project.mapLayers().values()
        if isinstance(layer, QgsVectorLayer) and layer.providerType() == "postgres"
    ]
    layers.sort(key=lambda layer: (layer.id() not in used_layer_ids, layer.name().lower()))

    # One entry per database
    result = []
    labels = set()
    for layer in layers:
        label = _database_label(QgsDataSourceUri(layer.source()))
        if label not in labels:
            labels.add(label)
            result.append(Database(label, layer))
    return result


def function_definition(layer: QgsVectorLayer, signature: str) -> str | None:
    """Read the definition of a function in the database of a layer.

    :param layer: A PostgreSQL layer, to open a connection to its database.
    :param signature: The function signature, such as 'public.lizmap_get_data(json)'. It must not come from a user.
    :return: The CREATE FUNCTION statement, or None if the function does not exist.
    :raises qgis.core.QgsProviderConnectionException: If the database cannot be reached.
    """
    metadata = QgsProviderRegistry.instance().providerMetadata("postgres")
    connection = metadata.createConnection(QgsDataSourceUri(layer.source()).uri(), {})
    # The signature is a constant of this module, not a value typed by the user
    result = connection.executeSql(  # nosec B608
        f"SELECT pg_catalog.pg_get_functiondef(pg_catalog.to_regprocedure('{signature}'))"
    )
    if not result or not result[0] or not result[0][0]:
        return None
    return str(result[0][0])


def _layer_names(project: QgsProject, action: Action) -> str:
    """Names of the layers of an action, for a SQL comment.

    :param project: The QGIS project.
    :param action: The action.
    :return: The layer names, or IDs if the layers are not in the project.
    """
    names = []
    for layer_id in action.layers:
        layer = project.mapLayer(layer_id)
        names.append(layer.name() if layer else layer_id)
    return ", ".join(names)


def _primary_key(project: QgsProject, action: Action) -> str:
    """Primary key of the first layer of an action, to find the feature.

    :param project: The QGIS project.
    :param action: The action.
    :return: The primary key column, 'id' by default.
    """
    for layer_id in action.layers:
        layer = project.mapLayer(layer_id)
        if layer:
            key = QgsDataSourceUri(layer.source()).keyColumn()
            if key:
                return key.strip('"')
    return "id"


def _geometry_column(project: QgsProject, action: Action) -> str:
    """Geometry column of the first layer of an action.

    :param project: The QGIS project.
    :param action: The action.
    :return: The geometry column, 'geom' by default.
    """
    for layer_id in action.layers:
        layer = project.mapLayer(layer_id)
        if layer:
            column = QgsDataSourceUri(layer.source()).geometryColumn()
            if column:
                return column
    return "geom"


def _sql_string(text: str) -> str:
    """Escape a text to be written inside a SQL string, itself inside the format() string.

    :param text: The text.
    :return: The text with each single quote written four times, and each '%' written twice for format().
    """
    return text.replace("'", "''''").replace("%", "%%")


def action_branch(project: QgsProject, action: Action, first: bool) -> str:
    """Write the IF branch of the lizmap_get_data function for an action.

    The query is an example depending on the scope, it must be adapted by the user.

    :param project: The QGIS project.
    :param action: The action.
    :param first: True for the first branch, written with IF instead of ELSIF.
    :return: The SQL code of the branch.
    """
    keyword = "IF" if first else "ELSIF"
    message = _sql_string(action.title)
    lines = [f"    {keyword} action_name = '{action.name}' THEN"]

    # Comments: scope, layers and options
    lines.append(f"        -- {action.title}")
    lines.append(f"        -- Scope : {action.scope.value}")
    if action.scope.has_layers():
        lines.append(f"        -- Layers : {_layer_names(project, action)}")
    for key, value in action.options.items():
        if key not in RESERVED_OPTION_KEYS:
            lines.append(f"        -- Option '{key}', default value {value!r} : parameters->>'{key}'")

    # Example of query according to the scope
    if action.scope == ActionScope.Feature:
        primary_key = _primary_key(project, action)
        geometry = _geometry_column(project, action)
        lines += [
            "        -- Returns the geometry of the feature",
            "        datasource := format('",
            f"            SELECT %1$L AS id, ''{message}'' AS message, {geometry} AS geom",
            "            FROM %2$I.%3$I",
            f"            WHERE {primary_key}::text = %1$L",
            "        ', feature_id, layer_schema, layer_table);",
        ]
    elif action.scope == ActionScope.Layer:
        geometry = _geometry_column(project, action)
        lines += [
            "        -- Returns the convex hull of all the features of the layer",
            "        datasource := format('",
            f"            SELECT 1 AS id, ''{message}'' AS message, ST_ConvexHull(ST_Collect({geometry})) AS geom",
            "            FROM %1$I.%2$I",
            "        ', layer_schema, layer_table);",
        ]
    else:
        # Geometry drawn by the user, or the map center
        source = "wkt" if action.geometry else "map_center"
        lines += [
            f"        -- Returns the {'geometry drawn by the user' if action.geometry else 'map center'}",
            "        datasource := format('",
            f"            SELECT 1 AS id, ''{message}'' AS message, ST_GeomFromText(%1$L, 4326) AS geom",
            f"        ', {source});",
        ]
    return "\n".join(lines)


def action_branches(project: QgsProject, actions: list[Action]) -> str:
    """Write the IF branches of the lizmap_get_data function for all actions.

    :param project: The QGIS project.
    :param actions: The actions.
    :return: The SQL code of the branches, to add in an existing function.
    """
    return "\n\n".join(action_branch(project, action, i == 0) for i, action in enumerate(actions))


def get_data_function(project: QgsProject, actions: list[Action]) -> str:
    """Write the complete lizmap_get_data function, with one branch per action.

    :param project: The QGIS project.
    :param actions: The actions.
    :return: The SQL code creating the function.
    """
    branches = action_branches(project, actions)
    if branches:
        branches += "\n\n    ELSE\n"
    else:
        branches = "    -- No action yet\n    IF TRUE THEN\n"

    return f"""-- Function called by Lizmap Web Client for each action.
-- It builds a query according to the action name, then returns the result as GeoJSON.
CREATE OR REPLACE FUNCTION public.lizmap_get_data(parameters json)
RETURNS json AS
$$
DECLARE
    action_name text;
    action_scope text;
    layer_name text;
    layer_schema text;
    layer_table text;
    feature_id text;
    map_center text;
    map_extent text;
    wkt text;
    user_login text;
    datasource text;
BEGIN
    -- Parameters sent by Lizmap Web Client.
    -- The options of the actions are also available, for instance parameters->>'buffer_size'.
    action_name := parameters->>'action_name';
    action_scope := parameters->>'action_scope';
    layer_name := parameters->>'layer_name';
    layer_schema := parameters->>'layer_schema';
    layer_table := parameters->>'layer_table';
    feature_id := parameters->>'feature_id';
    map_center := parameters->>'map_center';
    map_extent := parameters->>'map_extent';
    wkt := parameters->>'wkt';
    user_login := parameters->>'user_login';

    -- One query per action.
    -- Always use %L (literal) and %I (identifier) in format() for the values, to prevent SQL injection.
{branches}        -- Unknown action, no data
        RETURN NULL;
    END IF;

    RETURN public.query_to_geojson(datasource);
END;
$$
LANGUAGE plpgsql
VOLATILE;

COMMENT ON FUNCTION public.lizmap_get_data(json) IS 'Run a Lizmap action, called by Lizmap Web Client.

It builds a query according to the action name and the other parameters, such as the layer and the feature.

It returns the result of the query as GeoJSON.';
"""


def full_script(project: QgsProject, actions: list[Action]) -> str:
    """Write the complete SQL script, with both functions.

    :param project: The QGIS project.
    :param actions: The actions.
    :return: The SQL script.
    """
    return QUERY_TO_GEOJSON_SQL + "\n" + get_data_function(project, actions)
