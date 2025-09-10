"""Test toolbelt.

__copyright__ = 'Copyright 2025, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
"""
import tempfile

from pathlib import Path

# from qgis.testing import start_app
from qgis.core import QgsRasterLayer

from lizmap.toolbelt.layer import get_layer_wms_parameters
from lizmap.toolbelt.lizmap import sidecar_media_dirs
from lizmap.toolbelt.strings import human_size

from .compat import TestCase


class TestToolBelt(TestCase):

    def test_human_size(self):
        """ Test human size. """
        self.assertEqual("53 KB", human_size(54512))
        self.assertEqual("53 KB", human_size("54512"))
        self.assertEqual("14 KB", human_size(15145))
        self.assertEqual("14 KB", human_size("15145"))

    def test_lizmap_sidecar_dirs(self):
        """ Test to detect side-car files related to JavaScript or theme. """
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            test = Path(tmp_dir_name) / "project.qgs"
            test.touch()

            side_1 = Path(tmp_dir_name) / "media" / "js" / "default" / "default_included.js"
            side_1.parent.mkdir(parents=True)
            side_1.touch()

            side_2 = Path(tmp_dir_name) / "media" / "js" / "project" / "project_included.js"
            side_2.parent.mkdir(parents=True)
            side_2.touch()

            side_3 = Path(tmp_dir_name) / "media" / "js" / "excluded" / "excluded.js"
            side_3.parent.mkdir(parents=True)
            side_3.touch()

            side_4 = Path(tmp_dir_name) / "media" / "theme" / "default" / "css" / "default_included.css"
            side_4.parent.mkdir(parents=True)
            side_4.touch()

            side_5 = Path(tmp_dir_name) / "media" / "theme" / "excluded" / "css" / "excluded.css"
            side_5.parent.mkdir(parents=True)
            side_5.touch()

            side_6 = Path(tmp_dir_name) / "media" / "theme" / "project" / "css" / "project_included.css"
            side_6.parent.mkdir(parents=True)
            side_6.touch()

            expected = [
                Path(tmp_dir_name) / "media" / "js" / "default",
                Path(tmp_dir_name) / "media" / "js" / "project",
                Path(tmp_dir_name) / "media" / "theme" / "default",
                Path(tmp_dir_name) / "media" / "theme" / "project",
            ]
            expected.sort()
            self.assertListEqual(expected, sidecar_media_dirs(test))

    def test_wms_properties_wms(self):
        """ Test external WMS. """
        raster = QgsRasterLayer(
            "contextualWMSLegend=0&"
            "crs=EPSG:2056&"
            "dpiMode=7&"
            "featureCount=10&"
            "format=image/jpeg&"
            "layers=ch.swisstopo.pixelkarte-grau&"
            "styles&"
            "tilePixelRatio=0&"
            "url=https://wms.geo.admin.ch/",
            "wms",
            "wms"
        )
        self.assertTrue(raster.isValid())
        self.assertEqual('wms', raster.providerType())

        data = get_layer_wms_parameters(raster)

        self.assertEqual("0", data['contextualWMSLegend'])
        self.assertEqual("EPSG:2056", data['crs'])
        self.assertEqual("7", data['dpiMode'])
        self.assertEqual("10", data['featureCount'])
        self.assertEqual("image/jpeg", data['format'])
        self.assertEqual("ch.swisstopo.pixelkarte-grau", data['layers'])
        self.assertEqual("", data['styles'])
        self.assertEqual("0", data['tilePixelRatio'])
        self.assertEqual("https://wms.geo.admin.ch/", data['url'])

    def test_wms_properties_wmts(self):
        """ Test external WMTS. """
        raster = QgsRasterLayer(
            "crs=EPSG:3857&"
            "dpiMode=7&"
            "format=image/jpeg&"
            "layers=ORTHOIMAGERY.ORTHOPHOTOS&"
            "styles=normal&"
            "tileMatrixSet=PM&"
            "url=https://data.geopf.fr/wmts?SERVICE%3DWMTS%26VERSION%3D1.0.0%26REQUEST%3DGetCapabilities",
            "wms",
            "wms"
        )
        self.assertTrue(raster.isValid())
        self.assertEqual('wms', raster.providerType())

        data = get_layer_wms_parameters(raster)
        self.assertIsNone(data)
