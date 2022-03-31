"""Test Lizmap dialog UI."""

import os

from qgis.core import QgsProject, QgsVectorLayer
from qgis.testing import unittest
from qgis.testing.mocked import get_iface

from lizmap.plugin import Lizmap
from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestUiLizmapDialog(unittest.TestCase):

    def tearDown(self) -> None:
        os.remove(plugin_test_data_path('unittest.qgs'))

    def test_ui(self):
        """ Test opening the Lizmap dialog with some basic checks."""
        project = QgsProject.instance()
        lizmap = Lizmap(get_iface())

        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        project.addMapLayer(layer)

        layer = QgsVectorLayer(plugin_test_data_path('points.geojson'), 'points', 'ogr')
        project.addMapLayer(layer)

        flag, message = lizmap.check_global_project_options()
        self.assertFalse(flag, message)
        self.assertEqual(message, 'You need to open a QGIS project, using the QGS extension, before using Lizmap.')

        project.write(plugin_test_data_path('unittest.qgs'))
        flag, message = lizmap.check_global_project_options()
        self.assertTrue(flag, message)

        # lizmap.run()
        # lizmap.get_map_options()
