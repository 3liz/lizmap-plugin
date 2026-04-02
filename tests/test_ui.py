"""Test Lizmap dialog UI."""

import json

from pathlib import Path

import pytest

from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import Qt

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


def test_ui_base(data: Path, qgis_iface: QgisInterface):
    """Test opening the Lizmap dialog with some basic checks."""
    project = QgsProject.instance()
    project.clear()
    lizmap = Lizmap(qgis_iface, lwc_version=LwcVersions.latest())

    layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
    project.addMapLayer(layer)

    layer = QgsVectorLayer(str(data.joinpath("points.geojson")), "points", "ogr")
    project.addMapLayer(layer)

    flag, message = lizmap.check_global_project_options()
    assert not flag, message
    assert  message, (
        "You need to open a QGIS project, using the QGS extension.<br>This is "
        "needed before using other tabs in ""the plugin."
    )

    project.write(str(data.joinpath("unittest.qgs")))
    flag, message = lizmap.check_global_project_options()
    assert flag, message

    # lizmap.run()
    # lizmap.get_map_options()

def test_legend_options(data: Path, qgis_iface: QgisInterface):
    """Test about reading legend options."""
    project = QgsProject.instance()
    project.read(str(data.joinpath("legend_image_option.qgs")))
    assert len(project.mapLayers()) == 3

    lizmap = Lizmap(qgis_iface, lwc_version=LwcVersions.latest())
    # read_cfg_file will call "layers_config_file"
    config = lizmap.read_cfg_file(skip_tables=True)
    print("\n::test_legend_options::config", config)

    lizmap.process_node(lizmap.layerList, project.layerTreeRoot(), None, config)

    assert lizmap.dlg.minimum_scale.text() == "5000"
    assert lizmap.dlg.maximum_scale.text() == "500000"
    assert lizmap.dlg.list_map_scales.text() == "5000, 250000, 500000"

    assert lizmap.layerList.get("legend_disabled_layer_id").get("legend_image_option") == "disabled"
    assert lizmap.layerList["legend_displayed_startup_layer_id"]["legend_image_option"] == "expand_at_startup"
    assert lizmap.layerList["legend_hidden_startup_layer_id"]["legend_image_option"] == "hide_at_startup"

    # For LWC 3.6
    output = lizmap.project_config_file(
        LwcVersions.Lizmap_3_6,
        check_server=False,
        ignore_error=True,
    )

    # NOTE: Seems that HTML widget not working in tests
    # See lizmap.widgets.html_editor line 117
    # assert '<table>' in output['options']['datavizTemplate']

    assert output["layers"]["legend_displayed_startup"]["legend_image_option"] == "expand_at_startup"
    assert output["layers"]["legend_displayed_startup"].get("noLegendImage") is None
    assert output["options"].get("default_background_color_index") is None

    # For LWC 3.5
    output = lizmap.project_config_file(
        LwcVersions.Lizmap_3_5, with_gui=False, check_server=False, ignore_error=True
    )
    assert output["layers"]["legend_displayed_startup"].get("legend_image_option") is None
    assert str(False) == output["layers"]["legend_displayed_startup"]["noLegendImage"]

def _setup_empty_project(
    data: Path,
    qgis_iface: QgisInterface,
    lwc_version: LwcVersions = LwcVersions.latest(),
) -> Lizmap:
    """Internal function to add a layer and a basic check."""
    project = QgsProject.instance()
    layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
    project.addMapLayer(layer)
    project.setFileName(temporary_file_path())

    lizmap = Lizmap(qgis_iface, lwc_version=lwc_version)
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
    TestCase.assertDictEqual({}, config)

    # Some process
    lizmap.process_node(lizmap.layerList, project.layerTreeRoot(), None, {})

    return lizmap

