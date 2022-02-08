__copyright__ = 'Copyright 2021, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.core import Qgis, QgsCoordinateReferenceSystem

""" Test filter by polygon. """

import unittest

from qgis.core import QgsFeature, QgsGeometry, QgsProject, QgsVectorLayer, edit

from lizmap.server.filter_by_polygon import FilterByPolygon


class TestFilterByPolygon(unittest.TestCase):

    @unittest.skipIf(Qgis.QGIS_VERSION_INT < 31000, 'Memory layer does not work well with 3.4')
    def test_not_filtered_layer(self):
        """ Test for not filtered layer. """
        json = {
            "config": {
                "polygon_layer_id": "FOO",
                "group_field": "groups"
            },
            "layers": [
                {
                    "layer": "BAR",
                    "primary_key": "primary",
                    "spatial_relationship": "intersects",
                    "filter_mode": "display_and_editing"
                }
            ]
        }
        points = QgsVectorLayer('Point?field=id:integer', 'points', 'memory')
        self.assertFalse(FilterByPolygon(json, points).is_filtered())
        self.assertFalse(FilterByPolygon(json, points).is_valid())

    # noinspection PyArgumentList
    @unittest.skipIf(Qgis.QGIS_VERSION_INT < 31000, 'Memory layer does not work well with 3.4')
    def test_filter_by_polygon_filter(self):
        """ Test the generation of filter by polygon. """
        polygon = QgsVectorLayer('Polygon?field=id:integer&field=groups:string', 'polygon', 'memory')
        with edit(polygon):
            feature = QgsFeature(polygon.fields())
            feature.setGeometry(QgsGeometry.fromWkt('POLYGON((0 0,0 5,5 5,5 0,0 0))'))
            feature.setAttributes([1, "east,admins"])
            self.assertTrue(polygon.addFeature(feature))

            feature = QgsFeature(polygon.fields())
            feature.setGeometry(QgsGeometry.fromWkt('POLYGON((0 0,0 -5,-5 -5,-5 0,0 0))'))
            feature.setAttributes([1, "west,admins"])
            self.assertTrue(polygon.addFeature(feature))

            #  -5                0                5
            #  ####################################
            #  #                 |                |
            #  #  west, admins   |  east, admins  |
            #  #                 |                |
            #  ####################################

        points = QgsVectorLayer('Point?field=id:integer', 'points', 'memory')
        with edit(points):
            # In east group
            feature = QgsFeature(points.fields())
            feature.setGeometry(QgsGeometry.fromWkt('POINT(1 1)'))
            feature.setAttributes([1])
            self.assertTrue(points.addFeature(feature))

            # Outside
            feature = QgsFeature(points.fields())
            feature.setGeometry(QgsGeometry.fromWkt('POINT(10 10)'))
            feature.setAttributes([2])
            self.assertTrue(points.addFeature(feature))

            # In west group
            feature = QgsFeature(points.fields())
            feature.setGeometry(QgsGeometry.fromWkt('POINT(-1 -1)'))
            feature.setAttributes([3])
            self.assertTrue(points.addFeature(feature))

        # The only layer is display_and_editing
        json = {
            "config": {
                "polygon_layer_id": polygon.id(),
                "group_field": "groups"
            },
            "layers": [
                {
                    "layer": points.id(),
                    "primary_key": "id",
                    "spatial_relationship": "intersects",
                    "filter_mode": "display_and_editing"
                }
            ]
        }

        project = QgsProject.instance()
        project.addMapLayer(polygon)

        config = FilterByPolygon(json, points, editing=False)
        self.assertTrue(config.is_filtered())
        self.assertTrue(FilterByPolygon(json, points).is_valid())

        # For unknown
        groups = ('unknown',)
        geom = config._polygon_for_groups_with_qgis_api(groups)
        self.assertTrue(geom.isEmpty())
        subset, ewkt = config.subset_sql(groups)
        self.assertEqual('1 = 0', subset)
        self.assertEqual('', ewkt)

        # For admins, they see everything inside, not the one outside
        groups = ('admins',)
        geom = config._polygon_for_groups_with_qgis_api(groups)
        self.assertEqual(
            'MultiPolygon (((0 0, 0 5, 5 5, 5 0, 0 0)),((0 0, 0 -5, -5 -5, -5 0, 0 0)))',
            geom.asWkt(0))
        subset, ewkt = config.subset_sql(groups)
        self.assertEqual('"id" IN ( 1 , 3 )', subset)
        self.assertEqual(
            'SRID=4326;MultiPolygon (((0 0, 0 5, 5 5, 5 0, 0 0)),((0 0, 0 -5, -5 -5, -5 0, 0 0)))', ewkt)

        # For east
        groups = ('east',)
        geom = config._polygon_for_groups_with_qgis_api(groups)
        self.assertEqual(
            'MultiPolygon (((0 0, 0 5, 5 5, 5 0, 0 0)))',
            geom.asWkt(0))
        subset, ewkt = config.subset_sql(groups)
        self.assertEqual('"id" IN ( 1 )', subset)
        self.assertEqual(
            'SRID=4326;MultiPolygon (((0 0, 0 5, 5 5, 5 0, 0 0)))', ewkt)

        # For west
        groups = ('west',)
        geom = config._polygon_for_groups_with_qgis_api(groups)
        self.assertEqual(
            'MultiPolygon (((0 0, 0 -5, -5 -5, -5 0, 0 0)))',
            geom.asWkt(0))
        subset, ewkt = config.subset_sql(groups)
        self.assertEqual('"id" IN ( 3 )', subset)
        self.assertEqual(
            'SRID=4326;MultiPolygon (((0 0, 0 -5, -5 -5, -5 0, 0 0)))', ewkt)

        # The only layer is editing only
        json = {
            "config": {
                "polygon_layer_id": polygon.id(),
                "group_field": "groups"
            },
            "layers": [
                {
                    "layer": points.id(),
                    "primary_key": "id",
                    "spatial_relationship": "intersects",
                    "filter_mode": "editing"
                }
            ]
        }

        config = FilterByPolygon(json, points, editing=False)
        self.assertTrue(config.is_filtered())
        self.assertTrue(FilterByPolygon(json, points).is_valid())

        groups = ('admins',)
        subset, ewkt = config.subset_sql(groups)
        self.assertEqual('', subset)
        self.assertEqual('', ewkt)

        config = FilterByPolygon(json, points, editing=True)
        self.assertTrue(config.is_filtered())
        self.assertTrue(FilterByPolygon(json, points).is_valid())

        groups = ('admins',)
        geom = config._polygon_for_groups_with_qgis_api(groups)
        self.assertEqual(
            'MultiPolygon (((0 0, 0 5, 5 5, 5 0, 0 0)),((0 0, 0 -5, -5 -5, -5 0, 0 0)))',
            geom.asWkt(0))
        # self.assertEqual('"id" IN (1, 3)', config.subset_sql(groups))
        # self.assertEqual('', config.subset_sql(groups))
        project.clear()

    def test_format_sql_in(self):
        """ Test SQL IN statement. """
        # Integer only
        sql = FilterByPolygon._format_sql_in('code', (1, 2, 3))
        expected = '"code" IN ( 1 , 2 , 3 )'
        self.assertEqual(expected, sql)

        # Integer as string
        sql = FilterByPolygon._format_sql_in('code', ('1', '2', '3'))
        expected = '"code" IN ( \'1\' , \'2\' , \'3\' )'
        self.assertEqual(expected, sql)

        # String
        sql = FilterByPolygon._format_sql_in('code', ('a', 'b', 'c'))
        expected = '"code" IN ( \'a\' , \'b\' , \'c\' )'
        self.assertEqual(expected, sql)

    def test_subset_string_postgres(self):
        """ Test building a postgresql string for filter by polygon. """
        # ST_Intersect
        sql = FilterByPolygon._format_sql_st_relationship(
            QgsCoordinateReferenceSystem(2154),
            QgsCoordinateReferenceSystem(4326),
            'geom',
            QgsGeometry.fromWkt('POLYGON((0 0,0 5,5 5,5 0,0 0))'),
            use_st_intersect=True,
        )
        expected = """
ST_Intersects(
    ST_Transform(ST_GeomFromText('Polygon ((0 0, 0 5, 5 5, 5 0, 0 0))', 4326), 2154),
    "geom"
)"""
        self.assertEqual(expected, sql)

        # ST_Contains
        sql = FilterByPolygon._format_sql_st_relationship(
            QgsCoordinateReferenceSystem(2154),
            QgsCoordinateReferenceSystem(4326),
            'geom',
            QgsGeometry.fromWkt('POLYGON((0 0,0 5,5 5,5 0,0 0))'),
            use_st_intersect=False,
        )
        expected = """
ST_Contains(
    ST_Transform(ST_GeomFromText('Polygon ((0 0, 0 5, 5 5, 5 0, 0 0))', 4326), 2154),
    "geom"
)"""
        self.assertEqual(expected, sql)
