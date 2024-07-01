"""Test tools."""

import unittest

from qgis.core import QgsField, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant

from lizmap.toolbelt.convert import to_bool
from lizmap.toolbelt.layer import is_database_layer
from lizmap.toolbelt.lizmap import convert_lizmap_popup
from lizmap.toolbelt.resources import plugin_test_data_path
from lizmap.toolbelt.strings import merge_strings, unaccent
from lizmap.toolbelt.version import format_qgis_version, format_version_integer

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


class TestTools(unittest.TestCase):

    def test_database_based_layer(self):
        """ Test if a layer is in a database. """
        layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        self.assertFalse(is_database_layer(layer))

        path = plugin_test_data_path('points_lines.gpkg', copy=True)
        layer = QgsVectorLayer(path + '|layername=lines', 'lines', 'ogr')
        self.assertTrue(is_database_layer(layer))

    def test_format_qgis_version(self):
        """ Test to get a correct QGIS version number. """
        # Normal
        self.assertTupleEqual((3, 10, 0), format_qgis_version(31000))

        # Increment to stable version

        self.assertTupleEqual((3, 12, 0), format_qgis_version(31100))

        # Zero in the middle
        self.assertTupleEqual((3, 4, 10), format_qgis_version(30410))
        self.assertTupleEqual((4, 3, 14), format_qgis_version(40314, increase_odd_number=False))

        # As string, with long numbers
        self.assertTupleEqual((10, 11, 10), format_qgis_version("10.11.10", increase_odd_number=False))
        self.assertTupleEqual((10, 12, 10), format_qgis_version("10.11.10", increase_odd_number=True))

    def test_format_version_int(self):
        """ Test to transform string version to int version. """
        self.assertEqual("000102", format_version_integer("0.1.2"))
        self.assertEqual("040314", format_version_integer("4.3.14"))
        self.assertEqual("100912", format_version_integer("10.9.12"))
        self.assertEqual("030708", format_version_integer("3.7.8-alpha"))
        self.assertEqual("000000", format_version_integer("master"))

    def test_to_bool(self):
        """ Test the to_bool function. """
        self.assertTrue(to_bool('trUe'))
        self.assertTrue(to_bool('1'))
        self.assertTrue(to_bool(-1))
        self.assertTrue(to_bool(1))
        self.assertTrue(to_bool(5))
        self.assertTrue(to_bool(True))
        self.assertTrue(to_bool(None, default_value=True))
        self.assertTrue(to_bool(''))
        self.assertTrue(to_bool('', default_value=True))

        self.assertFalse(to_bool('false'))
        self.assertFalse(to_bool('FALSE'))
        self.assertFalse(to_bool('', default_value=False))
        self.assertFalse(to_bool('0'))
        self.assertFalse(to_bool(0))
        self.assertFalse(to_bool(False))
        self.assertFalse(to_bool(None, default_value=False))

    def test_unaccent(self):
        """ Test to unaccent a string. """
        self.assertEqual("a lAyer", unaccent("à lÂyér"))

    def test_merge_strings(self):
        """ Test to merge two strings and remove common parts. """
        self.assertEqual(
            'I like chocolate and banana',
            merge_strings('I like chocolate', 'chocolate and banana')
        )

        # LWC 3.6.1
        # instance name is duplicated
        self.assertEqual(
            'https://demo.lizmap.com/lizmap/assets/js/dataviz/plotly-latest.min.js',
            merge_strings('https://demo.lizmap.com/lizmap/', '/lizmap/assets/js/dataviz/plotly-latest.min.js')
        )

        # Nothing in common
        self.assertEqual(
            'https://demo.lizmap.com/lizmap/assets/js/dataviz/plotly-latest.min.js',
            merge_strings('https://demo.lizmap.com/lizmap/', 'assets/js/dataviz/plotly-latest.min.js')
        )

        # Only slash
        self.assertEqual(
            'https://demo.lizmap.com/lizmap/assets/js/dataviz/plotly-latest.min.js',
            merge_strings('https://demo.lizmap.com/lizmap/', '/assets/js/dataviz/plotly-latest.min.js')
        )

    def _layer_lizmap_popup(self) -> QgsVectorLayer:
        """ Internal function for setting up the layer. """
        layer = QgsVectorLayer('Point?crs=epsg:4326', 'Layer', "memory")
        self.assertTrue(layer.startEditing())

        # Normal field
        field_1 = QgsField("name", QVariant.String)
        layer.addAttribute(field_1)

        # Field with alias
        field_2 = QgsField("longfield", QVariant.String)
        field_2.setAlias("an alias")
        layer.addAttribute(field_2)

        # Field with underscore, accents, digit
        field_3 = QgsField("îD_cödÊ_1", QVariant.String)
        layer.addAttribute(field_3)

        self.assertTrue(layer.commitChanges())
        return layer

    def test_convert_lizmap_popup_1(self):
        """ Normal test about the Lizmap popup. """
        layer = self._layer_lizmap_popup()

        text = '''
        <p style="background-color:{$color}">
            <b>LINE</b> : { $an alias } - {$name}
        </p>'''
        expected = '''
        <p style="background-color:{$color}">
            <b>LINE</b> : [% "longfield" %] - [% "name" %]
        </p>'''
        result = convert_lizmap_popup(text, layer)
        self.assertEqual(expected, result[0])
        self.assertListEqual(['color'], result[1])

    def test_convert_lizmap_popup_2(self):
        """ Normal test with an alias. """
        layer = self._layer_lizmap_popup()
        text = '''
        <p>
            <b>LINE</b> : { $an alias } - {$name}
        </p>'''
        expected = '''
        <p>
            <b>LINE</b> : [% "longfield" %] - [% "name" %]
        </p>'''
        result = convert_lizmap_popup(text, layer)
        self.assertEqual(expected, result[0])
        self.assertListEqual([], result[1])

    def test_convert_lizmap_popup_3(self):
        """ Test with accents, digit, underscores. """
        layer = self._layer_lizmap_popup()
        text = '''
        <a href="media/pdf/{$îD_cödÊ_1}.pdf" target="_blank">
            Link
        </a>'''
        expected = '''
        <a href="media/pdf/[% "îD_cödÊ_1" %].pdf" target="_blank">
            Link
        </a>'''
        result = convert_lizmap_popup(text, layer)
        self.assertEqual(expected, result[0])
        self.assertListEqual([], result[1])