def test_lizmap_layer_properties(data: Path, qgis_iface: QgisInterface):
    """Test apply some properties in a layer in the dialog."""
    lizmap = _setup_empty_project(data, qgis_iface)

    # Click the layer
    item = lizmap.dlg.layer_tree.topLevelItem(0)
    assert item.text(0) == "lines"
    assert item.text(1).startswith("lines_")
    assert item.text(2) == "layer"
    assert item.data(0, Qt.ItemDataRole.UserRole + 1) == PredefinedGroup.No.value
    assert item.text(3) == ""  # Not used, just to test

    assert not lizmap.dlg.list_group_visibility.isEnabled(), "Visibility should be disabled"

    # Click the first line
    lizmap.dlg.layer_tree.setCurrentItem(lizmap.dlg.layer_tree.topLevelItem(0))

    # Fill the ACL field
    assert lizmap.dlg.list_group_visibility.isEnabled(), "Visibility should be enabled"
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
    assert not lizmap.dlg.panel_layer_all_settings.isEnabled()

    # Click the group project-background-color
    group_item = lizmap.dlg.layer_tree.findItems(
        "project-background-color", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0
    )[0]
    lizmap.dlg.layer_tree.setCurrentItem(group_item)
    assert lizmap.dlg.panel_layer_all_settings.isEnabled()
    assert lizmap.dlg.group_layer_metadata.isEnabled()
    # XXX QGIS4 KO
    assert not lizmap.dlg.group_layer_tree_options.isEnabled(), "Layer tree option should be disabled"

    # Click the group hidden
    group_item = lizmap.dlg.layer_tree.findItems(
        "hidden", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0
    )[0]
    lizmap.dlg.layer_tree.setCurrentItem(group_item)
    # It should work, maybe the test click and click in the UI is missing one thing
    # assert lizmap._current_item_predefined_group() == PredefinedGroup.Hidden.value
    # assert not lizmap.dlg.panel_layer_all_settings.isEnabled()

    # Back to a layer outside of these groups
    group_item = lizmap.dlg.layer_tree.findItems(
        "lines", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0
    )[0]
    lizmap.dlg.layer_tree.setCurrentItem(group_item)
    assert lizmap.dlg.list_group_visibility.isEnabled()

    # Check new values in the output config
    output = lizmap.project_config_file(
        LwcVersions.latest(),
        check_server=False,
        ignore_error=True,
    )

    # Layers
    assert output["layers"]["lines"]["group_visibility"] == [acl_layer]
    assert output["layers"]["lines"]["abstract"] == html_abstract
    # Predefined groups, still in the CFG
    assert output["layers"]["baselayers"]["group_visibility"] == []
    assert output["layers"]["baselayers"]["abstract"] == ""
    assert output["layers"]["project-background-color"]["group_visibility"] == []
    assert output["layers"]["project-background-color"]["abstract"] == ""
    # XXX QGIS4 KO
    assert output["options"]["default_background_color_index"] == 0

    assert not output["layers"]["lines"].get("children_lizmap_features_table")
    assert output["layers"]["lines"].get("popupDisplayChildren") == "False"

    # Test a false value as a string which shouldn't be there by default
    assert output["layers"]["lines"].get("externalWmsToggle") is None
    assert output["layers"]["lines"].get("metatileSize") is None

