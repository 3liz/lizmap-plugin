"""Test layer information."""

from pathlib import Path

from qgis.core import Qgis, QgsProject, QgsVectorLayer
from qgis.testing.mocked import get_iface

from lizmap.definitions.definitions import LayerProperties, LwcVersions
from lizmap.plugin import Lizmap
from lizmap.toolbelt.layer import layer_property, set_layer_property

from .compat import TestCase


class TestLayerTree(TestCase):
    def test_read_properties(self, data: Path):
        """Test we can read a layer property."""
        layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
        if Qgis.versionInt() < 33800:
            layer.setShortName("the_lines")
            layer.setTitle("The lines")
            layer.setAbstract("The lines layer")
            layer.setDataUrl("https://hello.world")
        else:
            layer.serverProperties().setShortName("the_lines")
            layer.serverProperties().setTitle("The lines")
            layer.serverProperties().setAbstract("The lines layer")
            layer.serverProperties().setDataUrl("https://hello.world")
        self.assertEqual("the_lines", layer_property(layer, LayerProperties.ShortName))
        self.assertEqual("The lines", layer_property(layer, LayerProperties.Title))
        self.assertEqual("The lines layer", layer_property(layer, LayerProperties.Abstract))
        self.assertEqual("https://hello.world", layer_property(layer, LayerProperties.DataUrl))

    def test_write_properties(self, data: Path):
        """Test we can read a layer property."""
        layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
        set_layer_property(layer, LayerProperties.ShortName, "the_lines")
        set_layer_property(layer, LayerProperties.Title, "The lines")
        set_layer_property(layer, LayerProperties.Abstract, "The lines layer")
        set_layer_property(layer, LayerProperties.DataUrl, "https://hello.world")
        if Qgis.versionInt() < 33800:
            self.assertEqual("the_lines", layer.shortName())
            self.assertEqual("The lines", layer.title())
            self.assertEqual("The lines layer", layer.abstract())
            self.assertEqual("https://hello.world", layer.dataUrl())
        else:
            self.assertEqual("the_lines", layer.serverProperties().shortName())
            self.assertEqual("The lines", layer.serverProperties().title())
            self.assertEqual("The lines layer", layer.serverProperties().abstract())
            self.assertEqual("https://hello.world", layer.serverProperties().dataUrl())

    def test_string_to_list(self):
        """Test about text to JSON list."""
        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.latest())
        self.assertListEqual(lizmap.string_to_list(""), [])
        self.assertListEqual(lizmap.string_to_list("a"), ["a"])
        self.assertListEqual(lizmap.string_to_list(" a "), ["a"])
        self.assertListEqual(lizmap.string_to_list("a,b"), ["a", "b"])

    def test_layer_metadata(self, data: Path):
        """Test metadata coming from layer or from Lizmap."""
        project = QgsProject.instance()
        layer_name = "lines"
        layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), layer_name, "ogr")
        project.addMapLayer(layer)
        self.assertTrue(layer.isValid())

        lizmap_config_url = "https://lizmap.url"
        qgis_config_url = "https://qgis.url"

        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.latest())

        # New project so Lizmap is empty
        config = lizmap.layers_config_file()
        self.assertDictEqual(config, {})

        # No link for now, config = {}
        lizmap.myDic = {}  # Must be called before process_node
        lizmap.process_node(project.layerTreeRoot(), None, config)
        self.assertEqual(lizmap.myDic[layer.id()]["link"], "")

        # Set the link from QGIS properties, we should have it in the Lizmap config now
        if Qgis.versionInt() < 33800:
            layer.setDataUrl(qgis_config_url)
        else:
            layer.serverProperties().setDataUrl(qgis_config_url)
        lizmap.myDic = {}  # Must be called before process_node
        lizmap.process_node(project.layerTreeRoot(), None, config)
        self.assertEqual(lizmap.myDic[layer.id()]["link"], qgis_config_url)

        # Hard code a URL in the Lizmap config, not from layer properties
        hard_coded_config = {
            layer_name: {
                "id": layer.id(),
                "name": layer_name,
                "type": "layer",
                "geometryType": "line",
                "extent": [3.854, 43.5786, 3.897, 43.622],
                "crs": "EPSG:4326",
                "title": "lines-geojson",
                "abstract": "",
                "link": lizmap_config_url,
                "minScale": 1,
                "maxScale": 1000000000000,
                "toggled": "False",
                "popup": "False",
                "popupFrame": None,
                "popupSource": "auto",
                "popupTemplate": "",
                "popupMaxFeatures": 10,
                "popupDisplayChildren": "False",
                "noLegendImage": "False",
                "groupAsLayer": "False",
                "baseLayer": "False",
                "displayInLegend": "True",
                "singleTile": "True",
                "imageFormat": "image/png",
                "cached": "False",
                "serverFrame": None,
                "clientCacheExpiration": 300,
            },
        }
        if Qgis.versionInt() < 33800:
            layer.setDataUrl(qgis_config_url)
        else:
            layer.serverProperties().setDataUrl(qgis_config_url)
        lizmap.myDic = {}  # Must be called before process_node
        lizmap.process_node(project.layerTreeRoot(), None, hard_coded_config)
        self.assertEqual(lizmap_config_url, lizmap.myDic[layer.id()]["link"])

        # Remove the link from Lizmap config, it should be the QGIS one now
        if Qgis.versionInt() < 33800:
            layer.setDataUrl(qgis_config_url)
        else:
            layer.serverProperties().setDataUrl(qgis_config_url)
        lizmap.myDic = {}  # Must be called before process_node
        hard_coded_config[layer_name]["link"] = ""
        lizmap.process_node(project.layerTreeRoot(), None, hard_coded_config)
        self.assertEqual(qgis_config_url, lizmap.myDic[layer.id()]["link"])

        # Remove the link from Lizmap config and from QGIS
        if Qgis.versionInt() < 33800:
            layer.setDataUrl("")
        else:
            layer.serverProperties().setDataUrl("")
        lizmap.myDic = {}  # Must be called before process_node
        hard_coded_config[layer_name]["link"] = ""
        lizmap.process_node(project.layerTreeRoot(), None, hard_coded_config)
        self.assertEqual("", lizmap.myDic[layer.id()]["link"])
