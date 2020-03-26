"""Test Traces."""
from collections import OrderedDict

from qgis.core import QgsVectorLayer, QgsProject
from qgis.testing import unittest

from lizmap.definitions.dataviz import GraphType
from lizmap.forms.trace_dataviz_edition import TraceDatavizEditionDialog
from lizmap.qgis_plugin_tools.tools.resources import plugin_test_data_path

__copyright__ = 'Copyright 2020, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class TestTraceDialog(unittest.TestCase):

    def setUp(self) -> None:
        self.layer = QgsVectorLayer(plugin_test_data_path('lines.geojson'), 'lines', 'ogr')
        QgsProject.instance().addMapLayer(self.layer)
        self.assertTrue(self.layer.isValid())

    def tearDown(self) -> None:
        QgsProject.instance().removeMapLayer(self.layer)
        del self.layer

    def test_z_field(self):
        """Test Z field is visible or not."""
        # Must be visible
        dialog = TraceDatavizEditionDialog(None, self.layer, GraphType.Sunburst, [])
        self.assertEqual(GraphType.Sunburst, dialog._graph)
        # self.assertTrue(dialog.label_z_field.isVisible())
        # self.assertTrue(dialog.z_field.isVisible())
        self.assertFalse(dialog.z_field.allowEmptyFieldName())

        # Not visible
        dialog = TraceDatavizEditionDialog(None, self.layer, GraphType.Histogram, [])
        self.assertFalse(dialog.label_z_field.isVisible())
        self.assertFalse(dialog.z_field.isVisible())
        self.assertTrue(dialog.z_field.allowEmptyFieldName())

    def test_unique(self):
        """Test Y is unique when we add a new row."""
        dialog = TraceDatavizEditionDialog(None, self.layer, GraphType.Histogram, [])
        self.assertFalse(dialog.error.isVisible())
        self.assertEqual('Y field is required.', dialog.validate())
        dialog.y_field.setCurrentIndex(0)
        self.assertIsNone(dialog.validate())

        # Same but with a unique value not existing
        dialog = TraceDatavizEditionDialog(None, self.layer, GraphType.Histogram, ['hello'])
        self.assertFalse(dialog.error.isVisible())
        self.assertEqual('Y field is required.', dialog.validate())
        dialog.y_field.setCurrentIndex(0)
        self.assertIsNone(dialog.validate())

        # Same but with a unique value
        dialog = TraceDatavizEditionDialog(None, self.layer, GraphType.Histogram, ['id'])
        self.assertFalse(dialog.error.isVisible())
        self.assertEqual('Y field is required.', dialog.validate())
        dialog.y_field.setCurrentIndex(0)
        self.assertEqual('This Y field is already existing.', dialog.validate())

    def test_trace_dialog(self):
        """Test trace dialog."""
        dialog = TraceDatavizEditionDialog(None, self.layer, GraphType.Histogram, [])
        self.assertFalse(dialog.error.isVisible())

        self.assertEqual('Y field is required.', dialog.validate())
        self.assertEqual('#086fa1', dialog.color.color().name())
        self.assertEqual('', dialog.color_field.currentField())
        self.assertTrue(dialog.color.isEnabled())
        self.assertTrue(dialog.color_field.allowEmptyFieldName())

        dialog.color_field.setCurrentIndex(1)
        self.assertNotEqual('', dialog.color_field.currentField())
        self.assertFalse(dialog.color.isEnabled())

        dialog.color_field.setCurrentIndex(0)
        self.assertEqual('', dialog.color_field.currentField())
        self.assertTrue(dialog.color.isEnabled())

        dialog.y_field.setCurrentIndex(0)
        self.assertIsNone(dialog.validate())

        data = dialog.save_form()
        expected = OrderedDict()
        expected['y_field'] = 'id'
        expected['color'] = '#086fa1'
        expected['colorfield'] = ''
        expected['z_field'] = ''
        self.assertEqual(expected, data)

        data = OrderedDict()
        data['y_field'] = 'name'
        data['color'] = '#aabbcc'
        data['colorfield'] = ''
        data['z_field'] = ''
        dialog.load_form(data)
        self.assertEqual(data, dialog.save_form())
