"""Test Lizmap dialog UI."""

from pathlib import Path

from qgis.core import QgsProject, QgsVectorLayer
from qgis.testing import unittest
from qgis.testing.mocked import get_iface

from lizmap.definitions.definitions import LwcVersions
from lizmap.plugin import Lizmap
from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path
from lizmap.test.utils import temporary_file_path

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
        lizmap.process_node(project.layerTreeRoot(), None, config)
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
        self.assertEqual(output['layers']['legend_displayed_startup']['noLegendImage'], str(False))

    def _setup_empty_project(self):
        """ Internal function to add a layer and a basic check. """
        project = QgsProject.instance()
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        project.addMapLayer(layer)
        project.setFileName(temporary_file_path())

        lizmap = Lizmap(get_iface())
        # Do not use read_lizmap_config_file
        # as it will be called by read_cfg_file and also the UI is set in read_cfg_file
        config = lizmap.read_cfg_file(skip_tables=True)

        lizmap.set_initial_extent_from_canvas()

        # Config is empty in the CFG file because it's a new project
        self.assertDictEqual({}, config)

        # Some process
        lizmap.myDic = {}
        lizmap.process_node(project.layerTreeRoot(), None, {})
        lizmap.layerList = lizmap.myDic

        return lizmap

    def test_lizmap_layer_properties(self):
        """ Test apply some properties in a layer in the dialog. """
        lizmap = self._setup_empty_project()

        # Click the layer
        item = lizmap.dlg.layer_tree.topLevelItem(0)
        self.assertEqual(item.text(0), 'lines')
        self.assertTrue(item.text(1).startswith('lines_'))
        self.assertEqual(item.text(2), 'layer')
        lizmap.dlg.layer_tree.setCurrentItem(lizmap.dlg.layer_tree.topLevelItem(0))

        # Fill the ACL field
        acl_layer = "a_group_id"
        lizmap.dlg.list_group_visibility.setText(acl_layer)
        lizmap.save_value_layer_group_data('group_visibility')

        # Fill the abstract field
        html_abstract = "<strong>Hello</strong>"
        lizmap.dlg.teLayerAbstract.setPlainText(html_abstract)
        lizmap.save_value_layer_group_data('abstract')

        # Check new values in the output config
        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False)
        self.assertListEqual(output['layers']['lines']['group_visibility'], [acl_layer])
        self.assertEqual(output['layers']['lines']['abstract'], html_abstract)

        # Test a false value as a string which shouldn't be there by default
        self.assertIsNone(output['layers']['lines'].get('externalWmsToggle'))
        self.assertIsNone(output['layers']['lines'].get('metatileSize'))

    def test_general_scales_properties(self):
        """ Test some UI settings about general properties. """
        lizmap = self._setup_empty_project()

        # Check default values
        self.assertEqual('10000, 25000, 50000, 100000, 250000, 500000', lizmap.dlg.inMapScales.text())

        # Default values from config.py at the beginning only
        self.assertEqual('1', lizmap.dlg.inMinScale.text())
        self.assertEqual('1000000000', lizmap.dlg.inMaxScale.text())

        # Trigger the signal
        lizmap.get_min_max_scales()

        # Values from the UI
        self.assertEqual('10000', lizmap.dlg.inMinScale.text())
        self.assertEqual('500000', lizmap.dlg.inMaxScale.text())

        scales = '1000, 5000, 15000'

        # Fill scales
        lizmap.dlg.inMapScales.setText(scales)
        lizmap.get_min_max_scales()
        self.assertEqual('1000', lizmap.dlg.inMinScale.text())
        self.assertEqual('15000', lizmap.dlg.inMaxScale.text())
        self.assertEqual(scales, lizmap.dlg.inMapScales.text())

        # Check new values in the output config
        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False)

        # Check scales in the CFG
        self.assertEqual(1000, output['options']['minScale'])
        self.assertEqual(15000, output['options']['maxScale'])
        self.assertListEqual([1000, 5000, 15000], output['options']['mapScales'])

    def test_general_properties_true_values(self):
        """ Test some UI settings about boolean values. """
        lizmap = self._setup_empty_project()

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False)
        self.assertIsNone(output['options'].get('atlasAutoPlay'))

        lizmap.dlg.atlasAutoPlay.setChecked(True)

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False)
        self.assertTrue(output['options'].get('atlasAutoPlay'))

        lizmap.dlg.atlasAutoPlay.setChecked(False)

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False)
        self.assertIsNone(output['options'].get('atlasAutoPlay'))

        # Test some strings as well as default value
        self.assertEqual("dock", output['options'].get('popupLocation'))
        self.assertEqual("seconds", output["options"].get("tmTimeFrameType"))
        # Not working for now, maybe because of the table manager
        # self.assertEqual("light", output['options'].get('theme'))


if __name__ == "__main__":
    from qgis.testing import start_app
    start_app()
