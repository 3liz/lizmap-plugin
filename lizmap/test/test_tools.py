"""Test tools."""

import unittest

from qgis.core import QgsVectorLayer

from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path
from lizmap.tools import format_qgis_version, is_database_layer

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestTools(unittest.TestCase):

    def test_database_based_layer(self):
        """ Test if a layer is in a database. """
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        self.assertFalse(is_database_layer(layer))

        path = plugin_test_data_path('points_lines.gpkg', copy=True)
        layer = QgsVectorLayer(path + '|layername=lines', 'lines', 'ogr')
        self.assertTrue(is_database_layer(layer))

    def test_format_qgis_version(self):
        """ Test to get a correct QGIS version number. """
        self.assertTupleEqual((3, 12, 0), format_qgis_version(31100))
        self.assertTupleEqual((3, 10, 0), format_qgis_version(31000))
        self.assertTupleEqual((3, 4, 10), format_qgis_version(30410))
