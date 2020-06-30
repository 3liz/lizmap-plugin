"""Test tools."""

import unittest

from qgis.core import QgsVectorLayer

from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path
from lizmap.tools import is_database_layer

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestTools(unittest.TestCase):

    def test_database_based_layer(self):
        """ Test if a layer is in a database. """
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        self.assertFalse(is_database_layer(layer))

        layer = QgsVectorLayer(plugin_test_data_path('points_lines.gpkg|layername=lines'), 'lines', 'ogr')
        self.assertTrue(is_database_layer(layer))
