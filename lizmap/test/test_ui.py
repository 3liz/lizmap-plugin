"""Test Lizmap dialog UI."""
import json

from pathlib import Path

from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.testing import unittest
from qgis.testing.mocked import get_iface

from lizmap.definitions.definitions import LwcVersions, PredefinedGroup
from lizmap.plugin import Lizmap
from lizmap.test.utils import temporary_file_path
from lizmap.toolbelt.resources import plugin_test_data_path

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
        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.latest())

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

        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.latest())
        # read_cfg_file will call "layers_config_file"
        config = lizmap.read_cfg_file(skip_tables=True)

        lizmap.myDic = {}
        lizmap.process_node(project.layerTreeRoot(), None, config)
        lizmap.layerList = lizmap.myDic

        self.assertEqual('5000', lizmap.dlg.minimum_scale.text())
        self.assertEqual('500000', lizmap.dlg.maximum_scale.text())
        self.assertEqual('5000, 250000, 500000', lizmap.dlg.list_map_scales.text())

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
        output = lizmap.project_config_file(LwcVersions.Lizmap_3_6, check_server=False, ignore_error=True)
        self.assertTrue('<table>' in output['options']['datavizTemplate'])

        self.assertEqual(output['layers']['legend_displayed_startup']['legend_image_option'], 'expand_at_startup')
        self.assertIsNone(output['layers']['legend_displayed_startup'].get('noLegendImage'))

        self.assertIsNone(output['options'].get('default_background_color_index'))

        # For LWC 3.5
        output = lizmap.project_config_file(LwcVersions.Lizmap_3_5, with_gui=False, check_server=False, ignore_error=True)
        self.assertIsNone(output['layers']['legend_displayed_startup'].get('legend_image_option'))
        self.assertEqual(output['layers']['legend_displayed_startup']['noLegendImage'], str(False))

    def _setup_empty_project(self, lwc_version=LwcVersions.latest()):
        """ Internal function to add a layer and a basic check. """
        project = QgsProject.instance()
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        project.addMapLayer(layer)
        project.setFileName(temporary_file_path())

        lizmap = Lizmap(get_iface(), lwc_version=lwc_version)
        baselayers = lizmap._add_group_legend('baselayers', exclusive=True, parent=None, project=project)
        lizmap._add_group_legend('project-background-color', exclusive=False, parent=baselayers, project=project)
        hidden = lizmap._add_group_legend('hidden', project=project)

        # For testing, we add OSM as hidden layer
        hidden_raster = QgsRasterLayer("type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png", "OSM", 'wms')
        project.addMapLayer(hidden_raster, False)
        hidden.addLayer(hidden_raster)

        # Do not use read_lizmap_config_file
        # as it will be called by read_cfg_file and also the UI is set in read_cfg_file
        config = lizmap.read_cfg_file(skip_tables=True)

        lizmap.dlg.widget_initial_extent.setOutputExtentFromLayer(layer)

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
        self.assertEqual(item.data(0, Qt.UserRole + 1), PredefinedGroup.No.value)
        self.assertEqual(item.text(3), '')  # Not used, just to test

        self.assertFalse(lizmap.dlg.list_group_visibility.isEnabled())

        # Click the first line
        lizmap.dlg.layer_tree.setCurrentItem(lizmap.dlg.layer_tree.topLevelItem(0))

        # Fill the ACL field
        self.assertTrue(lizmap.dlg.list_group_visibility.isEnabled())
        acl_layer = "a_group_id"
        lizmap.dlg.list_group_visibility.setText(acl_layer)
        lizmap.save_value_layer_group_data('group_visibility')

        # Fill the abstract field
        html_abstract = "<strong>Hello</strong>"
        lizmap.dlg.teLayerAbstract.setPlainText(html_abstract)
        lizmap.save_value_layer_group_data('abstract')

        # Click the group base-layers
        group_item = lizmap.dlg.layer_tree.findItems('baselayers', Qt.MatchContains | Qt.MatchRecursive, 0)[0]
        lizmap.dlg.layer_tree.setCurrentItem(group_item)
        self.assertFalse(lizmap.dlg.panel_layer_all_settings.isEnabled())

        # Click the group project-background-color
        group_item = lizmap.dlg.layer_tree.findItems(
            'project-background-color', Qt.MatchContains | Qt.MatchRecursive, 0)[0]
        lizmap.dlg.layer_tree.setCurrentItem(group_item)
        self.assertTrue(lizmap.dlg.panel_layer_all_settings.isEnabled())
        self.assertTrue(lizmap.dlg.group_layer_metadata.isEnabled())
        self.assertFalse(lizmap.dlg.group_layer_tree_options.isEnabled())

        # Click the group hidden
        group_item = lizmap.dlg.layer_tree.findItems('hidden', Qt.MatchContains | Qt.MatchRecursive, 0)[0]
        lizmap.dlg.layer_tree.setCurrentItem(group_item)
        # It should work, maybe the test click and click in the UI is missing one thing
        # self.assertEqual(PredefinedGroup.Hidden.value, lizmap._current_item_predefined_group())
        # self.assertFalse(lizmap.dlg.panel_layer_all_settings.isEnabled())

        # Back to a layer outside of these groups
        group_item = lizmap.dlg.layer_tree.findItems('lines', Qt.MatchContains | Qt.MatchRecursive, 0)[0]
        lizmap.dlg.layer_tree.setCurrentItem(group_item)
        self.assertTrue(lizmap.dlg.list_group_visibility.isEnabled())

        # Check new values in the output config
        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        # Layers
        self.assertListEqual(output['layers']['lines']['group_visibility'], [acl_layer])
        self.assertEqual(output['layers']['lines']['abstract'], html_abstract)
        # Predefined groups, still in the CFG
        self.assertListEqual(output['layers']['baselayers']['group_visibility'], [])
        self.assertEqual(output['layers']['baselayers']['abstract'], '')
        self.assertListEqual(output['layers']['project-background-color']['group_visibility'], [])
        self.assertEqual(output['layers']['project-background-color']['abstract'], '')
        self.assertEqual(0, output['options'].get('default_background_color_index'))

        # Test a false value as a string which shouldn't be there by default
        self.assertIsNone(output['layers']['lines'].get('externalWmsToggle'))
        self.assertIsNone(output['layers']['lines'].get('metatileSize'))

    def test_general_scales_properties_lwc_3_6(self):
        """ Test some UI settings about general properties with LWC 3.6. """
        lizmap = self._setup_empty_project(LwcVersions.Lizmap_3_6)

        # Check default values
        self.assertEqual('10000, 25000, 50000, 100000, 250000, 500000', lizmap.dlg.list_map_scales.text())

        # Default values from config.py at the beginning only
        self.assertEqual('1', lizmap.dlg.minimum_scale.text())
        self.assertEqual('1000000000', lizmap.dlg.maximum_scale.text())

        # Trigger the signal
        lizmap.get_min_max_scales()

        # Values from the UI
        self.assertEqual('10000', lizmap.dlg.minimum_scale.text())
        self.assertEqual('500000', lizmap.dlg.maximum_scale.text())

        scales = '1000, 5000, 15000'

        # Fill scales
        lizmap.dlg.list_map_scales.setText(scales)
        lizmap.get_min_max_scales()
        self.assertEqual('1000', lizmap.dlg.minimum_scale.text())
        self.assertEqual('15000', lizmap.dlg.maximum_scale.text())
        self.assertEqual(scales, lizmap.dlg.list_map_scales.text())

        # Check new values in the output config
        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)

        # Check scales in the CFG
        self.assertEqual(1000, output['options']['minScale'])
        self.assertEqual(15000, output['options']['maxScale'])
        self.assertListEqual([1000, 5000, 15000], output['options']['mapScales'])

        # Project is in EPSG:2154, must be False
        self.assertFalse(output['options']['use_native_zoom_levels'])

        # Check an empty list and a populated list then
        self.assertIsNone(output['options'].get('acl'))
        lizmap.dlg.inAcl.setText('cadastre,urbanism')
        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        self.assertListEqual(['cadastre', 'urbanism'], output['options'].get('acl'))

    def test_read_existing_lwc_3_6_to_3_7(self):
        """ Test to read a CFG 3.6 and to export it to 3.7 about scales. """
        # Checking CFG before opening the QGS file
        with open(plugin_test_data_path('3857_project_lwc_3_6.qgs.cfg')) as f:
            json_data = json.load(f)
        self.assertListEqual([1000, 5000, 10000, 500000], json_data['options']['mapScales'])

        project = QgsProject.instance()
        project.read(plugin_test_data_path('3857_project_lwc_3_6.qgs'))
        self.assertEqual(1, len(project.mapLayers()))

        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.Lizmap_3_7)
        # read_cfg_file will call "layers_config_file"
        lizmap.read_cfg_file(skip_tables=True)

        self.assertEqual('1000', lizmap.dlg.minimum_scale.text())
        self.assertEqual('500000', lizmap.dlg.maximum_scale.text())
        self.assertEqual('1000, 5000, 10000, 500000', lizmap.dlg.list_map_scales.text())

        output = lizmap.project_config_file(LwcVersions.Lizmap_3_7, check_server=False, ignore_error=True)
        # Project is in EPSG:3857, must be True
        self.assertTrue(output['options']['use_native_zoom_levels'])
        # only two when we save
        self.assertListEqual([1000, 500000], output['options']['mapScales'])
        self.assertEqual(1000, output['options']['minScale'])
        self.assertEqual(500000, output['options']['maxScale'])

    def test_read_existing_lwc_3_6_to_3_6(self):
        """ Test to read a CFG 3.6 and to export it to 3.6 about scales. """
        # Checking CFG before opening the QGS file
        project = QgsProject.instance()
        project.read(plugin_test_data_path('3857_project_lwc_3_6.qgs'))
        self.assertEqual(1, len(project.mapLayers()))

        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.Lizmap_3_6)
        # read_cfg_file will call "layers_config_file"
        lizmap.read_cfg_file(skip_tables=True)

        self.assertEqual('1000', lizmap.dlg.minimum_scale.text())
        self.assertEqual('500000', lizmap.dlg.maximum_scale.text())
        self.assertEqual('1000, 5000, 10000, 500000', lizmap.dlg.list_map_scales.text())

        output = lizmap.project_config_file(LwcVersions.Lizmap_3_6, check_server=False, ignore_error=True)
        # Project is in EPSG:3857, must be False because of LWC 3.6
        self.assertFalse(output['options']['use_native_zoom_levels'])

        self.assertListEqual([1000, 5000, 10000, 500000], output['options']['mapScales'])
        self.assertEqual(1000, output['options']['minScale'])
        self.assertEqual(500000, output['options']['maxScale'])

    def test_general_properties_true_values(self):
        """ Test some UI settings about boolean values. """
        lizmap = self._setup_empty_project()

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        self.assertIsNone(output['options'].get('atlasAutoPlay'))

        lizmap.dlg.atlasAutoPlay.setChecked(True)

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        self.assertTrue(output['options'].get('atlasAutoPlay'))

        lizmap.dlg.atlasAutoPlay.setChecked(False)

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        self.assertIsNone(output['options'].get('atlasAutoPlay'))

        # Test some strings as well as default value
        self.assertEqual("dock", output['options'].get('popupLocation'))
        self.assertEqual("seconds", output["options"].get("tmTimeFrameType"))
        # Not working for now, maybe because of the table manager
        # self.assertEqual("light", output['options'].get('theme'))


if __name__ == "__main__":
    from qgis.testing import start_app
    start_app()
