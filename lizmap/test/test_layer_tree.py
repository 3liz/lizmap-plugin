"""Test layer information."""

from qgis.core import QgsProject, QgsVectorLayer
from qgis.testing import unittest
from qgis.testing.mocked import get_iface

from lizmap.definitions.definitions import LayerProperties, LwcVersions
from lizmap.plugin import Lizmap
from lizmap.toolbelt.layer import layer_property
from lizmap.toolbelt.resources import plugin_test_data_path

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestLayerTree(unittest.TestCase):

    def test_read_properties(self):
        """ Test we can read a layer property. """
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        layer.setDataUrl('https://hello.world')
        self.assertEqual('https://hello.world', layer_property(layer, LayerProperties.DataUrl))

    def test_string_to_list(self):
        """ Test about text to JSON list. """
        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.latest())
        self.assertListEqual(lizmap.string_to_list(''), [])
        self.assertListEqual(lizmap.string_to_list('a'), ['a'])
        self.assertListEqual(lizmap.string_to_list(' a '), ['a'])
        self.assertListEqual(lizmap.string_to_list('a,b'), ['a', 'b'])

    def test_layer_metadata(self):
        """ Test metadata coming from layer or from Lizmap. """
        project = QgsProject.instance()
        layer_name = 'lines'
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), layer_name, 'ogr')
        project.addMapLayer(layer)
        self.assertTrue(layer.isValid())

        lizmap_config_url = 'https://lizmap.url'
        qgis_config_url = 'https://qgis.url'

        lizmap = Lizmap(get_iface(), lwc_version=LwcVersions.latest())

        # New project so Lizmap is empty
        config = lizmap.layers_config_file()
        self.assertDictEqual(config, {})

        # No link for now, config = {}
        lizmap.myDic = {}  # Must be called before process_node
        lizmap.process_node(project.layerTreeRoot(), None, config)
        self.assertEqual(lizmap.myDic[layer.id()]['link'], '')

        # Set the link from QGIS properties, we should have it in the Lizmap config now
        layer.setDataUrl(qgis_config_url)
        lizmap.myDic = {}  # Must be called before process_node
        lizmap.process_node(project.layerTreeRoot(), None, config)
        self.assertEqual(lizmap.myDic[layer.id()]['link'], qgis_config_url)

        # Hard code a URL in the Lizmap config, not from layer properties
        hard_coded_config = {
            layer_name: {
                'id': layer.id(),
                'name': layer_name,
                'type': 'layer',
                'geometryType': 'line',
                'extent': [3.854, 43.5786, 3.897, 43.622],
                'crs': 'EPSG:4326',
                'title': 'lines-geojson',
                'abstract': '',
                'link': lizmap_config_url,
                'minScale': 1,
                'maxScale': 1000000000000,
                'toggled': 'False',
                'popup': 'False',
                'popupFrame': None,
                'popupSource': 'auto',
                'popupTemplate': '',
                'popupMaxFeatures': 10,
                'popupDisplayChildren': 'False',
                'noLegendImage': 'False',
                'groupAsLayer': 'False',
                'baseLayer': 'False',
                'displayInLegend': 'True',
                'singleTile': 'True',
                'imageFormat': 'image/png',
                'cached': 'False',
                'serverFrame': None,
                'clientCacheExpiration': 300,
            },
        }
        layer.setDataUrl(qgis_config_url)
        lizmap.myDic = {}  # Must be called before process_node
        lizmap.process_node(project.layerTreeRoot(), None, hard_coded_config)
        self.assertEqual(lizmap_config_url, lizmap.myDic[layer.id()]['link'])

        # Remove the link from Lizmap config, it should be the QGIS one now
        layer.setDataUrl(qgis_config_url)
        lizmap.myDic = {}  # Must be called before process_node
        hard_coded_config[layer_name]['link'] = ''
        lizmap.process_node(project.layerTreeRoot(), None, hard_coded_config)
        self.assertEqual(qgis_config_url, lizmap.myDic[layer.id()]['link'])

        # Remove the link from Lizmap config and from QGIS
        layer.setDataUrl('')
        lizmap.myDic = {}  # Must be called before process_node
        hard_coded_config[layer_name]['link'] = ''
        lizmap.process_node(project.layerTreeRoot(), None, hard_coded_config)
        self.assertEqual('', lizmap.myDic[layer.id()]['link'])
