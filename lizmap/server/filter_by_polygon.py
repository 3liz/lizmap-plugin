__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from functools import lru_cache
from typing import Tuple

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDataSourceUri,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProject,
    QgsSpatialIndex,
    QgsVectorLayer,
)

if Qgis.QGIS_VERSION_INT > 31000:
    import binascii

    from qgis.core import QgsProviderRegistry

from lizmap.server.logger import Logger, profiling

# TODO implement LRU cache with this variable
CACHE_MAX_SIZE = 100

# 1 = 0 results in a "false" in OGR/PostGIS
# ET : I didn't find a proper false value in OGR
NO_FEATURES = '1 = 0'
ALL_FEATURES = ''


class FilterByPolygon:

    def __init__(
            self, config: dict, layer: QgsVectorLayer, editing: bool = False, use_st_intersect: bool = False):
        """Constructor for the filter by polygon.

        :param config: The filter by polygon configuration as dictionary
        :param layer: The vector layer to filter
        """
        # QGIS Server can consider the ST_Intersect not safe regarding SQL injection.
        # Using this flag will transform or not the ST_Intersect into an IN by making the query straight to
        # PostGIS.
        self.use_st_intersect = use_st_intersect
        self.config = config
        self.editing = editing
        # noinspection PyArgumentList
        self.project = QgsProject.instance()

        # Current layer in the request
        self.layer = layer

        # Will be filled if the current layer is filtered
        self.primary_key = None
        self.filter_mode = None

        # Will be filled with the polygon layer
        self.polygon = None
        self.group_field = None

        # Read the configuration
        self._parse()

    def is_filtered(self) -> bool:
        """If the configuration is filtering the given layer."""
        return self.primary_key is not None

    @profiling
    def _parse(self) -> None:
        """Read the configuration and fill variables"""
        # Leave as quick as possible
        if not self.layer.isSpatial():
            return None

        if self.config is None:
            return None

        layers = self.config.get('layers')
        if not layers:
            return None

        for layer in layers:
            if layer.get("layer") == self.layer.id():
                self.primary_key = layer.get('primary_key')
                self.filter_mode = layer.get('filter_mode')
                break

        if self.primary_key is None:
            return None

        config = self.config.get("config")
        self.polygon = self.project.mapLayer(config['polygon_layer_id'])
        self.group_field = config.get("group_field")

    def is_valid(self) -> bool:
        """ If the configuration is valid or not."""
        if not self.polygon:
            Logger.critical("The polygon layer for filtering is not valid.")
            return False

        if not self.polygon and self.polygon.isValid():
            Logger.critical("The polygon layer for filtering is not valid.")
            return False

        if self.polygon.fields().indexOf(self.group_field) < 0:
            Logger.critical(
                "The field {} used for filtering does not exist in {}".format(
                    self.group_field, self.polygon.name()))
            return False

        if not self.layer.isValid():
            Logger.critical(
                "The field {} used for filtering does not exist in {}".format(
                    self.primary_key, self.layer.name()))
            return False

        if self.layer.fields().indexOf(self.primary_key) < 0:
            Logger.critical(
                "The field {} used for filtering does not exist in {}".format(
                    self.primary_key, self.layer.name()))

        return True

    @profiling
    def subset_sql(self, groups: tuple) -> Tuple[str, str]:
        """ Get the SQL subset string for the current groups of the user.

        :param groups: List of groups belongings to the user.
        :returns: The subset SQL string to use
        """
        if self.filter_mode == 'editing':
            if not self.editing:
                Logger.info(
                    "Layer is editing only BUT we are not in an editing session. Return all features.")
                return ALL_FEATURES, ''

            Logger.info(
                "Layer is editing only AND we are in an editing session. Continue to find the subset string")

        # We need to have a cache for this, valid for the combo polygon layer id & user_groups
        # as it will be done for each WMS or WFS query
        if self.polygon.providerType() == 'postgres' and Qgis.QGIS_VERSION_INT > 31000:
            polygon = self._polygon_for_groups_with_sql_query(groups)
        else:
            polygon = self._polygon_for_groups_with_qgis_api(groups)
        # Logger.info("LRU Cache _polygon_for_groups : {}".format(self._polygon_for_groups.cache_info()))

        if polygon.isEmpty():
            return NO_FEATURES, ''

        ewkt = "SRID={crs};{wkt}".format(
            crs=self.polygon.crs().postgisSrid(),
            wkt=polygon.asWkt(6 if self.polygon.crs().isGeographic() else 2)
        )

        if self.layer.providerType() == 'postgres':
            if self.use_st_intersect or Qgis.QGIS_VERSION_INT > 31000:
                uri = QgsDataSourceUri(self.layer.source())
                st_intersect = self._format_sql_st_intersects(
                    self.layer.sourceCrs(),
                    self.polygon.sourceCrs(),
                    uri.geometryColumn(),
                    polygon)

                if self.use_st_intersect:
                    return st_intersect, ewkt

                return self._features_ids_with_sql_query(st_intersect), ewkt

        # Still here ? So we use the slow method with QGIS API
        subset = self._features_ids_with_qgis_api(polygon)
        # Logger.info("LRU Cache _layer_not_postgres : {}".format(self._layer_not_postgres.cache_info()))
        return subset, ewkt

    @profiling
    @lru_cache(maxsize=CACHE_MAX_SIZE)
    def _polygon_for_groups_with_qgis_api(self, groups: tuple) -> QgsGeometry:
        """ All features from the polygon layer corresponding to the user groups """
        expression = """
array_intersect(
    array_foreach(
        string_to_array("{polygon_field}"),
        trim(@element)
    ),
    array_foreach(
        string_to_array('{groups}'),
        trim(@element)
    )
)""".format(
            polygon_field=self.group_field,
            groups=','.join(groups)
        )

        # Create request
        request = QgsFeatureRequest()
        request.setSubsetOfAttributes([])
        request.setFilterExpression(expression)

        polygon_geoms = []
        for feature in self.polygon.getFeatures(request):
            polygon_geoms.append(feature.geometry())

        return QgsGeometry().collectGeometry(polygon_geoms)

    @profiling
    @lru_cache(maxsize=CACHE_MAX_SIZE)
    def _polygon_for_groups_with_sql_query(self, groups: tuple) -> QgsGeometry:
        """ All features from the polygon layer corresponding to the user groups for a Postgresql layer.

        Only for QGIS >= 3.10
        """
        uri = QgsDataSourceUri(self.polygon.source())
        try:
            sql = r"""
WITH current_groups AS (
    SELECT
        ARRAY_REMOVE(
            STRING_TO_ARRAY(
                regexp_replace(
                    '{groups}', '[^a-zA-Z0-9_-]', ',', 'g'
                ),
                ','
            ),
        '') AS user_group
),
polygons AS (
    SELECT
        id, geom,
        ARRAY_REMOVE(
            STRING_TO_ARRAY(
                regexp_replace(
                    '{polygon_field}', '[^a-zA-Z0-9_-]', ',', 'g'
                ),
                ','
            ),
        '') AS polygon_groups
    FROM {schema}.{table}
)
SELECT '1' AS id, ST_AsBinary(ST_Union(geom)) AS geom
FROM
    current_groups c,
    polygons p
WHERE c.user_group && p.polygon_groups
""".format(
                polygon_field=self.group_field,
                groups=','.join(groups),
                schema=uri.schema(),
                table=uri.table(),
            )
            Logger.info(
                "Requesting the database about polygons for the current groups with : \n{}".format(sql))

            # noinspection PyArgumentList
            metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
            connection = metadata.createConnection(uri.uri(), {})
            results = connection.executeSql(sql)
            wkb = results[0][1]

            geom = QgsGeometry()
            # Remove \x from string
            # Related to https://gis.stackexchange.com/questions/411545/use-st-asbinary-from-postgis-in-pyqgis
            geom.fromWkb(binascii.a2b_hex(wkb[2:]))
            return geom
        except Exception as e:
            # Let's be safe
            Logger.log_exception(e)
            Logger.critical(
                "The filter_by_polygon._polygon_for_groups_with_sql_query failed when requesting PostGIS.\n"
                "Using the QGIS API")
            return self._polygon_for_groups_with_qgis_api(groups)

    @profiling
    @lru_cache(maxsize=CACHE_MAX_SIZE)
    def _features_ids_with_qgis_api(self, polygons: QgsGeometry) -> str:
        """ List all features using the QGIS API.

        :returns: The subset SQL string.
        """
        # For other types, we need to find all the ids with an expression
        # And then search for these ids in the substring, as it must be SQL

        # Build the spatial index
        index = QgsSpatialIndex()
        index.addFeatures(self.layer.getFeatures())

        # Find candidates, if not already in cache
        transform = QgsCoordinateTransform(self.polygon.crs(), self.layer.crs(), self.project)
        polygons.transform(transform)
        candidates = index.intersects(polygons.boundingBox())

        # Check real intersection for the candidates
        unique_ids = []
        for candidate_id in candidates:
            feature = self.layer.getFeature(candidate_id)
            if feature.geometry().intersects(polygons):
                unique_ids.append(str(feature[self.primary_key]))

        return self._format_sql_in(self.primary_key, unique_ids)

    @profiling
    @lru_cache(maxsize=CACHE_MAX_SIZE)
    def _features_ids_with_sql_query(self, st_intersect: str) -> str:
        """ List all features using a SQL query.

        Only for QGIS >= 3.10

        :returns: The subset SQL string.
        """
        uri = QgsDataSourceUri(self.layer.source())

        sql = 'SELECT {pk} FROM {schema}.{table} WHERE {st_intersect}'.format(
            pk=self.primary_key,
            schema=uri.schema(),
            table=uri.table(),
            st_intersect=st_intersect,
        )
        Logger.info(
            "Requesting the database about IDs to filter with {}...".format(sql[0:90]))

        # noinspection PyArgumentList
        metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
        connection = metadata.createConnection(uri.uri(), {})
        results = connection.executeSql(sql)

        unique_ids = [str(row[0]) for row in results]

        return self._format_sql_in(self.primary_key, unique_ids)

    @classmethod
    def _format_sql_in(cls, primary_key: str, values: list) -> str:
        """Format the SQL IN statement."""
        if not values:
            return NO_FEATURES

        return '"{pk}" IN ( {values} )'.format(pk=primary_key, values=' , '.join(values))

    @classmethod
    def _format_sql_st_intersects(
            cls,
            filtered_crs: QgsCoordinateReferenceSystem,
            filtering_crs: QgsCoordinateReferenceSystem,
            geom_field: str,
            polygons: QgsGeometry) -> str:
        """If layer is of type PostgreSQL, use a simple ST_Intersects.

        :returns: The subset SQL string.
        """
        sql = """ST_Intersects(
    "{geom_field}",
    ST_Transform(ST_GeomFromText('{wkt}', {from_crs}), {to_crs})
)""".format(
            geom_field=geom_field,
            wkt=polygons.asWkt(6 if filtering_crs.isGeographic() else 2),
            from_crs=filtering_crs.postgisSrid(),
            to_crs=filtered_crs.postgisSrid()
        )
        return sql
