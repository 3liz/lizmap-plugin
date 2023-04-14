__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import unittest

from qgis.core import QgsProject

from lizmap.ogc_project_validity import OgcProjectValidity
from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path


class TestShortNames(unittest.TestCase):

    def tearDown(self) -> None:
        QgsProject.instance().clear()

    def test_shortname_generation(self):
        """ Test we can generate shortname. """
        self.assertEqual("layer", OgcProjectValidity.short_name("layer", []))
        self.assertEqual("layer", OgcProjectValidity.short_name("    layer   ", []))
        self.assertEqual("l_1_layer", OgcProjectValidity.short_name("!1 layer", []))
        self.assertEqual("l_1_layer", OgcProjectValidity.short_name("_1 layer", []))
        self.assertEqual("l_1_layer", OgcProjectValidity.short_name("__1 layer", []))
        self.assertEqual("a_layer", OgcProjectValidity.short_name("a_layer", []))
        self.assertEqual("osm-mapnik", OgcProjectValidity.short_name("osm-mapnik", []))
        self.assertEqual("osm-mapnik", OgcProjectValidity.short_name("-osm-mapnik", []))
        self.assertEqual("a_lAyer", OgcProjectValidity.short_name("à lÂyér", []))
        self.assertEqual("l_123_a_layer", OgcProjectValidity.short_name("123 a layer", []))

        shortname = OgcProjectValidity.short_name('こんにちは', [])
        self.assertEqual(5, len(shortname))
        self.assertTrue(shortname.isalpha())

    def test_shortname_prefix(self):
        """ Test with different prefix. """
        self.assertEqual("a_123_layer", OgcProjectValidity.short_name("a_123 layer", []))
        self.assertEqual("b_123_layer", OgcProjectValidity.short_name("123 layer", [], 'b'))
        self.assertEqual("l_123_layer", OgcProjectValidity.short_name("123 layer", []))

    def test_shortname_incrementation(self):
        """ Test the shortname incrementation. """
        self.assertEqual("layer", OgcProjectValidity.short_name("layer", ['gis']))
        self.assertEqual("LAYER", OgcProjectValidity.short_name("LAYER", ['layer']))
        self.assertEqual("layer_1", OgcProjectValidity.short_name("layer", ['layer']))
        self.assertEqual("layer_2", OgcProjectValidity.short_name("layer", ['layer', 'layer_1']))
        self.assertEqual("layer", OgcProjectValidity.short_name("layer_", ['layer_']))
        self.assertEqual("layer_1", OgcProjectValidity.short_name("layer_", ['layer_', 'layer']))

    def test_parse_legend(self):
        """ Test to read and add all shortnames in a project. """
        project_file = plugin_test_data_path('shortnames.qgs')
        project = QgsProject.instance()
        project.read(project_file)

        validator = OgcProjectValidity(project)
        self.assertListEqual(validator.existing_shortnames(), ['lines-1', 'sub-group'])

        validator.add_shortnames()
        self.assertListEqual(validator.existing_shortnames(), ['lines-1', 'lines-1_1', 'group-1', 'sub-group', 'lines-2'])

        # Project short name
        self.assertEqual("", project.readEntry("WMSRootName", "/", "")[0])

        validator.set_project_short_name()

        self.assertEqual("p_1_Test_project", project.readEntry("WMSRootName", "/", "")[0])