def test_default_options_values_3_6(data: Path, qgis_iface: QgisInterface):
    """Test default options values."""
    lizmap = _setup_empty_project(data, qgis_iface)

    output = lizmap.project_config_file(LwcVersions.Lizmap_3_6, check_server=False, ignore_error=True)

    # generic options
    assert output["options"].get("hideProject") is None
    assert not output["options"].get("automatic_permalink")
    assert not output["options"].get("wms_single_request_for_all_layers")
    assert output["options"].get("acl") is None

    # map tools
    assert not output["options"].get("measure")
    assert not output["options"].get("print")  # The checkbox is removed since LWC 3.7.0
    assert not output["options"].get("zoomHistory")  # The checkbox is removed since LWC 3.8.0
    assert not output["options"].get("geolocation")
    assert not output["options"].get("draw")
    assert output["options"].get("externalSearch") is None
    assert output["options"]["pointTolerance"] == 25
    assert output["options"]["lineTolerance"] == 10
    assert output["options"]["polygonTolerance"] == 5

    # API keys
    assert output["options"].get("googleKey") is None
    assert output["options"].get("bingKey") is None
    assert output["options"].get("ignKey") is None

    # Scales
    assert not output["options"].get("use_native_zoom_levels")
    assert not output["options"].get("hide_numeric_scale_value")
    assert output["options"]["mapScales"] == [10000, 25000, 50000, 100000, 250000, 500000]
    assert output["options"]["minScale"] == 1
    assert output["options"]["maxScale"] == 1000000000
    assert output["options"].get("max_scale_points") is None
    assert output["options"].get("max_scale_lines_polygons") is None

    # Map interface
    assert not output["options"].get("hideHeader")
    assert not output["options"].get("hideMenu")
    assert not output["options"].get("hideLegend")
    assert not output["options"].get("hideOverview")
    assert not output["options"].get("hideNavbar")
    assert output["options"]["popupLocation"] == "dock"
    assert output["options"]["fixed_scale_overview_map"]

    # Layers page
    assert output["options"].get("hideGroupCheckbox") is None
    assert output["options"].get("activateFirstMapTheme") is None

    # Baselayers page
    assert output["options"].get("emptyBaselayer") is None
    assert output["options"].get("startupBaselayer") is None

    # Attribute page
    assert output["options"].get("limitDataToBbox") is None

    # Layouts page
    assert not output["options"].get("default_popup_print")

    # Dataviz page
    assert output["options"].get("datavizTemplate") is None
    assert output["options"].get("dataviz_drag_drop") is None
    assert output["options"]["datavizLocation"] == "dock"
    assert output["options"].get("theme") is None # default value "dark" is not set

    # Time manager page
    assert output["options"]["tmTimeFrameSize"] == 10
    assert output["options"]["tmTimeFrameType"] == "seconds"
    assert output["options"]["tmAnimationFrameLength"] == 1000

    # Atlas page
    assert output["options"].get("atlasShowAtStartup") is None
    assert output["options"].get("atlasAutoPlay") is None

def test_default_options_values_3_7(data: Path, qgis_iface: QgisInterface):
    """Test default options values."""
    lizmap = _setup_empty_project(data, qgis_iface)

    output = lizmap.project_config_file(LwcVersions.Lizmap_3_7, check_server=False, ignore_error=True)

    # generic options
    output["options"].get("hideProject") is None
    assert not output["options"].get("automatic_permalink")
    assert not output["options"].get("wms_single_request_for_all_layers")
    assert output["options"].get("acl") is None

    # map tools
    assert not output["options"].get("measure")
    assert output["options"].get("print") is None  # The checkbox is removed since LWC 3.7.0
    assert not output["options"].get("zoomHistory")  # The checkbox is removed since LWC 3.8.0
    assert not output["options"].get("geolocation")
    assert not output["options"].get("draw")
    assert output["options"].get("externalSearch") is None
    assert output["options"]["pointTolerance"] == 25
    assert output["options"]["lineTolerance"] == 10
    assert output["options"]["polygonTolerance"] == 5

    # API keys
    assert output["options"].get("googleKey") is None
    assert output["options"].get("bingKey") is None
    assert output["options"].get("ignKey") is None

    # Scales
    assert not output["options"].get("use_native_zoom_levels")
    assert not output["options"].get("hide_numeric_scale_value")
    assert output["options"]["mapScales"] == [10000, 25000, 50000, 100000, 250000, 500000]
    assert output["options"]["minScale"] == 1
    assert output["options"]["maxScale"] == 1000000000
    assert output["options"].get("max_scale_points") is None
    assert output["options"].get("max_scale_lines_polygons") is None

    # Map interface
    assert not output["options"].get("hideHeader")
    assert not output["options"].get("hideMenu")
    assert not output["options"].get("hideLegend")
    assert not output["options"].get("hideOverview")
    assert not output["options"].get("hideNavbar")
    assert output["options"]["popupLocation"] == "dock"
    assert output["options"].get("fixed_scale_overview_map")

    # Layers page
    assert output["options"].get("hideGroupCheckbox") is None
    assert output["options"].get("activateFirstMapTheme") is None

    # Baselayers page
    assert output["options"].get("emptyBaselayer") is None
    assert output["options"].get("startupBaselayer") is None

    # Attribute page
    assert output["options"].get("limitDataToBbox") is None

    # Layouts page
    assert not output["options"].get("default_popup_print")

    # Dataviz page
    assert output["options"].get("datavizTemplate") is None
    assert output["options"].get("dataviz_drag_drop") is None
    assert output["options"]["datavizLocation"] == "dock"
    assert output["options"].get("theme") is None  # default value "dark" is not set

    # Time manager page
    assert output["options"]["tmTimeFrameSize"] == 10
    assert output["options"]["tmTimeFrameType"] == "seconds"
    assert output["options"]["tmAnimationFrameLength"] == 1000

    # Atlas page
    assert output["options"].get("atlasShowAtStartup") is None
    assert output["options"].get("atlasAutoPlay") is None

