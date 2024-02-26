import unittest

from qgis.core import QgsProject, QgsVectorLayer

from lizmap.project_checker_tools import (
    duplicated_rule_key_legend,
    french_geopf_authcfg_url_parameters,
    trailing_layer_group_name,
)
from lizmap.toolbelt.resources import plugin_test_data_path
from lizmap.widgets.check_project import Error

__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestProjectTable(unittest.TestCase):

    def test_trailing_spaces(self):
        """ Test about trailing spaces in the table. """
        layer = QgsVectorLayer('None?field=field_a:string', ' table', 'memory')
        project = QgsProject()
        project.addMapLayer(layer)

        results = trailing_layer_group_name(project.layerTreeRoot(), project, [])
        self.assertEqual(1, len(results))
        self.assertIsInstance(results[0], Error)
        self.assertEqual(' table', results[0].source)

    def test_rule_key_legend(self):
        """ Test duplicated rule key in the legend. """
        project_file = plugin_test_data_path('rule_key_duplicated.qgs')
        project = QgsProject.instance()
        project.read(project_file)

        self.assertDictEqual(
            {
                'points_b7228e3a_5092_4ee2_b9e7_e1da96f8a395': {
                    '{007c67f1-3e25-479d-b33b-fac4a0a705b0}': 1,
                    '{cdee1fdb-874c-4265-aa26-5e915d69563f}': 2,
                }
            },
            duplicated_rule_key_legend(project))

    def french_raster_datasource_authcfg(self):
        """ Check for authcfg in raster datasource. """
        raster = (
            "contextualWMSLegend=0&amp;crs=EPSG:2154&amp;dpiMode=7&amp;featureCount=10&amp;format=image/jpeg&amp;"
            "layers=SCAN25TOUR_PYR-JPEG_WLD_WM&amp;styles&amp;url=https://other.url.fr/private/wms-r?VERSION%3D1.3.0"
            "&amp;authCFG=x3rzac9"
        )
        self.assertFalse(french_geopf_authcfg_url_parameters(raster))

        raster = (
            "contextualWMSLegend=0&amp;crs=EPSG:2154&amp;dpiMode=7&amp;featureCount=10&amp;format=image/jpeg&amp;"
            "layers=SCAN25TOUR_PYR-JPEG_WLD_WM&amp;styles&amp;url=https://data.GEOPF.fr/private/wms-r?VERSION%3D1.3.0"
            "&amp;authCFG=x3rzac9"
        )
        self.assertTrue(french_geopf_authcfg_url_parameters(raster))

        raster = (
            "contextualWMSLegend=0&amp;crs=EPSG:2154&amp;dpiMode=7&amp;featureCount=10&amp;format=image/jpeg&amp;"
            "layers=SCAN25TOUR_PYR-JPEG_WLD_WM&amp;styles&amp;url=https://data.geopf.fr/private/wms-r?VERSION%3D1.3.0"
        )
        self.assertFalse(french_geopf_authcfg_url_parameters(raster))
