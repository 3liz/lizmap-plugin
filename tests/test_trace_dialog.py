from collections import OrderedDict
from pathlib import Path

import pytest

from qgis.core import QgsProject, QgsVectorLayer

from lizmap.definitions.dataviz import GraphType
from lizmap.definitions.definitions import LwcVersions
from lizmap.forms.trace_dataviz_edition import TraceDatavizEditionDialog
from lizmap.qt_style_sheets import NEW_FEATURE_CSS

from .compat import TestCase


@pytest.fixture()
def layer(data: Path):
    layer = QgsVectorLayer(str(data.joinpath("lines.geojson")), "lines", "ogr")
    assert layer.isValid()
    QgsProject.instance().addMapLayer(layer)

    yield layer
    QgsProject.instance().removeMapLayer(layer)


class TestTraceDialog(TestCase):
    def test_z_field(self, layer: QgsVectorLayer):
        """Test Z field is visible or not."""
        # Must be visible
        dialog = TraceDatavizEditionDialog(None, layer, GraphType.Sunburst, [])
        self.assertEqual(GraphType.Sunburst, dialog._graph)
        # self.assertTrue(dialog.label_z_field.isVisible())
        # self.assertTrue(dialog.z_field.isVisible())
        self.assertFalse(dialog.z_field.allowEmptyFieldName())

        # Not visible
        dialog = TraceDatavizEditionDialog(None, layer, GraphType.Histogram, [])
        self.assertFalse(dialog.label_z_field.isVisible())
        self.assertFalse(dialog.z_field.isVisible())
        self.assertTrue(dialog.z_field.allowEmptyFieldName())

    def test_unique(self, layer: QgsVectorLayer):
        """Test Y is unique when we add a new row."""
        dialog = TraceDatavizEditionDialog(None, layer, GraphType.Histogram, [])
        self.assertFalse(dialog.error.isVisible())
        self.assertEqual("id", dialog.y_field.currentField())
        self.assertIsNone(dialog.validate())

        # Same but with a unique value not existing
        dialog = TraceDatavizEditionDialog(None, layer, GraphType.Histogram, ["hello"])
        self.assertFalse(dialog.error.isVisible())
        self.assertEqual("id", dialog.y_field.currentField())
        self.assertIsNone(dialog.validate())

        # Same but with a unique value
        dialog = TraceDatavizEditionDialog(None, layer, GraphType.Histogram, ["id"])
        self.assertFalse(dialog.error.isVisible())
        self.assertEqual("id", dialog.y_field.currentField())
        self.assertEqual("This Y field is already existing.", dialog.validate())

    def test_trace_dialog(self, layer: QgsVectorLayer):
        """Test trace dialog."""
        dialog = TraceDatavizEditionDialog(None, layer, GraphType.Histogram, [])
        self.assertFalse(dialog.error.isVisible())

        # By default, no color field: the default color is used
        self.assertEqual("id", dialog.y_field.currentField())
        self.assertEqual("#086fa1", dialog.color.color().name())
        self.assertEqual("", dialog.color_field.currentField())
        self.assertTrue(dialog.color.isEnabled())

        # The aggregation list is filled, with the default aggregation selected
        assert dialog.trace_aggregation.count() > 0
        self.assertEqual("sum", dialog.trace_aggregation.currentData())

        self.assertTrue(dialog.color_field.allowEmptyFieldName())

        dialog.color_field.setCurrentIndex(1)
        self.assertNotEqual("", dialog.color_field.currentField())
        self.assertFalse(dialog.color.isEnabled())

        dialog.color_field.setCurrentIndex(0)
        self.assertEqual("", dialog.color_field.currentField())
        self.assertTrue(dialog.color.isEnabled())

        dialog.y_field.setCurrentIndex(0)
        self.assertIsNone(dialog.validate())

        data = dialog.save_form()
        expected = OrderedDict()
        expected["y_field"] = "id"
        expected["trace_aggregation"] = "sum"
        expected["color"] = "#086fa1"
        expected["colorfield"] = ""
        expected["z_field"] = ""
        self.assertEqual(expected, data)

        # Load a trace with another aggregation
        data = OrderedDict()
        data["y_field"] = "name"
        data["trace_aggregation"] = "count"
        data["color"] = "#aabbcc"
        data["colorfield"] = ""
        data["z_field"] = ""
        dialog.load_form(data)
        self.assertEqual(data, dialog.save_form())

        # An empty aggregation, from a legacy project, means no aggregation
        data["trace_aggregation"] = ""
        dialog.load_form(data)
        self.assertEqual("no", dialog.trace_aggregation.currentData())

    def test_new_features_lwc_3_11(self, layer: QgsVectorLayer):
        """Test the aggregation label is highlighted for a LWC version older than 3.11."""
        # Not available in LWC 3.10
        dialog = TraceDatavizEditionDialog(None, layer, GraphType.Bar, [], LwcVersions.Lizmap_3_10)
        assert dialog.label_trace_aggregation.styleSheet() == NEW_FEATURE_CSS
        # The other settings are available
        assert dialog.label_y_field.styleSheet() == ""

        # Available in LWC 3.11
        dialog = TraceDatavizEditionDialog(None, layer, GraphType.Bar, [], LwcVersions.Lizmap_3_11)
        assert dialog.label_trace_aggregation.styleSheet() == ""

        # Without version, the latest one is used
        dialog = TraceDatavizEditionDialog(None, layer, GraphType.Bar, [])
        assert dialog.label_trace_aggregation.styleSheet() == ""
