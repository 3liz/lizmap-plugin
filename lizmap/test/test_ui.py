"""Test Lizmap dialog UI."""

from pathlib import Path

from qgis.core import QgsProject, QgsVectorLayer
from qgis.testing import unittest
from qgis.testing.mocked import get_iface

from lizmap.definitions.definitions import LwcVersions
from lizmap.plugin import Lizmap
from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestUiLizmapDialog(unittest.TestCase):

    def tearDown(self) -> None:
        """ Cleaning data."""
        filepath = Path(plugin_test_data_path('unittest.qgs'))
        if filepath.exists():
            filepath.unlink()

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

        self.assertEqual(
            'disabled',
            lizmap.myDic.get('legend_disabled_layer_id').get('legend_image_option'))

        self.assertEqual(
            'expand_at_startup',
            lizmap.myDic.get('legend_displayed_startup_layer_id').get('legend_image_option'))

        self.assertEqual(
            'hide_at_startup',
            lizmap.myDic.get('legend_hidden_startup_layer_id').get('legend_image_option'))

        # For LWC 3.6
        output = lizmap.project_config_file(LwcVersions.Lizmap_3_6, check_server=False)
        self.assertEqual(output['layers']['legend_displayed_startup']['legend_image_option'], 'expand_at_startup')
        self.assertIsNone(output['layers']['legend_displayed_startup'].get('noLegendImage'))

        # For LWC 3.5
        output = lizmap.project_config_file(LwcVersions.Lizmap_3_5, with_gui=False, check_server=False)
        self.assertIsNone(output['layers']['legend_displayed_startup'].get('legend_image_option'))
        self.assertEqual(output['layers']['legend_displayed_startup']['noLegendImage'], 'False')
