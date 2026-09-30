"""Test Lizmap BaseLayers."""

from pathlib import Path

from qgis.core import (
    QgsLayerTree,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsProject,
    QgsVectorLayer,
)
from qgis.testing.mocked import get_iface

from lizmap.definitions.definitions import GroupNames, IgnLayers, LwcVersions
from lizmap.plugin import Lizmap
from lizmap.plugin.baselayers import (
    add_french_ign_layer,
    add_osm_mapnik,
    add_osm_opentopomap,
)
from lizmap.toolbelt.convert import cast_to_group, cast_to_layer

from .compat import TestCase
from .utils import temporary_file_path


class TestBaseLayers(TestCase):
    def test_add_osm_mapnik(self, data: Path):

        lizmap = self._setup_empty_project(data)

        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "lines"))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenStreetMap"))

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get("lines") is not None)
        self.assertIsNone(output["layers"].get(GroupNames.BaseLayers))
        self.assertIsNone(output["layers"].get("OpenStreetMap"))

        add_osm_mapnik(lizmap)

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenStreetMap"))

        # Some process
        lizmap.process_node(lizmap.layerList, lizmap.project.layerTreeRoot(), None, {})

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get(GroupNames.BaseLayers) is not None)
        self.assertTrue(output["layers"].get("OpenStreetMap") is not None)

    def test_add_osm_opentopomap(self, data: Path):

        lizmap = self._setup_empty_project(data)

        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "lines"))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenTopoMap"))

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get("lines") is not None)
        self.assertIsNone(output["layers"].get(GroupNames.BaseLayers))
        self.assertIsNone(output["layers"].get("OpenTopoMap"))

        add_osm_opentopomap(lizmap)

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenTopoMap"))

        lizmap.process_node(lizmap.layerList, lizmap.project.layerTreeRoot(), None, {})

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get(GroupNames.BaseLayers) is not None)
        self.assertTrue(output["layers"].get("OpenTopoMap") is not None)

    def test_add_french_ign_layer(self, data: Path):

        lizmap = self._setup_empty_project(data)

        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "lines"))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get("lines") is not None)
        self.assertIsNone(output["layers"].get(GroupNames.BaseLayers))
        self.assertIsNone(output["layers"].get(IgnLayers.IgnOrthophoto.title))
        self.assertIsNone(output["layers"].get(IgnLayers.IgnPlan.title))
        self.assertIsNone(output["layers"].get(IgnLayers.IgnCadastre.title))

        add_french_ign_layer(IgnLayers.IgnOrthophoto, lizmap)

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        lizmap.process_node(lizmap.layerList, lizmap.project.layerTreeRoot(), None, {})

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get(GroupNames.BaseLayers) is not None)
        self.assertTrue(output["layers"].get(IgnLayers.IgnOrthophoto.title) is not None)
        self.assertIsNone(output["layers"].get(IgnLayers.IgnPlan.title))
        self.assertIsNone(output["layers"].get(IgnLayers.IgnCadastre.title))

        add_french_ign_layer(IgnLayers.IgnPlan, lizmap)

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        add_french_ign_layer(IgnLayers.IgnCadastre, lizmap)

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        lizmap.process_node(lizmap.layerList, lizmap.project.layerTreeRoot(), None, {})

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get(GroupNames.BaseLayers) is not None)
        self.assertTrue(output["layers"].get(IgnLayers.IgnOrthophoto.title) is not None)
        self.assertTrue(output["layers"].get(IgnLayers.IgnPlan.title) is not None)
        self.assertTrue(output["layers"].get(IgnLayers.IgnCadastre.title) is not None)


    def test_ui_add_layers(self, data: Path):

        lizmap = self._setup_empty_project(data)

        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "lines"))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenStreetMap"))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenTopoMap"))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get("lines") is not None)
        self.assertIsNone(output["layers"].get(GroupNames.BaseLayers))
        self.assertIsNone(output["layers"].get("OpenStreetMap"))
        self.assertIsNone(output["layers"].get("OpenTopoMap"))
        self.assertIsNone(output["layers"].get(IgnLayers.IgnOrthophoto.title))
        self.assertIsNone(output["layers"].get(IgnLayers.IgnPlan.title))
        self.assertIsNone(output["layers"].get(IgnLayers.IgnCadastre.title))

        lizmap.dlg.button_osm_mapnik.click()

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenStreetMap"))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenTopoMap"))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        lizmap.dlg.button_osm_opentopomap.click()

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenStreetMap"))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenTopoMap"))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        lizmap.dlg.button_ign_orthophoto.click()

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenStreetMap"))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenTopoMap"))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        lizmap.dlg.button_ign_plan.click()

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenStreetMap"))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenTopoMap"))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertFalse(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        lizmap.dlg.button_ign_cadastre.click()

        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenStreetMap"))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "OpenTopoMap"))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnOrthophoto.title))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnPlan.title))
        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), IgnLayers.IgnCadastre.title))

        lizmap.process_node(lizmap.layerList, lizmap.project.layerTreeRoot(), None, {})

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get(GroupNames.BaseLayers) is not None)
        self.assertTrue(output["layers"].get("OpenStreetMap") is not None)
        self.assertTrue(output["layers"].get("OpenTopoMap") is not None)
        self.assertTrue(output["layers"].get(IgnLayers.IgnOrthophoto.title) is not None)
        self.assertTrue(output["layers"].get(IgnLayers.IgnPlan.title) is not None)
        self.assertTrue(output["layers"].get(IgnLayers.IgnCadastre.title) is not None)


    def test_ui_add_groups(self, data: Path):

        lizmap = self._setup_empty_project(data)

        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "lines"))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.Hidden))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), "overview"))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BackgroundColor))

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get("lines") is not None)
        self.assertIsNone(output["layers"].get(GroupNames.BaseLayers))
        self.assertIsNone(output["layers"].get(GroupNames.Hidden))
        self.assertIsNone(output["layers"].get("overview"))
        self.assertIsNone(output["layers"].get(GroupNames.BackgroundColor))

        lizmap.dlg.add_group_baselayers.click()

        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "lines"))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.Hidden))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), "overview"))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BackgroundColor))

        lizmap.dlg.add_group_hidden.click()

        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "lines"))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.Hidden))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), "overview"))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BackgroundColor))

        lizmap.dlg.add_group_overview.click()

        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "lines"))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.Hidden))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), "overview"))
        self.assertFalse(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BackgroundColor))

        lizmap.dlg.add_group_empty.click()

        self.assertTrue(self._existing_layer_tree_layer(lizmap.project.layerTreeRoot(), "lines"))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BaseLayers))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.Hidden))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), "overview"))
        self.assertTrue(self._existing_layer_tree_group(lizmap.project.layerTreeRoot(), GroupNames.BackgroundColor))

        lizmap.process_node(lizmap.layerList, lizmap.project.layerTreeRoot(), None, {})

        output = lizmap.project_config_file(
            LwcVersions.latest(),
            check_server=False,
            ignore_error=True,
        )

        self.assertTrue(output["layers"].get(GroupNames.BaseLayers) is not None)
        self.assertTrue(output["layers"].get(GroupNames.Hidden) is not None)
        self.assertTrue(output["layers"].get("overview") is not None)
        self.assertTrue(output["layers"].get(GroupNames.BackgroundColor) is not None)


    def _setup_empty_project(
        self,
        data: Path,
        lwc_version: LwcVersions = LwcVersions.latest(),
    ) -> Lizmap:
        """Internal function to add a layer and a basic check."""
        project = QgsProject.instance()
        project.clear()
        layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
        project.addMapLayer(layer)
        project.setFileName(temporary_file_path())

        lizmap = Lizmap(get_iface(), lwc_version=lwc_version)

        # Do not use read_lizmap_config_file
        # as it will be called by read_cfg_file and also the UI is set in read_cfg_file
        config = lizmap.read_cfg_file(skip_tables=True)

        lizmap.dlg.widget_initial_extent.setOutputExtentFromLayer(layer)

        # Config is empty in the CFG file because it's a new project
        self.assertDictEqual({}, config)

        # Some process
        lizmap.process_node(lizmap.layerList, project.layerTreeRoot(), None, {})

        return lizmap

    def _existing_layer_tree_group(
        self,
        root_group: QgsLayerTree|QgsLayerTreeGroup,
        label: str,
    ) -> bool:
        """Check if a group exists in the layer tree"""
        if not root_group:
            return False

        # Iterate over all child (layers and groups)
        children = root_group.children()
        for child in children:
            if not QgsLayerTree.isGroup(child):
                continue

            qgis_group = cast_to_group(child)
            qgis_group: QgsLayerTreeGroup

            if qgis_group.name() == label:
                return True

            if self._existing_layer_tree_group(qgis_group, label):
                return True

        return False

    def _existing_layer_tree_layer(
        self,
        root_group: QgsLayerTree|QgsLayerTreeGroup,
        label: str,
    ) -> bool:
        """Check if a group exists in the layer tree"""
        if not root_group:
            return False

        # Iterate over all child (layers and groups)
        children = root_group.children()
        for child in children:
            if QgsLayerTree.isGroup(child):
                qgis_group = cast_to_group(child)
                qgis_group: QgsLayerTreeGroup
                if self._existing_layer_tree_layer(qgis_group, label):
                    return True
                continue

            qgis_layer = cast_to_layer(child)
            qgis_layer: QgsLayerTreeLayer

            if qgis_layer.name() == label:
                return True

        return False
