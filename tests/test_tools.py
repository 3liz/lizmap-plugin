from pathlib import Path

from qgis.core import Qgis, QgsField, QgsVectorLayer
from qgis.PyQt.QtCore import QMetaType, QVariant

from lizmap.toolbelt.convert import ambiguous_to_bool, as_boolean
from lizmap.toolbelt.layer import is_database_layer
from lizmap.toolbelt.lizmap import convert_lizmap_popup
from lizmap.toolbelt.strings import merge_strings, unaccent
from lizmap.toolbelt.version import format_version_integer, qgis_version_info

from .compat import TestCase


class TestTools(TestCase):
    def test_database_based_layer(self, data: Path):
        """Test if a layer is in a database."""
        layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
        self.assertFalse(is_database_layer(layer))

        path = str(data.joinpath("points_lines.gpkg"))
        layer = QgsVectorLayer(path + "|layername=lines", "lines", "ogr")
        self.assertTrue(is_database_layer(layer))

    def test_qgis_version_info(self):
        """Test to get a correct QGIS version number."""
        # Normal
        self.assertTupleEqual((3, 10, 0), qgis_version_info(31000))

        # Increment to stable version

        self.assertTupleEqual((3, 12, 0), qgis_version_info(31100))

        # Zero in the middle
        self.assertTupleEqual((3, 4, 10), qgis_version_info(30410))
        self.assertTupleEqual((4, 3, 14), qgis_version_info(40314, increase_odd_number=False))

    def test_format_version_int(self):
        """Test to transform string version to int version."""
        self.assertEqual("000102", format_version_integer("0.1.2"))
        self.assertEqual("040314", format_version_integer("4.3.14"))
        self.assertEqual("100912", format_version_integer("10.9.12"))
        self.assertEqual("030708", format_version_integer("3.7.8-alpha"))
        self.assertEqual("000000", format_version_integer("master"))

    def test_as_boolean(self):
        """Test the to_bool function."""
        self.assertTrue(as_boolean("trUe"))
        self.assertTrue(as_boolean("1"))
        self.assertTrue(as_boolean(-1))
        self.assertTrue(as_boolean(1))
        self.assertTrue(as_boolean(5))
        self.assertTrue(as_boolean(True))
        self.assertFalse(as_boolean(""))
        self.assertFalse(as_boolean(None))

        self.assertFalse(as_boolean("false"))
        self.assertFalse(as_boolean("FALSE"))
        self.assertFalse(as_boolean(""))
        self.assertFalse(as_boolean("0"))
        self.assertFalse(as_boolean(0))
        self.assertFalse(as_boolean(False))

    def test_ambiguous_to_bool(self):
        """Test the to_bool function."""
        self.assertTrue(ambiguous_to_bool("trUe"))
        self.assertTrue(ambiguous_to_bool("1"))
        self.assertTrue(ambiguous_to_bool(-1))
        self.assertTrue(ambiguous_to_bool(1))
        self.assertTrue(ambiguous_to_bool(5))
        self.assertTrue(ambiguous_to_bool(True))
        self.assertTrue(ambiguous_to_bool(None, default_value=True))
        self.assertTrue(ambiguous_to_bool(""))
        self.assertTrue(ambiguous_to_bool("", default_value=True))

        self.assertFalse(ambiguous_to_bool("false"))
        self.assertFalse(ambiguous_to_bool("FALSE"))
        self.assertFalse(ambiguous_to_bool("", default_value=False))
        self.assertFalse(ambiguous_to_bool("0"))
        self.assertFalse(ambiguous_to_bool(0))
        self.assertFalse(ambiguous_to_bool(False))
        self.assertFalse(ambiguous_to_bool(None, default_value=False))

    def test_unaccent(self):
        """Test to unaccent a string."""
        self.assertEqual("a lAyer", unaccent("à lÂyér"))

    def test_merge_strings(self):
        """Test to merge two strings and remove common parts."""
        self.assertEqual(
            "I like chocolate and banana", merge_strings("I like chocolate", "chocolate and banana")
        )

        # LWC 3.6.1
        # instance name is duplicated
        self.assertEqual(
            "https://demo.lizmap.com/lizmap/assets/js/dataviz/plotly-latest.min.js",
            merge_strings(
                "https://demo.lizmap.com/lizmap/", "/lizmap/assets/js/dataviz/plotly-latest.min.js"
            ),
        )

        # Nothing in common
        self.assertEqual(
            "https://demo.lizmap.com/lizmap/assets/js/dataviz/plotly-latest.min.js",
            merge_strings("https://demo.lizmap.com/lizmap/", "assets/js/dataviz/plotly-latest.min.js"),
        )

        # Only slash
        self.assertEqual(
            "https://demo.lizmap.com/lizmap/assets/js/dataviz/plotly-latest.min.js",
            merge_strings("https://demo.lizmap.com/lizmap/", "/assets/js/dataviz/plotly-latest.min.js"),
        )

    def _layer_lizmap_popup(self) -> QgsVectorLayer:
        """Internal function for setting up the layer."""
        layer = QgsVectorLayer("Point?crs=epsg:4326", "Layer", "memory")
        self.assertTrue(layer.startEditing())

        # Normal field
        if Qgis.versionInt() < 33800:
            field_1 = QgsField("name", QVariant.String)
        else:
            field_1 = QgsField("name", QMetaType.Type.QString)
        layer.addAttribute(field_1)

        # Field with alias
        if Qgis.versionInt() < 33800:
            field_2 = QgsField("longfield", QVariant.String)
        else:
            field_2 = QgsField("longfield", QMetaType.Type.QString)
        field_2.setAlias("an alias")
        layer.addAttribute(field_2)

        # Field with underscore, accents, digit
        if Qgis.versionInt() < 33800:
            field_3 = QgsField("îD_cödÊ_1", QVariant.String)
        else:
            field_3 = QgsField("îD_cödÊ_1", QMetaType.Type.QString)
        layer.addAttribute(field_3)

        self.assertTrue(layer.commitChanges())
        return layer

    def test_convert_lizmap_popup_1(self):
        """Normal test about the Lizmap popup."""
        layer = self._layer_lizmap_popup()

        text = """
        <p style="background-color:{$color}">
            <b>LINE</b> : { $an alias } - {$name}
        </p>"""
        expected = """
        <p style="background-color:{$color}">
            <b>LINE</b> : [% "longfield" %] - [% "name" %]
        </p>"""
        result = convert_lizmap_popup(text, layer)
        self.assertEqual(expected, result[0])
        self.assertListEqual(["color"], result[1])

    def test_convert_lizmap_popup_2(self):
        """Normal test with an alias."""
        layer = self._layer_lizmap_popup()
        text = """
        <p>
            <b>LINE</b> : { $an alias } - {$name}
        </p>"""
        expected = """
        <p>
            <b>LINE</b> : [% "longfield" %] - [% "name" %]
        </p>"""
        result = convert_lizmap_popup(text, layer)
        self.assertEqual(expected, result[0])
        self.assertListEqual([], result[1])

    def test_convert_lizmap_popup_3(self):
        """Test with accents, digit, underscores."""
        layer = self._layer_lizmap_popup()
        text = """
        <a href="media/pdf/{$îD_cödÊ_1}.pdf" target="_blank">
            Link
        </a>"""
        expected = """
        <a href="media/pdf/[% "îD_cödÊ_1" %].pdf" target="_blank">
            Link
        </a>"""
        result = convert_lizmap_popup(text, layer)
        self.assertEqual(expected, result[0])
        self.assertListEqual([], result[1])