def test_default_options_values_3_8(data: Path, qgis_iface: QgisInterface):
    """Test default options values."""
    lizmap = _setup_empty_project(data, qgis_iface)

    output = lizmap.project_config_file(LwcVersions.Lizmap_3_8, check_server=False, ignore_error=True)

    # generic options
    assert output["options"].get("hideProject") is None
    assert not output["options"].get("automatic_permalink")
    assert not output["options"].get("wms_single_request_for_all_layers")
    assert output["options"].get("acl") is None

    # map tools
    assert not output["options"].get("measure")
    assert output["options"].get("print") is None  # The checkbox is removed since LWC 3.7.0
    assert output["options"].get("zoomHistory") is None  # The checkbox is removed since LWC 3.8.0
    assert not output["options"].get("geolocation")
    assert not output["options"].get("draw")
    assert output["options"].get("externalSearch") is None
    assert output["options"].get("pointTolerance") == 25
    assert output["options"].get("lineTolerance") == 10
    assert output["options"].get("polygonTolerance") == 5

    # API keys
    assert output["options"].get("googleKey") is None
    assert output["options"].get("bingKey") is None
    assert output["options"].get("ignKey") is None

    # Scales
    assert not output["options"].get("use_native_zoom_levels")
    assert not output["options"].get("hide_numeric_scale_value")
    assert output["options"].get("mapScales") == [10000, 25000, 50000, 100000, 250000, 500000]
    assert output["options"].get("minScale") == 1
    assert output["options"].get("maxScale") == 1000000000
    assert output["options"].get("max_scale_points") is None
    assert output["options"].get("max_scale_lines_polygons") is None

    # Map interface
    assert not output["options"].get("hideHeader")
    assert not output["options"].get("hideMenu")
    assert not output["options"].get("hideLegend")
    assert not output["options"].get("hideOverview")
    assert not output["options"].get("hideNavbar")
    assert output["options"].get("popupLocation") == "dock"
    assert output["options"].get("fixed_scale_overview_map")

    # Layers page
    assert output["options"].get("hideGroupCheckbox") is None
    assert output["options"].get("activateFirstMapTheme") is None

    # Baselayers page
    assert output["options"].get("emptyBaselayer") is None
    assert output["options"].get("startupBaselayer") is None

    # Attribute page
    assert output["options"].get("limitDataToBbox") is None

    # Layouts page
    assert not output["options"].get("default_popup_print")

    # Dataviz page
    assert output["options"].get("datavizTemplate") is None
    assert output["options"].get("dataviz_drag_drop") is None
    assert output["options"].get("datavizLocation") == "dock"
    assert output["options"].get("theme") is None  # default value "dark" is not set

    # Time manager page
    assert output["options"].get("tmTimeFrameSize") == 10
    assert output["options"].get("tmTimeFrameType") == "seconds"
    assert output["options"].get("tmAnimationFrameLength") == 1000

    # Atlas page
    assert output["options"].get("atlasShowAtStartup") is None
    assert output["options"].get("atlasAutoPlay") is None

