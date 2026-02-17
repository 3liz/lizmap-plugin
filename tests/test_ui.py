"""Test Lizmap dialog UI."""

import json
import logging

from pathlib import Path

import pytest

from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import Qt
from qgis.testing.mocked import get_iface

from lizmap.definitions.definitions import LwcVersions, PredefinedGroup
from lizmap.plugin import Lizmap

from .compat import TestCase
from .utils import temporary_file_path


@pytest.fixture(autouse=True)
def teardown(data: Path) -> None:
    yield
    filepath = data.joinpath("unittest.qgs")
    if filepath.exists():
        filepath.unlink()


class TestUiLizmapDialog(TestCase):
    def test_ui(self, data: Path):
        """Test opening the Lizmap dialog with some basic checks."""
        project = QgsProject.instance()
        project.clear()
        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.latest())

        layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
        project.addMapLayer(layer)

        layer = QgsVectorLayer(str(data.joinpath("points.geojson")), "points", "ogr")
        project.addMapLayer(layer)

        flag, message = lizmap.check_global_project_options()
        self.assertFalse(flag, message)
        self.assertEqual(
            message,
            "You need to open a QGIS project, using the QGS extension.<br>This is needed before using other tabs in "
            "the plugin.",
        )

        project.write(str(data.joinpath("unittest.qgs")))
        flag, message = lizmap.check_global_project_options()
        self.assertTrue(flag, message)

        # lizmap.run()
        # lizmap.get_map_options()

    def test_legend_options(self, data: Path):
        """Test about reading legend options."""
        project = QgsProject.instance()
        project.read(str(data.joinpath("legend_image_option.qgs")))
        self.assertEqual(3, len(project.mapLayers()))

        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.latest())
        # read_cfg_file will call "layers_config_file"
        config = lizmap.read_cfg_file(skip_tables=True)
        print("\n::test_legend_options::config", config)

        lizmap.myDic = {}
        lizmap.process_node(project.layerTreeRoot(), None, config)
        lizmap.layerList = lizmap.myDic

        self.assertEqual("5000", lizmap.dlg.minimum_scale.text())
        self.assertEqual("500000", lizmap.dlg.maximum_scale.text())
        self.assertEqual("5000, 250000, 500000", lizmap.dlg.list_map_scales.text())

        self.assertEqual("disabled", lizmap.myDic.get("legend_disabled_layer_id").get("legend_image_option"))

        self.assertEqual(
            "expand_at_startup",
            lizmap.myDic.get("legend_displayed_startup_layer_id").get("legend_image_option"),
        )

        self.assertEqual(
            "hide_at_startup", lizmap.myDic.get("legend_hidden_startup_layer_id").get("legend_image_option")
        )

        # For LWC 3.6
        output = lizmap.project_config_file(
            LwcVersions.Lizmap_3_6,
            check_server=False,
            ignore_error=True,
        )

        # NOTE: Seems that HTML widget not working in tests
        # See lizmap.widgets.html_editor line 117
        logging.warning("HTML widget not working in tests")
        # self.assertTrue('<table>' in output['options']['datavizTemplate'])

        self.assertEqual(
            output["layers"]["legend_displayed_startup"]["legend_image_option"], "expand_at_startup"
        )
        self.assertIsNone(output["layers"]["legend_displayed_startup"].get("noLegendImage"))

        self.assertIsNone(output["options"].get("default_background_color_index"))

        # For LWC 3.5
        output = lizmap.project_config_file(
            LwcVersions.Lizmap_3_5, with_gui=False, check_server=False, ignore_error=True
        )
        self.assertIsNone(output["layers"]["legend_displayed_startup"].get("legend_image_option"))
        self.assertEqual(output["layers"]["legend_displayed_startup"]["noLegendImage"], str(False))

    def _setup_empty_project(
        self,
        data: Path,
        lwc_version: LwcVersions = LwcVersions.latest(),
    ) -> Lizmap:
        """Internal function to add a layer and a basic check."""
        project = QgsProject.instance()
        layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
        project.addMapLayer(layer)
        project.setFileName(temporary_file_path())

        lizmap = Lizmap(get_iface(), lwc_version=lwc_version)
        baselayers = lizmap._add_group_legend("baselayers", exclusive=True, parent=None, project=project)
        lizmap._add_group_legend(
            "project-background-color", exclusive=False, parent=baselayers, project=project
        )
        hidden = lizmap._add_group_legend("hidden", project=project)

        # For testing, we add OSM as hidden layer
        hidden_raster = QgsRasterLayer(
            "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png", "OSM", "wms"
        )
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

    def test_lizmap_layer_properties(self, data: Path):
        """Test apply some properties in a layer in the dialog."""
        lizmap = self._setup_empty_project(data)

        # Click the layer
        item = lizmap.dlg.layer_tree.topLevelItem(0)
        self.assertEqual(item.text(0), "lines")
        self.assertTrue(item.text(1).startswith("lines_"))
        self.assertEqual(item.text(2), "layer")
        self.assertEqual(item.data(0, Qt.ItemDataRole.UserRole + 1), PredefinedGroup.No.value)
        self.assertEqual(item.text(3), "")  # Not used, just to test

        self.assertFalse(lizmap.dlg.list_group_visibility.isEnabled())

        # Click the first line
        lizmap.dlg.layer_tree.setCurrentItem(lizmap.dlg.layer_tree.topLevelItem(0))

        # Fill the ACL field
        self.assertTrue(lizmap.dlg.list_group_visibility.isEnabled())
        acl_layer = "a_group_id"
        lizmap.dlg.list_group_visibility.setText(acl_layer)
        lizmap.save_value_layer_group_data("group_visibility")

        # Fill the abstract field
        html_abstract = "<strong>Hello</strong>"
        lizmap.dlg.teLayerAbstract.setPlainText(html_abstract)
        lizmap.save_value_layer_group_data("abstract")

        # Click the group base-layers
        group_item = lizmap.dlg.layer_tree.findItems(
            "baselayers", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0
        )[0]
        lizmap.dlg.layer_tree.setCurrentItem(group_item)
        self.assertFalse(lizmap.dlg.panel_layer_all_settings.isEnabled())

        # Click the group project-background-color
        group_item = lizmap.dlg.layer_tree.findItems(
            "project-background-color", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0
        )[0]
        lizmap.dlg.layer_tree.setCurrentItem(group_item)
        self.assertTrue(lizmap.dlg.panel_layer_all_settings.isEnabled())
        self.assertTrue(lizmap.dlg.group_layer_metadata.isEnabled())
        self.assertFalse(lizmap.dlg.group_layer_tree_options.isEnabled())

        # Click the group hidden
        group_item = lizmap.dlg.layer_tree.findItems(
            "hidden", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0
        )[0]
        lizmap.dlg.layer_tree.setCurrentItem(group_item)
        # It should work, maybe the test click and click in the UI is missing one thing
        # self.assertEqual(PredefinedGroup.Hidden.value, lizmap._current_item_predefined_group())
        # self.assertFalse(lizmap.dlg.panel_layer_all_settings.isEnabled())

        # Back to a layer outside of these groups
        group_item = lizmap.dlg.layer_tree.findItems(
            "lines", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0
        )[0]
        lizmap.dlg.layer_tree.setCurrentItem(group_item)
        self.assertTrue(lizmap.dlg.list_group_visibility.isEnabled())

        # Check new values in the output config
        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        # Layers
        self.assertListEqual(output["layers"]["lines"]["group_visibility"], [acl_layer])
        self.assertEqual(output["layers"]["lines"]["abstract"], html_abstract)
        # Predefined groups, still in the CFG
        self.assertListEqual(output["layers"]["baselayers"]["group_visibility"], [])
        self.assertEqual(output["layers"]["baselayers"]["abstract"], "")
        self.assertListEqual(output["layers"]["project-background-color"]["group_visibility"], [])
        self.assertEqual(output["layers"]["project-background-color"]["abstract"], "")
        self.assertEqual(output["options"].get("default_background_color_index"), 0)

        self.assertFalse(output["layers"]["lines"].get("children_lizmap_features_table"))
        self.assertEqual("False", output["layers"]["lines"].get("popupDisplayChildren"))

        # Test a false value as a string which shouldn't be there by default
        self.assertIsNone(output["layers"]["lines"].get("externalWmsToggle"))
        self.assertIsNone(output["layers"]["lines"].get("metatileSize"))

    def test_default_options_values_3_6(self, data: Path):
        """Test default options values."""
        lizmap = self._setup_empty_project(data)

        output = lizmap.project_config_file(LwcVersions.Lizmap_3_6, check_server=False, ignore_error=True)

        # generic options
        self.assertIsNone(output["options"].get("hideProject"))
        self.assertFalse(output["options"].get("automatic_permalink"))
        self.assertFalse(output["options"].get("wms_single_request_for_all_layers"))
        self.assertIsNone(output["options"].get("acl"))

        # map tools
        self.assertFalse(output["options"].get("measure"))
        self.assertFalse(output["options"].get("print"))  # The checkbox is removed since LWC 3.7.0
        self.assertFalse(output["options"].get("zoomHistory"))  # The checkbox is removed since LWC 3.8.0
        self.assertFalse(output["options"].get("geolocation"))
        self.assertFalse(output["options"].get("draw"))
        self.assertIsNone(output["options"].get("externalSearch"))
        self.assertEqual(25, output["options"].get("pointTolerance"))
        self.assertEqual(10, output["options"].get("lineTolerance"))
        self.assertEqual(5, output["options"].get("polygonTolerance"))

        # API keys
        self.assertIsNone(output["options"].get("googleKey"))
        self.assertIsNone(output["options"].get("bingKey"))
        self.assertIsNone(output["options"].get("ignKey"))

        # Scales
        self.assertFalse(output["options"].get("use_native_zoom_levels"))
        self.assertFalse(output["options"].get("hide_numeric_scale_value"))
        self.assertEqual([10000, 25000, 50000, 100000, 250000, 500000], output["options"].get("mapScales"))
        self.assertEqual(1, output["options"].get("minScale"))
        self.assertEqual(1000000000, output["options"].get("maxScale"))
        self.assertIsNone(output["options"].get("max_scale_points"))
        self.assertIsNone(output["options"].get("max_scale_lines_polygons"))

        # Map interface
        self.assertFalse(output["options"].get("hideHeader"))
        self.assertFalse(output["options"].get("hideMenu"))
        self.assertFalse(output["options"].get("hideLegend"))
        self.assertFalse(output["options"].get("hideOverview"))
        self.assertFalse(output["options"].get("hideNavbar"))
        self.assertEqual("dock", output["options"].get("popupLocation"))
        self.assertTrue(output["options"].get("fixed_scale_overview_map"))

        # Layers page
        self.assertIsNone(output["options"].get("hideGroupCheckbox"))
        self.assertIsNone(output["options"].get("activateFirstMapTheme"))

        # Baselayers page
        self.assertIsNone(output["options"].get("emptyBaselayer"))
        self.assertIsNone(output["options"].get("startupBaselayer"))

        # Attribute page
        self.assertIsNone(output["options"].get("limitDataToBbox"))

        # Layouts page
        self.assertFalse(output["options"].get("default_popup_print"))

        # Dataviz page
        self.assertIsNone(output["options"].get("datavizTemplate"))
        self.assertIsNone(output["options"].get("dataviz_drag_drop"))
        self.assertEqual("dock", output["options"].get("datavizLocation"))
        self.assertIsNone(output["options"].get("theme"))  # default value "dark" is not set

        # Time manager page
        self.assertEqual(10, output["options"].get("tmTimeFrameSize"))
        self.assertEqual("seconds", output["options"].get("tmTimeFrameType"))
        self.assertEqual(1000, output["options"].get("tmAnimationFrameLength"))

        # Atlas page
        self.assertIsNone(output["options"].get("atlasShowAtStartup"))
        self.assertIsNone(output["options"].get("atlasAutoPlay"))

    def test_default_options_values_3_7(self, data: Path):
        """Test default options values."""
        lizmap = self._setup_empty_project(data)

        output = lizmap.project_config_file(LwcVersions.Lizmap_3_7, check_server=False, ignore_error=True)

        # generic options
        self.assertIsNone(output["options"].get("hideProject"))
        self.assertFalse(output["options"].get("automatic_permalink"))
        self.assertFalse(output["options"].get("wms_single_request_for_all_layers"))
        self.assertIsNone(output["options"].get("acl"))

        # map tools
        self.assertFalse(output["options"].get("measure"))
        self.assertIsNone(output["options"].get("print"))  # The checkbox is removed since LWC 3.7.0
        self.assertFalse(output["options"].get("zoomHistory"))  # The checkbox is removed since LWC 3.8.0
        self.assertFalse(output["options"].get("geolocation"))
        self.assertFalse(output["options"].get("draw"))
        self.assertIsNone(output["options"].get("externalSearch"))
        self.assertEqual(25, output["options"].get("pointTolerance"))
        self.assertEqual(10, output["options"].get("lineTolerance"))
        self.assertEqual(5, output["options"].get("polygonTolerance"))

        # API keys
        self.assertIsNone(output["options"].get("googleKey"))
        self.assertIsNone(output["options"].get("bingKey"))
        self.assertIsNone(output["options"].get("ignKey"))

        # Scales
        self.assertFalse(output["options"].get("use_native_zoom_levels"))
        self.assertFalse(output["options"].get("hide_numeric_scale_value"))
        self.assertEqual([10000, 25000, 50000, 100000, 250000, 500000], output["options"].get("mapScales"))
        self.assertEqual(1, output["options"].get("minScale"))
        self.assertEqual(1000000000, output["options"].get("maxScale"))
        self.assertIsNone(output["options"].get("max_scale_points"))
        self.assertIsNone(output["options"].get("max_scale_lines_polygons"))

        # Map interface
        self.assertFalse(output["options"].get("hideHeader"))
        self.assertFalse(output["options"].get("hideMenu"))
        self.assertFalse(output["options"].get("hideLegend"))
        self.assertFalse(output["options"].get("hideOverview"))
        self.assertFalse(output["options"].get("hideNavbar"))
        self.assertEqual("dock", output["options"].get("popupLocation"))
        self.assertTrue(output["options"].get("fixed_scale_overview_map"))

        # Layers page
        self.assertIsNone(output["options"].get("hideGroupCheckbox"))
        self.assertIsNone(output["options"].get("activateFirstMapTheme"))

        # Baselayers page
        self.assertIsNone(output["options"].get("emptyBaselayer"))
        self.assertIsNone(output["options"].get("startupBaselayer"))

        # Attribute page
        self.assertIsNone(output["options"].get("limitDataToBbox"))

        # Layouts page
        self.assertFalse(output["options"].get("default_popup_print"))

        # Dataviz page
        self.assertIsNone(output["options"].get("datavizTemplate"))
        self.assertIsNone(output["options"].get("dataviz_drag_drop"))
        self.assertEqual("dock", output["options"].get("datavizLocation"))
        self.assertIsNone(output["options"].get("theme"))  # default value "dark" is not set

        # Time manager page
        self.assertEqual(10, output["options"].get("tmTimeFrameSize"))
        self.assertEqual("seconds", output["options"].get("tmTimeFrameType"))
        self.assertEqual(1000, output["options"].get("tmAnimationFrameLength"))

        # Atlas page
        self.assertIsNone(output["options"].get("atlasShowAtStartup"))
        self.assertIsNone(output["options"].get("atlasAutoPlay"))

    def test_default_options_values_3_8(self, data: Path):
        """Test default options values."""
        lizmap = self._setup_empty_project(data)

        output = lizmap.project_config_file(LwcVersions.Lizmap_3_8, check_server=False, ignore_error=True)

        # generic options
        self.assertIsNone(output["options"].get("hideProject"))
        self.assertFalse(output["options"].get("automatic_permalink"))
        self.assertFalse(output["options"].get("wms_single_request_for_all_layers"))
        self.assertIsNone(output["options"].get("acl"))

        # map tools
        self.assertFalse(output["options"].get("measure"))
        self.assertIsNone(output["options"].get("print"))  # The checkbox is removed since LWC 3.7.0
        self.assertIsNone(output["options"].get("zoomHistory"))  # The checkbox is removed since LWC 3.8.0
        self.assertFalse(output["options"].get("geolocation"))
        self.assertFalse(output["options"].get("draw"))
        self.assertIsNone(output["options"].get("externalSearch"))
        self.assertEqual(25, output["options"].get("pointTolerance"))
        self.assertEqual(10, output["options"].get("lineTolerance"))
        self.assertEqual(5, output["options"].get("polygonTolerance"))

        # API keys
        self.assertIsNone(output["options"].get("googleKey"))
        self.assertIsNone(output["options"].get("bingKey"))
        self.assertIsNone(output["options"].get("ignKey"))

        # Scales
        self.assertFalse(output["options"].get("use_native_zoom_levels"))
        self.assertFalse(output["options"].get("hide_numeric_scale_value"))
        self.assertEqual([10000, 25000, 50000, 100000, 250000, 500000], output["options"].get("mapScales"))
        self.assertEqual(1, output["options"].get("minScale"))
        self.assertEqual(1000000000, output["options"].get("maxScale"))
        self.assertIsNone(output["options"].get("max_scale_points"))
        self.assertIsNone(output["options"].get("max_scale_lines_polygons"))

        # Map interface
        self.assertFalse(output["options"].get("hideHeader"))
        self.assertFalse(output["options"].get("hideMenu"))
        self.assertFalse(output["options"].get("hideLegend"))
        self.assertFalse(output["options"].get("hideOverview"))
        self.assertFalse(output["options"].get("hideNavbar"))
        self.assertEqual("dock", output["options"].get("popupLocation"))
        self.assertTrue(output["options"].get("fixed_scale_overview_map"))

        # Layers page
        self.assertIsNone(output["options"].get("hideGroupCheckbox"))
        self.assertIsNone(output["options"].get("activateFirstMapTheme"))

        # Baselayers page
        self.assertIsNone(output["options"].get("emptyBaselayer"))
        self.assertIsNone(output["options"].get("startupBaselayer"))

        # Attribute page
        self.assertIsNone(output["options"].get("limitDataToBbox"))

        # Layouts page
        self.assertFalse(output["options"].get("default_popup_print"))

        # Dataviz page
        self.assertIsNone(output["options"].get("datavizTemplate"))
        self.assertIsNone(output["options"].get("dataviz_drag_drop"))
        self.assertEqual("dock", output["options"].get("datavizLocation"))
        self.assertIsNone(output["options"].get("theme"))  # default value "dark" is not set

        # Time manager page
        self.assertEqual(10, output["options"].get("tmTimeFrameSize"))
        self.assertEqual("seconds", output["options"].get("tmTimeFrameType"))
        self.assertEqual(1000, output["options"].get("tmAnimationFrameLength"))

        # Atlas page
        self.assertIsNone(output["options"].get("atlasShowAtStartup"))
        self.assertIsNone(output["options"].get("atlasAutoPlay"))

    def test_default_options_values_3_9(self, data: Path):
        """Test default options values."""
        lizmap = self._setup_empty_project(data)

        output = lizmap.project_config_file(LwcVersions.Lizmap_3_9, check_server=False, ignore_error=True)

        # generic options
        self.assertIsNone(output["options"].get("hideProject"))
        self.assertFalse(output["options"].get("automatic_permalink"))
        self.assertFalse(output["options"].get("wms_single_request_for_all_layers"))
        self.assertIsNone(output["options"].get("acl"))

        # map tools
        self.assertFalse(output["options"].get("measure"))
        self.assertIsNone(output["options"].get("print"))  # The checkbox is removed since LWC 3.7.0
        self.assertIsNone(output["options"].get("zoomHistory"))  # The checkbox is removed since LWC 3.8.0
        self.assertFalse(output["options"].get("geolocation"))
        # self.assertIsNone(output["options"].get("geolocationPrecision")) # Added since LWC 3.10.0
        # self.assertIsNone(output["options"].get("geolocationDirection")) # Added since LWC 3.10.0
        self.assertFalse(output["options"].get("draw"))
        self.assertIsNone(output["options"].get("externalSearch"))
        self.assertEqual(25, output["options"].get("pointTolerance"))
        self.assertEqual(10, output["options"].get("lineTolerance"))
        self.assertEqual(5, output["options"].get("polygonTolerance"))

        # API keys
        self.assertIsNone(output["options"].get("googleKey"))
        self.assertIsNone(output["options"].get("bingKey"))
        self.assertIsNone(output["options"].get("ignKey"))

        # Scales
        self.assertFalse(output["options"].get("use_native_zoom_levels"))
        self.assertFalse(output["options"].get("hide_numeric_scale_value"))
        self.assertEqual([10000, 25000, 50000, 100000, 250000, 500000], output["options"].get("mapScales"))
        self.assertEqual(1, output["options"].get("minScale"))
        self.assertEqual(1000000000, output["options"].get("maxScale"))
        self.assertIsNone(output["options"].get("max_scale_points"))
        self.assertIsNone(output["options"].get("max_scale_lines_polygons"))

        # Map interface
        self.assertFalse(output["options"].get("hideHeader"))
        self.assertFalse(output["options"].get("hideMenu"))
        self.assertFalse(output["options"].get("hideLegend"))
        self.assertFalse(output["options"].get("hideOverview"))
        self.assertFalse(output["options"].get("hideNavbar"))
        self.assertEqual("dock", output["options"].get("popupLocation"))
        self.assertTrue(output["options"].get("fixed_scale_overview_map"))

        # Layers page
        self.assertIsNone(output["options"].get("hideGroupCheckbox"))
        self.assertIsNone(output["options"].get("activateFirstMapTheme"))

        # Baselayers page
        self.assertIsNone(output["options"].get("emptyBaselayer"))
        self.assertIsNone(output["options"].get("startupBaselayer"))

        # Attribute page
        self.assertIsNone(output["options"].get("limitDataToBbox"))

        # Layouts page
        self.assertFalse(output["options"].get("default_popup_print"))

        # Dataviz page
        self.assertIsNone(output["options"].get("datavizTemplate"))
        self.assertIsNone(output["options"].get("dataviz_drag_drop"))
        self.assertEqual("dock", output["options"].get("datavizLocation"))
        self.assertIsNone(output["options"].get("theme"))  # default value "dark" is not set

        # Time manager page
        self.assertEqual(10, output["options"].get("tmTimeFrameSize"))
        self.assertEqual("seconds", output["options"].get("tmTimeFrameType"))
        self.assertEqual(1000, output["options"].get("tmAnimationFrameLength"))

        # Atlas page
        self.assertIsNone(output["options"].get("atlasShowAtStartup"))
        self.assertIsNone(output["options"].get("atlasAutoPlay"))

    def test_default_options_latest(self, data: Path):
        """Test default options values."""
        lizmap = self._setup_empty_project(data)

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)

        # generic options
        self.assertIsNone(output["options"].get("hideProject"))
        self.assertFalse(output["options"].get("automatic_permalink"))
        self.assertFalse(output["options"].get("wms_single_request_for_all_layers"))
        self.assertIsNone(output["options"].get("acl"))

        # map tools
        self.assertFalse(output["options"].get("measure"))
        self.assertIsNone(output["options"].get("print"))  # The checkbox is removed since LWC 3.7.0
        self.assertIsNone(output["options"].get("zoomHistory"))  # The checkbox is removed since LWC 3.8.0
        self.assertFalse(output["options"].get("geolocation"))
        self.assertTrue(output["options"].get("geolocationPrecision"))  # Added since LWC 3.10.0
        self.assertFalse(output["options"].get("geolocationDirection"))  # Added since LWC 3.10.0
        self.assertFalse(output["options"].get("draw"))
        self.assertIsNone(output["options"].get("externalSearch"))
        self.assertEqual(25, output["options"].get("pointTolerance"))
        self.assertEqual(10, output["options"].get("lineTolerance"))
        self.assertEqual(5, output["options"].get("polygonTolerance"))

        # API keys
        self.assertIsNone(output["options"].get("googleKey"))
        self.assertIsNone(output["options"].get("bingKey"))
        self.assertIsNone(output["options"].get("ignKey"))

        # Scales
        self.assertFalse(output["options"].get("use_native_zoom_levels"))
        self.assertFalse(output["options"].get("hide_numeric_scale_value"))
        self.assertEqual([10000, 25000, 50000, 100000, 250000, 500000], output["options"].get("mapScales"))
        self.assertEqual(1, output["options"].get("minScale"))
        self.assertEqual(1000000000, output["options"].get("maxScale"))
        self.assertIsNone(output["options"].get("max_scale_points"))
        self.assertIsNone(output["options"].get("max_scale_lines_polygons"))

        # Map interface
        self.assertFalse(output["options"].get("hideHeader"))
        self.assertFalse(output["options"].get("hideMenu"))
        self.assertFalse(output["options"].get("hideLegend"))
        self.assertFalse(output["options"].get("hideOverview"))
        self.assertFalse(output["options"].get("hideNavbar"))
        self.assertEqual("dock", output["options"].get("popupLocation"))
        self.assertTrue(output["options"].get("fixed_scale_overview_map"))

        # Layers page
        self.assertIsNone(output["options"].get("hideGroupCheckbox"))
        self.assertIsNone(output["options"].get("activateFirstMapTheme"))

        # Baselayers page
        self.assertIsNone(output["options"].get("emptyBaselayer"))
        self.assertIsNone(output["options"].get("startupBaselayer"))

        # Attribute page
        self.assertIsNone(output["options"].get("limitDataToBbox"))

        # Layouts page
        self.assertFalse(output["options"].get("default_popup_print"))

        # Dataviz page
        self.assertIsNone(output["options"].get("datavizTemplate"))
        self.assertIsNone(output["options"].get("dataviz_drag_drop"))
        self.assertEqual("dock", output["options"].get("datavizLocation"))
        self.assertIsNone(output["options"].get("theme"))  # default value "dark" is not set

        # Time manager page
        self.assertEqual(10, output["options"].get("tmTimeFrameSize"))
        self.assertEqual("seconds", output["options"].get("tmTimeFrameType"))
        self.assertEqual(1000, output["options"].get("tmAnimationFrameLength"))

        # Atlas page
        self.assertIsNone(output["options"].get("atlasShowAtStartup"))
        self.assertIsNone(output["options"].get("atlasAutoPlay"))

    def test_max_scale_lwc_3_7(self, data: Path):
        """Test about maximum scale when zooming."""
        lizmap = self._setup_empty_project(data, LwcVersions.Lizmap_3_6)

        self.assertEqual(5000.0, lizmap.dlg.max_scale_points.scale())
        self.assertEqual(5000.0, lizmap.dlg.max_scale_lines_polygons.scale())

        # Max scale when zoomin
        # Only points with a different value
        lizmap.dlg.max_scale_points.setScale(1000.0)

        # Check new values in the output config
        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        # Check scales in the CFG
        self.assertEqual(1000.0, output["options"]["max_scale_points"])
        self.assertIsNone(output["options"].get("max_scale_lines_polygons"))

    def test_general_scales_properties_lwc_3_6(self, data: Path):
        """Test some UI settings about general properties with LWC 3.6."""
        lizmap = self._setup_empty_project(data, LwcVersions.Lizmap_3_6)

        # Check default values
        self.assertEqual("10000, 25000, 50000, 100000, 250000, 500000", lizmap.dlg.list_map_scales.text())

        # Default values from config.py at the beginning only
        self.assertEqual("1", lizmap.dlg.minimum_scale.text())
        self.assertEqual("1000000000", lizmap.dlg.maximum_scale.text())

        # Trigger the signal
        lizmap.get_min_max_scales()

        # Values from the UI
        self.assertEqual("10000", lizmap.dlg.minimum_scale.text())
        self.assertEqual("500000", lizmap.dlg.maximum_scale.text())

        scales = "1000, 5000, 15000"

        # Fill scales
        lizmap.dlg.list_map_scales.setText(scales)
        lizmap.get_min_max_scales()
        self.assertEqual("1000", lizmap.dlg.minimum_scale.text())
        self.assertEqual("15000", lizmap.dlg.maximum_scale.text())
        self.assertEqual(scales, lizmap.dlg.list_map_scales.text())

        # Check new values in the output config
        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)

        # Check scales in the CFG
        self.assertEqual(1000, output["options"]["minScale"])
        self.assertEqual(15000, output["options"]["maxScale"])
        self.assertListEqual([1000, 5000, 15000], output["options"]["mapScales"])

        # Project is in EPSG:2154, must be False
        self.assertFalse(output["options"]["use_native_zoom_levels"])

        # Check an empty list and a populated list then
        self.assertIsNone(output["options"].get("acl"))
        lizmap.dlg.inAcl.setText("cadastre,urbanism")

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )
        self.assertListEqual(["cadastre", "urbanism"], output["options"].get("acl"))

    def test_read_existing_lwc_3_6_to_3_7(self, data: Path):
        """Test to read a CFG 3.6 and to export it to 3.7 about scales."""
        # Checking CFG before opening the QGS file
        with data.joinpath("3857_project_lwc_3_6.qgs.cfg").open() as f:
            json_data = json.load(f)
        self.assertListEqual([1000, 5000, 10000, 500000], json_data["options"]["mapScales"])

        project = QgsProject.instance()
        project.read(str(data.joinpath("3857_project_lwc_3_6.qgs")))
        self.assertEqual(1, len(project.mapLayers()))

        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.Lizmap_3_7)
        # read_cfg_file will call "layers_config_file"
        lizmap.read_cfg_file(skip_tables=True)

        self.assertEqual("1000", lizmap.dlg.minimum_scale.text())
        self.assertEqual("500000", lizmap.dlg.maximum_scale.text())
        self.assertEqual("1000, 5000, 10000, 500000", lizmap.dlg.list_map_scales.text())

        output = lizmap.project_config_file(
            LwcVersions.Lizmap_3_7,
            check_server=False,
            ignore_error=True,
        )

        # Project is in EPSG:3857, must be True
        self.assertTrue(output["options"]["use_native_zoom_levels"])
        # only two when we save
        self.assertListEqual([1000, 500000], output["options"]["mapScales"])
        self.assertEqual(1000, output["options"]["minScale"])
        self.assertEqual(500000, output["options"]["maxScale"])

    def test_read_existing_lwc_3_6_to_3_6(self, data: Path):
        """Test to read a CFG 3.6 and to export it to 3.6 about scales."""
        # Checking CFG before opening the QGS file
        project = QgsProject.instance()
        project.read(str(data.joinpath("3857_project_lwc_3_6.qgs")))
        self.assertEqual(1, len(project.mapLayers()))

        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.Lizmap_3_6)
        # read_cfg_file will call "layers_config_file"
        lizmap.read_cfg_file(skip_tables=True)

        self.assertEqual("1000", lizmap.dlg.minimum_scale.text())
        self.assertEqual("500000", lizmap.dlg.maximum_scale.text())
        self.assertEqual("1000, 5000, 10000, 500000", lizmap.dlg.list_map_scales.text())

        output = lizmap.project_config_file(
            LwcVersions.Lizmap_3_6,
            check_server=False,
            ignore_error=True,
        )

        # Project is in EPSG:3857, must be False because of LWC 3.6
        self.assertFalse(output["options"]["use_native_zoom_levels"])

        self.assertListEqual([1000, 5000, 10000, 500000], output["options"]["mapScales"])
        self.assertEqual(1000, output["options"]["minScale"])
        self.assertEqual(500000, output["options"]["maxScale"])

    def test_atlas_auto_play_true_values(self, data: Path):
        """Test some UI settings about boolean values."""
        lizmap = self._setup_empty_project(data)

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        self.assertIsNone(output["options"].get("atlasAutoPlay"))

        lizmap.dlg.atlasAutoPlay.setChecked(True)

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        self.assertTrue(output["options"].get("atlasAutoPlay"))

        lizmap.dlg.atlasAutoPlay.setChecked(False)

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertIsNone(output["options"].get("atlasAutoPlay"))

    def test_geolocation_values(self, data: Path):
        """Test geolocation UI settings."""
        lizmap = self._setup_empty_project(data)

        # Default geolocation checkboxes checked
        self.assertFalse(lizmap.dlg.groupbox_geolocation.isChecked())
        self.assertTrue(lizmap.dlg.checkbox_geolocation_precision.isChecked())
        self.assertFalse(lizmap.dlg.checkbox_geolocation_direction.isChecked())

        # Default geolocation checkboxes enabled
        self.assertTrue(lizmap.dlg.groupbox_geolocation.isEnabled())
        self.assertFalse(lizmap.dlg.checkbox_geolocation_precision.isEnabled())
        self.assertFalse(lizmap.dlg.checkbox_geolocation_direction.isEnabled())

        # Check geolocation checkbox to enable other checkboxes
        lizmap.dlg.groupbox_geolocation.setChecked(True)
        self.assertTrue(lizmap.dlg.checkbox_geolocation_precision.isEnabled())
        self.assertTrue(lizmap.dlg.checkbox_geolocation_direction.isEnabled())

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        # options
        self.assertTrue(output["options"].get("geolocation"))
        self.assertTrue(output["options"].get("geolocationPrecision"))
        self.assertFalse(output["options"].get("geolocationDirection"))

        # Check direction
        lizmap.dlg.checkbox_geolocation_direction.setChecked(True)
        # Uncheck precision
        lizmap.dlg.checkbox_geolocation_precision.setChecked(False)

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        # options
        self.assertTrue(output["options"].get("geolocation"))
        self.assertFalse(output["options"].get("geolocationPrecision"))
        self.assertTrue(output["options"].get("geolocationDirection"))

    def test_exclude_basemaps_from_single_wms_values(self, data: Path):
        """Test exclude basemaps from single WMS UI settings."""
        lizmap = self._setup_empty_project(data)

        # Default checkbox states
        self.assertFalse(lizmap.dlg.checkbox_wms_single_request_all_layers.isChecked())
        self.assertFalse(lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.isChecked())

        # Exclude basemaps checkbox should be disabled when single WMS is off
        self.assertFalse(lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.isEnabled())

        # Enable single WMS - exclude basemaps checkbox should become enabled
        lizmap.dlg.checkbox_wms_single_request_all_layers.setChecked(True)
        self.assertTrue(lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.isEnabled())

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        # Single WMS enabled, exclude basemaps still unchecked
        self.assertTrue(output["options"].get("wms_single_request_for_all_layers"))
        self.assertFalse(output["options"].get("exclude_basemaps_from_single_wms"))

        # Enable exclude basemaps
        lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.setChecked(True)

        output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
        # Both options enabled
        self.assertTrue(output["options"].get("wms_single_request_for_all_layers"))
        self.assertTrue(output["options"].get("exclude_basemaps_from_single_wms"))

        # Disable single WMS - exclude basemaps checkbox should become disabled
        lizmap.dlg.checkbox_wms_single_request_all_layers.setChecked(False)
        self.assertFalse(lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.isEnabled())
