"""Test toolbelt."""

import unittest

from qgis.core import QgsRasterLayer

from lizmap.toolbelt.layer import layer_wms_parameters
from lizmap.toolbelt.strings import human_size

__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestToolBelt(unittest.TestCase):

    def test_human_size(self):
        """ Test human size. """
        self.assertEqual("53 KB", human_size(54512))
        self.assertEqual("53 KB", human_size("54512"))
        self.assertEqual("14 KB", human_size(15145))
        self.assertEqual("14 KB", human_size("15145"))

    def test_wms_properties(self):
        """ Test WMS layer properties. """
        layer = QgsRasterLayer(
            "contextualWMSLegend=0&crs=EPSG:2056&dpiMode=7&featureCount=10&format=image/jpeg&"
            "layers=ch.swisstopo.pixelkarte-grau&styles&tilePixelRatio=0&url=https://wms.geo.admin.ch/",
            "test",
            "wms"
        )
        expected = {
            'contextualWMSLegend': '0',
            'crs': 'EPSG:2056',
            'dpiMode': '7',
            'featureCount': '10',
            'format': 'image/jpeg',
            'layers': 'ch.swisstopo.pixelkarte-grau',
            # 'styles': '',
            'tilePixelRatio': '0',
            'url': 'https://wms.geo.admin.ch/',
        }
        self.assertDictEqual(expected, layer_wms_parameters(layer))