def test_default_options_values_3_9(data: Path, qgis_iface: QgisInterface):
    """Test default options values."""
    lizmap = _setup_empty_project(data, qgis_iface)

    output = lizmap.project_config_file(LwcVersions.Lizmap_3_9, check_server=False, ignore_error=True)

    # generic options
    assert output["options"].get("hideProject") is None
    assert not output["options"].get("automatic_permalink")
    assert not output["options"].get("wms_single_request_for_all_layers")
    assert output["options"].get("acl") is None

    # map tools
    assert not output["options"].get("measure")
    assert output["options"].get("print") is None  # The checkbox is removed since LWC 3.7.0
    assert output["options"].get("zoomHistory") is None  # The checkbox is removed since LWC 3.8.0
    assert not output["options"].get("geolocation")
    # assert output["options"].get("geolocationPrecision") is None # Added since LWC 3.10.0
    # assert output["options"].get("geolocationDirection") is None # Added since LWC 3.10.0
    assert not output["options"].get("draw")
    assert output["options"].get("externalSearch") is None
    assert output["options"].get("pointTolerance") == 25
    assert output["options"].get("lineTolerance") == 10
    assert output["options"].get("polygonTolerance") == 5

    # API keys
    assert output["options"].get("googleKey") is None
    assert output["options"].get("bingKey") is None
    assert output["options"].get("ignKey") is None

    # Scales
    assert not output["options"].get("use_native_zoom_levels")
    assert not output["options"].get("hide_numeric_scale_value")
    assert output["options"].get("mapScales") == [10000, 25000, 50000, 100000, 250000, 500000]
    assert output["options"].get("minScale") == 1
    assert output["options"].get("maxScale") == 1000000000
    assert output["options"].get("max_scale_points") is None
    assert output["options"].get("max_scale_lines_polygons") is None

    # Map interface
    assert not output["options"].get("hideHeader")
    assert not output["options"].get("hideMenu")
    assert not output["options"].get("hideLegend")
    assert not output["options"].get("hideOverview")
    assert not output["options"].get("hideNavbar")
    assert output["options"].get("popupLocation") == "dock"
    assert output["options"].get("fixed_scale_overview_map")

    # Layers page
    assert output["options"].get("hideGroupCheckbox") is None
    assert output["options"].get("activateFirstMapTheme") is None

    # Baselayers page
    assert output["options"].get("emptyBaselayer") is None
    assert output["options"].get("startupBaselayer") is None

    # Attribute page
    assert output["options"].get("limitDataToBbox") is None

    # Layouts page
    assert not output["options"].get("default_popup_print")

    # Dataviz page
    assert output["options"].get("datavizTemplate") is None
    assert output["options"].get("dataviz_drag_drop") is None
    assert output["options"].get("datavizLocation") == "dock"
    assert output["options"].get("theme") is None  # default value "dark" is not set

    # Time manager page
    assert output["options"].get("tmTimeFrameSize") == 10
    assert output["options"].get("tmTimeFrameType") == "seconds"
    assert output["options"].get("tmAnimationFrameLength") == 1000

    # Atlas page
    assert output["options"].get("atlasShowAtStartup") is None
    assert output["options"].get("atlasAutoPlay") is None

