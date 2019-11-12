"""Test Lizmap dialog UI."""

from qgis.core import QgsVectorLayer, QgsProject
from qgis.testing import unittest, start_app
from qgis.testing.mocked import get_iface

from ..lizmap import Lizmap
from ..qgis_plugin_tools.tools.resources import plugin_test_data_path


start_app()

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestUiLizmapDialog(unittest.TestCase):

    def test_ui(self):
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
