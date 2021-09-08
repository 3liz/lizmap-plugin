__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from functools import lru_cache

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDataSourceUri,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProject,
    QgsSpatialIndex,
    QgsVectorLayer,
)

from lizmap.server.logger import Logger, profiling

# TODO implement LRU cache with this variable
CACHE_MAX_SIZE = 100

# 1 = 0 results in a "false" in OGR/PostGIS
# ET : I didn't find a proper false value in OGR
NO_FEATURES = '1 = 0'


class FilterByPolygon:

    def __init__(
            self, config: dict, layer: QgsVectorLayer, editing: bool = False, use_st_intersect: bool = False):
        """Constructor for the filter by polygon.

        :param config: The filter by polygon configuration as dictionary
        :param layer: The vector layer to filter
        """
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
        # Leave as quick it's possible
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

    @profiling
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
    def subset_sql(self, groups: tuple) -> str:
        """ Get the SQL subset string for the current groups of the user.

        :param groups: List of groups belongings to the user.
        :returns: The subset SQL string to use
        """
        if self.filter_mode == 'editing':
            return ''
            # if not self.editing:
            #     Logger.info(
            #         "Layer is editing only but we are not in an editing session. Return all features.")
            #     return ''
            # else:
            #     Logger.info(
            #         "Layer is editing only and we are in an editing session. Continue to find the subset "
            #         "string")

        # We need to have a cache for this, valid for the combo polygon layer id & user_groups
        # as it will be done for each WMS or WFS query
        polygon = self._polygon_for_groups(groups)
        # Logger.info("LRU Cache _polygon_for_groups : {}".format(self._polygon_for_groups.cache_info()))

        if polygon.isEmpty():
            return NO_FEATURES

        if self.layer.providerType() == 'postgres':
            if self.use_st_intersect:
                uri = QgsDataSourceUri(self.layer.source())
                sql = self._layer_postgres(
                    self.layer.sourceCrs(),
                    self.polygon.sourceCrs(),
                    uri.geometryColumn(),
                    polygon)
                return sql

            else:
                Logger.info("Layer is postgres, but not using ST_Intersect")

        subset = self._layer_not_postgres(polygon)
        # Logger.info("LRU Cache _layer_not_postgres : {}".format(self._layer_not_postgres.cache_info()))
        return subset

    @profiling
    @lru_cache(maxsize=CACHE_MAX_SIZE)
    def _polygon_for_groups(self, groups: tuple) -> QgsGeometry:
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
    def _layer_not_postgres(self, polygons: QgsGeometry) -> str:
        """ When the layer is not a postgres based layer.

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

        if not unique_ids:
            return NO_FEATURES

        return '"{}" IN ({})'.format(self.primary_key, ', '.join(unique_ids))

    @classmethod
    @profiling
    def _layer_postgres(
            cls,
            filtered_crs: QgsCoordinateReferenceSystem,
            filtering_crs: QgsCoordinateReferenceSystem,
            geom_field: str,
            polygons: QgsGeometry) -> str:
        """If layer is of type PostgreSQL, use a simple ST_Intersects.

        :returns: The subset SQL string.
        """
        if filtering_crs.isGeographic():
            decimals = 6
        else:
            decimals = 2

        sql = """ST_Intersects(
    "{geom_field}",
    ST_Transform(ST_GeomFromText('{wkt}', {from_crs}), {to_crs})
)""".format(
            geom_field=geom_field,
            wkt=polygons.asWkt(decimals),
            from_crs=filtering_crs.postgisSrid(),
            to_crs=filtered_crs.postgisSrid()
        )
        return sql