def test_default_options_latest(data: Path, qgis_iface: QgisInterface):
    """Test default options values."""
    lizmap = _setup_empty_project(data, qgis_iface)

    output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)

    # generic options
    assert output["options"].get("hideProject") is None
    assert not output["options"].get("automatic_permalink")
    assert not output["options"].get("wms_single_request_for_all_layers")
    assert output["options"].get("acl") is None

    # map tools
    assert not output["options"].get("measure")
    assert output["options"].get("print") is None  # The checkbox is removed since LWC 3.7.0
    assert output["options"].get("zoomHistory") is None  # The checkbox is removed since LWC 3.8.0
    assert not output["options"].get("geolocation")
    assert output["options"].get("geolocationPrecision")  # Added since LWC 3.10.0
    assert not output["options"].get("geolocationDirection")  # Added since LWC 3.10.0
    assert not output["options"].get("draw")
    assert output["options"].get("externalSearch") is None
    assert output["options"].get("pointTolerance") == 25
    assert output["options"].get("lineTolerance") == 10
    assert output["options"].get("polygonTolerance") == 5

    # API keys
    assert output["options"].get("googleKey") is None
    assert output["options"].get("bingKey") is None
    assert output["options"].get("ignKey") is None

    # Scales
    assert not output["options"].get("use_native_zoom_levels")
    assert not output["options"].get("hide_numeric_scale_value")
    assert output["options"].get("mapScales") == [10000, 25000, 50000, 100000, 250000, 500000]
    assert output["options"].get("minScale") == 1
    assert output["options"].get("maxScale") == 1000000000
    assert output["options"].get("max_scale_points") is None
    assert output["options"].get("max_scale_lines_polygons") is None

    # Map interface
    assert not output["options"].get("hideHeader")
    assert not output["options"].get("hideMenu")
    assert not output["options"].get("hideLegend")
    assert not output["options"].get("hideOverview")
    assert not output["options"].get("hideNavbar")
    assert output["options"].get("popupLocation") == "dock"
    assert output["options"].get("fixed_scale_overview_map")

    # Layers page
    assert output["options"].get("hideGroupCheckbox") is None
    assert output["options"].get("activateFirstMapTheme") is None

    # Baselayers page
    assert output["options"].get("emptyBaselayer") is None
    assert output["options"].get("startupBaselayer") is None

    # Attribute page
    assert output["options"].get("limitDataToBbox") is None

    # Layouts page
    assert not output["options"].get("default_popup_print")

    # Dataviz page
    assert output["options"].get("datavizTemplate") is None
    assert output["options"].get("dataviz_drag_drop") is None
    assert output["options"].get("datavizLocation") == "dock"
    assert output["options"].get("theme") is None  # default value "dark" is not set

    # Time manager page
    assert output["options"].get("tmTimeFrameSize") == 10
    assert output["options"].get("tmTimeFrameType") == "seconds"
    assert output["options"].get("tmAnimationFrameLength") == 1000

    # Atlas page
    assert output["options"].get("atlasShowAtStartup") is None
    assert output["options"].get("atlasAutoPlay") is None

def test_max_scale_lwc_3_7(data: Path, qgis_iface: QgisInterface):
    """Test about maximum scale when zooming."""
    lizmap = _setup_empty_project(data, qgis_iface, LwcVersions.Lizmap_3_6)

    assert lizmap.dlg.max_scale_points.scale() == 5000.0
    assert lizmap.dlg.max_scale_lines_polygons.scale() == 5000.0

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
    assert output["options"]["max_scale_points"] == 1000.0
    assert output["options"].get("max_scale_lines_polygons") is None

