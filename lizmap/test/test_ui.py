"""Test Lizmap dialog UI."""

from pathlib import Path

from qgis.core import QgsProject, QgsVectorLayer
from qgis.testing import unittest
from qgis.testing.mocked import get_iface

from lizmap.plugin import Lizmap
from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestUiLizmapDialog(unittest.TestCase):

    def tearDown(self) -> None:
        Path(plugin_test_data_path('unittest.qgs')).unlink(missing_ok=True)

    def test_ui(self):
        """ Test opening the Lizmap dialog with some basic checks."""
        project = QgsProject.instance()
        project.clear()
        lizmap = Lizmap(get_iface())

        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        project.addMapLayer(layer)

        layer = QgsVectorLayer(plugin_test_data_path('points.geojson'), 'points', 'ogr')
        project.addMapLayer(layer)

        flag, message = lizmap.check_global_project_options()
        self.assertFalse(flag, message)
        self.assertEqual(
            message,
            'You need to open a QGIS project, using the QGS extension.<br>This is needed before using other tabs in '
            'the plugin.')

        project.write(plugin_test_data_path('unittest.qgs'))
        flag, message = lizmap.check_global_project_options()
        self.assertTrue(flag, message)

        # lizmap.run()
        # lizmap.get_map_options()

    def test_legend_options(self):
        """ Test about reading legend options. """
        project = QgsProject.instance()
        project.read(plugin_test_data_path('legend_image_option.qgs'))
        self.assertEqual(3, len(project.mapLayers()))

        lizmap = Lizmap(get_iface())
        config = lizmap.read_lizmap_config_file()

        lizmap.myDic = {}
        root = project.layerTreeRoot()
        lizmap.process_node(root, None, config)
        lizmap.layerList = lizmap.myDic

        layers = lizmap.layerList
        self.assertEqual(
            'disabled',
            layers.get('legend_disabled_layer_id').get('legend_image_option'))

        self.assertEqual(
            'expand_at_startup',
            layers.get('legend_displayed_startup_layer_id').get('legend_image_option'))

        self.assertEqual(
            'hide_at_startup',
            layers.get('legend_hidden_startup_layer_id').get('legend_image_option'))