def test_general_scales_properties_lwc_3_6(data: Path, qgis_iface: QgisInterface):
    """Test some UI settings about general properties with LWC 3.6."""
    lizmap = _setup_empty_project(data, qgis_iface, LwcVersions.Lizmap_3_6)

    # Check default values
    assert lizmap.dlg.list_map_scales.text() == "10000, 25000, 50000, 100000, 250000, 500000"

    # Default values from config.py at the beginning only
    assert lizmap.dlg.minimum_scale.text() == "1"
    assert lizmap.dlg.maximum_scale.text() == "1000000000"

    # Trigger the signal
    lizmap.get_min_max_scales()

    # Values from the UI
    assert lizmap.dlg.minimum_scale.text() == "10000"
    assert lizmap.dlg.maximum_scale.text() == "500000"

    scales = "1000, 5000, 15000"

    # Fill scales
    lizmap.dlg.list_map_scales.setText(scales)
    lizmap.get_min_max_scales()
    assert lizmap.dlg.minimum_scale.text() == "1000"
    assert lizmap.dlg.maximum_scale.text() == "15000"
    assert lizmap.dlg.list_map_scales.text() == scales

    # Check new values in the output config
    output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)

    # Check scales in the CFG
    assert output["options"]["minScale"] == 1000
    assert output["options"]["maxScale"] == 15000
    assert output["options"]["mapScales"] == [1000, 5000, 15000]

    # Project is in EPSG:2154, must be False
    assert not output["options"]["use_native_zoom_levels"]

    # Check an empty list and a populated list then
    assert output["options"].get("acl") is None
    lizmap.dlg.inAcl.setText("cadastre,urbanism")

    output = lizmap.project_config_file(
        LwcVersions.latest(),
        check_server=False,
        ignore_error=True,
    )
    TestCase.assertListEqual(["cadastre", "urbanism"], output["options"].get("acl"))

def test_read_existing_lwc_3_6_to_3_7(data: Path, qgis_iface: QgisInterface):
    """Test to read a CFG 3.6 and to export it to 3.7 about scales."""
    # Checking CFG before opening the QGS file
    with data.joinpath("3857_project_lwc_3_6.qgs.cfg").open() as f:
        json_data = json.load(f)
    TestCase.assertListEqual([1000, 5000, 10000, 500000], json_data["options"]["mapScales"])

    project = QgsProject.instance()
    project.read(str(data.joinpath("3857_project_lwc_3_6.qgs")))
    assert len(project.mapLayers()) == 1

    lizmap = Lizmap(qgis_iface, lwc_version=LwcVersions.Lizmap_3_7)
    # read_cfg_file will call "layers_config_file"
    lizmap.read_cfg_file(skip_tables=True)

    assert lizmap.dlg.minimum_scale.text() == "1000"
    assert lizmap.dlg.maximum_scale.text() == "500000"
    assert lizmap.dlg.list_map_scales.text() == "1000, 5000, 10000, 500000"

    output = lizmap.project_config_file(
        LwcVersions.Lizmap_3_7,
        check_server=False,
        ignore_error=True,
    )

    # Project is in EPSG:3857, must be True
    assert output["options"]["use_native_zoom_levels"]
    # only two when we save
    assert output["options"]["mapScales"] == [1000, 500000]
    assert output["options"]["minScale"] == 1000
    assert output["options"]["maxScale"] == 500000

def test_read_existing_lwc_3_6_to_3_6(data: Path, qgis_iface: QgisInterface):
    """Test to read a CFG 3.6 and to export it to 3.6 about scales."""
    # Checking CFG before opening the QGS file
    project = QgsProject.instance()
    project.read(str(data.joinpath("3857_project_lwc_3_6.qgs")))
    assert len(project.mapLayers()) == 1

    lizmap = Lizmap(qgis_iface, lwc_version=LwcVersions.Lizmap_3_6)
    # read_cfg_file will call "layers_config_file"
    lizmap.read_cfg_file(skip_tables=True)

    assert lizmap.dlg.minimum_scale.text() == "1000"
    assert lizmap.dlg.maximum_scale.text() == "500000"
    assert lizmap.dlg.list_map_scales.text() == "1000, 5000, 10000, 500000"

    output = lizmap.project_config_file(
        LwcVersions.Lizmap_3_6,
        check_server=False,
        ignore_error=True,
    )

    # Project is in EPSG:3857, must be False because of LWC 3.6
    assert not output["options"]["use_native_zoom_levels"]

    TestCase.assertListEqual([1000, 5000, 10000, 500000], output["options"]["mapScales"])
    assert output["options"]["minScale"] == 1000
    assert output["options"]["maxScale"] == 500000

def test_atlas_auto_play_true_values(data: Path, qgis_iface: QgisInterface):
    """Test some UI settings about boolean values."""
    lizmap = _setup_empty_project(data, qgis_iface)

    output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
    assert output["options"].get("atlasAutoPlay") is None

    lizmap.dlg.atlasAutoPlay.setChecked(True)

    output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
    assert output["options"].get("atlasAutoPlay")

    lizmap.dlg.atlasAutoPlay.setChecked(False)

    output = lizmap.project_config_file(
        LwcVersions.latest(),
        check_server=False,
        ignore_error=True,
    )

    assert output["options"].get("atlasAutoPlay") is None

def test_geolocation_values(data: Path, qgis_iface: QgisInterface):
    """Test geolocation UI settings."""
    lizmap = _setup_empty_project(data, qgis_iface)

    # Default geolocation checkboxes checked
    assert not lizmap.dlg.groupbox_geolocation.isChecked()
    assert lizmap.dlg.checkbox_geolocation_precision.isChecked()
    assert not lizmap.dlg.checkbox_geolocation_direction.isChecked()

    # Default geolocation checkboxes enabled
    assert lizmap.dlg.groupbox_geolocation.isEnabled()
    assert not lizmap.dlg.checkbox_geolocation_precision.isEnabled()
    assert not lizmap.dlg.checkbox_geolocation_direction.isEnabled()

    # Check geolocation checkbox to enable other checkboxes
    lizmap.dlg.groupbox_geolocation.setChecked(True)
    assert lizmap.dlg.checkbox_geolocation_precision.isEnabled()
    assert lizmap.dlg.checkbox_geolocation_direction.isEnabled()

    output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
    # options
    assert output["options"].get("geolocation")
    assert output["options"].get("geolocationPrecision")
    assert not output["options"].get("geolocationDirection")

    # Check direction
    lizmap.dlg.checkbox_geolocation_direction.setChecked(True)
    # Uncheck precision
    lizmap.dlg.checkbox_geolocation_precision.setChecked(False)

    output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
    # options
    assert output["options"].get("geolocation")
    assert not output["options"].get("geolocationPrecision")
    assert output["options"].get("geolocationDirection")

def test_exclude_basemaps_from_single_wms_values(data: Path, qgis_iface: QgisInterface):
    """Test exclude basemaps from single WMS UI settings."""
    lizmap = _setup_empty_project(data, qgis_iface)

    # Default checkbox states
    assert not lizmap.dlg.checkbox_wms_single_request_all_layers.isChecked()
    assert not lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.isChecked()

    # Exclude basemaps checkbox should be disabled when single WMS is off
    assert not lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.isEnabled()

    # Enable single WMS - exclude basemaps checkbox should become enabled
    lizmap.dlg.checkbox_wms_single_request_all_layers.setChecked(True)
    assert lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.isEnabled()

    output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
    # Single WMS enabled, exclude basemaps still unchecked
    assert output["options"].get("wms_single_request_for_all_layers")
    assert not output["options"].get("exclude_basemaps_from_single_wms")

    # Enable exclude basemaps
    lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.setChecked(True)

    output = lizmap.project_config_file(LwcVersions.latest(), check_server=False, ignore_error=True)
    # Both options enabled
    assert output["options"].get("wms_single_request_for_all_layers")
    assert output["options"].get("exclude_basemaps_from_single_wms")

    # Disable single WMS - exclude basemaps checkbox should become disabled
    lizmap.dlg.checkbox_wms_single_request_all_layers.setChecked(False)
    assert not lizmap.dlg.checkbox_exclude_basemaps_from_single_wms.isEnabled()
